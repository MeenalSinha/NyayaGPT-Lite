"""
NyayaGPT Lite - Backend API
FastAPI server for legal document explanation

Inference strategy (hybrid):
  1. On startup, model_loader.py attempts to load Mistral-7B + LoRA adapter.
  2. If successful, /api/explain-document uses LLM inference.
  3. If the model is unavailable OR runtime inference fails, the request
     automatically falls back to the deterministic rule-based logic.
  4. Every response includes a `source` field: "llm" | "fallback" so the
     frontend and operators can see which path was taken.
  The API never returns a 500 due to model unavailability.
"""

from contextlib import asynccontextmanager
import logging
import io
import re
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pdfplumber

# ── Model loader import ───────────────────────────────────────────────────────
# model_loader handles ALL ML dependencies internally.
# If torch/transformers/peft are not installed it degrades gracefully –
# importing this module is always safe.
import model_loader

logger = logging.getLogger(__name__)


# ── Application lifespan ──────────────────────────────────────────────────────
# FastAPI's lifespan context replaces the deprecated @app.on_event("startup").
# Model loading happens here so it runs once before the first request.

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    )
    logger.info("NyayaGPT Lite starting up...")
    logger.info("Attempting to load LoRA model (this may take a minute on first run)...")

    # This call is safe: it NEVER raises, NEVER crashes the app.
    model_loader.load_model()

    status = model_loader.get_model_status()
    logger.info("Model status after startup: %s", status)

    yield  # <- application runs here

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("NyayaGPT Lite shutting down.")


app = FastAPI(
    title="NyayaGPT Lite API",
    description="AI-powered legal document explanation API for Indian citizens",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ─────────────────────────────────────────────────

class DocumentRequest(BaseModel):
    text: str
    language: str = "english"

class ExplanationResponse(BaseModel):
    # ── New field: tells the caller which inference path was used ─────────────
    # "llm"      -> fine-tuned Mistral model answered
    # "fallback" -> deterministic rule-based logic answered
    source: str = "fallback"

    summary: str
    parties: Dict[str, str]
    stage: str
    nextSteps: List[str]
    options: List[Dict[str, Any]]
    highlightedSections: Optional[List[Dict[str, str]]] = None
    timeline: Optional[str] = None
    suggestedQuestions: Optional[List[str]] = None
    documentType: str

class HealthResponse(BaseModel):
    status: str
    message: str
    timestamp: str
    # Expose inference mode so operators can confirm model status at a glance
    inference_mode: str = "fallback"


# ── Document helpers (unchanged) ──────────────────────────────────────────────

def detect_document_type(text: str) -> str:
    """Detect the type of legal document."""
    upper_text = text.upper()
    if 'FIRST INFORMATION REPORT' in upper_text or 'FIR' in upper_text:
        return 'FIR'
    elif 'COURT ORDER' in upper_text or 'JUDGMENT' in upper_text or 'DECREE' in upper_text:
        return 'COURT_ORDER'
    elif 'LEGAL NOTICE' in upper_text or 'NOTICE' in upper_text:
        return 'LEGAL_NOTICE'
    elif 'SUMMONS' in upper_text:
        return 'SUMMONS'
    elif 'BAIL' in upper_text:
        return 'BAIL_ORDER'
    else:
        return 'GENERAL_LEGAL'


def extract_document_info(text: str, doc_type: str) -> Dict:
    """Extract key information from legal document."""
    info: Dict[str, Any] = {
        'sections': [],
        'parties': {},
        'dates': [],
        'case_number': None,
    }
    section_pattern = r'(IPC|CPC|CrPC|Section)\s+(\d+[A-Z]?)'
    sections = re.findall(section_pattern, text, re.IGNORECASE)
    info['sections'] = [f"{s[0]} Section {s[1]}" for s in sections]

    date_pattern = r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}'
    info['dates'] = re.findall(date_pattern, text)

    if doc_type == 'FIR':
        fir_match = re.search(r'FIR\s*No[.:]?\s*(\d+[/\\]\d+)', text, re.IGNORECASE)
        if fir_match:
            info['case_number'] = fir_match.group(1)

    return info


# ── LLM response parser ───────────────────────────────────────────────────────

def _parse_llm_response(raw: str, doc_type: str, doc_info: Dict) -> ExplanationResponse:
    """
    Wrap a raw LLM text output into the structured ExplanationResponse schema.

    The model is instructed to produce sections (Case Summary, Parties, etc.)
    but we cannot guarantee it always will. This parser is deliberately
    lenient: if a section is missing, it uses a safe placeholder rather than
    failing. Incomplete LLM output is better served than a 500 error.
    """

    def _extract_section(text: str, heading: str) -> str:
        """Pull text after a heading until the next heading or end of string."""
        pattern = rf'(?i){re.escape(heading)}[:\-]*\s*\n?(.*?)(?=\n[A-Z][^a-z]{{2,}}|\Z)'
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""

    summary = (
        _extract_section(raw, "Case Summary")
        or _extract_section(raw, "Summary")
        or raw[:500]   # last resort: use first 500 chars of raw output
    )

    parties_raw = (
        _extract_section(raw, "Parties Involved")
        or _extract_section(raw, "Parties")
    )
    # Build a simple dict from the parties block; fall back to generic labels
    parties: Dict[str, str] = {}
    if parties_raw:
        for line in parties_raw.splitlines():
            if ':' in line:
                key, _, val = line.partition(':')
                parties[key.strip().lower()] = val.strip()
    if not parties:
        parties = {"parties": parties_raw or "See document for party details"}

    stage = (
        _extract_section(raw, "Current Stage")
        or _extract_section(raw, "Stage")
        or "See explanation above for current stage details."
    )

    next_steps_raw = (
        _extract_section(raw, "What Usually Happens Next")
        or _extract_section(raw, "Next Steps")
    )
    next_steps = [
        line.lstrip("*-0123456789.) \t")
        for line in next_steps_raw.splitlines()
        if line.strip()
    ] if next_steps_raw else ["Refer to the explanation above for next steps."]

    options_raw = (
        _extract_section(raw, "Available Options")
        or _extract_section(raw, "Options")
    )
    options = [
        {"title": "See Explanation", "description": options_raw or raw, "recommended": False}
    ]

    # Highlighted sections come from regex extraction, not the LLM,
    # so they are always accurate regardless of LLM output quality.
    highlighted = [
        {"section": sec, "explanation": "Legal provision referenced in this document"}
        for sec in doc_info['sections'][:3]
    ] if doc_info['sections'] else None

    # Disclaimer is always appended — even if the LLM already included one.
    # Belt-and-suspenders approach to safety guardrails.
    DISCLAIMER = (
        "\n\n Disclaimer: This explanation is for understanding purposes only "
        "and does not constitute legal advice. Please consult a qualified lawyer."
    )
    if "disclaimer" not in summary.lower():
        summary += DISCLAIMER

    return ExplanationResponse(
        source="llm",
        summary=summary,
        parties=parties,
        stage=stage,
        nextSteps=next_steps,
        options=options,
        highlightedSections=highlighted,
        timeline=None,          # LLM output not reliably structured for this field
        suggestedQuestions=None,
        documentType=doc_type,
    )


# ── Core explanation logic ────────────────────────────────────────────────────

def generate_explanation(text: str, language: str, doc_type: str) -> ExplanationResponse:
    """
    Hybrid explanation dispatcher.

    Decision tree:
      1. If MODEL_AVAILABLE -> try LLM inference
         a. If inference returns a result -> parse and return with source="llm"
         b. If inference returns None (any error) -> fall through to step 2
      2. Use deterministic fallback -> return with source="fallback"

    This function itself does not raise; all failure modes are handled internally.
    """
    doc_info = extract_document_info(text, doc_type)

    # ── Step 1: attempt LLM path ──────────────────────────────────────────────
    if model_loader.MODEL_AVAILABLE:
        logger.info(
            "Attempting LLM inference for doc_type=%s lang=%s", doc_type, language
        )
        raw_output = model_loader.run_inference(text, language, doc_type)

        if raw_output is not None:
            logger.info("LLM inference succeeded; returning LLM response.")
            try:
                return _parse_llm_response(raw_output, doc_type, doc_info)
            except Exception as parse_exc:
                # Parsing failed unexpectedly; fall through to deterministic logic
                logger.warning(
                    "LLM response parsing failed (%s); using fallback.", parse_exc
                )
        else:
            logger.warning("LLM inference returned None; using fallback.")
    else:
        logger.debug("Model not available; using deterministic fallback directly.")

    # ── Step 2: deterministic fallback ────────────────────────────────────────
    if language == 'hindi':
        response = _fallback_hindi(doc_type, doc_info)
    else:
        response = _fallback_english(doc_type, doc_info)

    # Stamp the source so the caller knows this was rule-based
    response.source = "fallback"
    return response


# ── Deterministic fallback functions (original logic, preserved exactly) ──────

def _fallback_english(doc_type: str, doc_info: Dict) -> ExplanationResponse:
    """Original English deterministic explanations."""

    if doc_type == 'FIR':
        return ExplanationResponse(
            summary=(
                "This is a First Information Report (FIR) which is the first step in the "
                "criminal justice process. It records the complaint about a cognizable "
                "offense that has been committed."
            ),
            parties={
                "complainant": "The person who has filed the complaint (extract from document)",
                "accused": "The person against whom the complaint has been filed (extract from document)",
            },
            stage="FIR has been registered - This is the initial stage. Police investigation has begun.",
            nextSteps=[
                "Police will investigate the allegations and collect evidence",
                "Accused may be called for questioning",
                "Accused may be arrested if evidence warrants",
                "Chargesheet will be filed if sufficient evidence is found",
                "Case will proceed to court trial",
            ],
            options=[
                {"title": "Continue with Case",   "description": "Allow police investigation and court proceedings to continue", "recommended": True},
                {"title": "Mediation/Lok Adalat", "description": "For compoundable offenses, parties can settle through mediation", "recommended": False},
                {"title": "Legal Aid",            "description": "Apply for free legal assistance through DLSA if financially weak", "recommended": True},
            ],
            highlightedSections=[
                {"section": sec, "explanation": "Legal provision applicable to this case"}
                for sec in doc_info['sections'][:3]
            ] if doc_info['sections'] else None,
            timeline="FIR investigation typically takes 2-3 months. Complete case resolution may take 12-18 months depending on complexity.",
            suggestedQuestions=[
                "Do I need a lawyer at this stage?",
                "What evidence do I need to provide?",
                "Can the FIR be cancelled?",
                "What are my rights during investigation?",
            ],
            documentType=doc_type,
        )

    elif doc_type == 'COURT_ORDER':
        return ExplanationResponse(
            summary=(
                "This is a court order issued by a judicial authority. It contains directions "
                "or decisions on specific matters in your case."
            ),
            parties={
                "petitioner": "The party who filed the case/petition",
                "respondent": "The party against whom the case is filed",
            },
            stage="Court order has been issued - The court has made a decision on the matter presented.",
            nextSteps=[
                "Comply with the directions in the order",
                "If dissatisfied, you may file an appeal within the stipulated time",
                "Attend the next hearing date if mentioned",
                "Consult with your lawyer about next steps",
            ],
            options=[
                {"title": "Comply with Order",  "description": "Follow the directions given by the court", "recommended": True},
                {"title": "File Appeal",        "description": "If you disagree with the order, appeal to a higher court within time limit", "recommended": False},
                {"title": "Seek Clarification", "description": "If order is unclear, file application for clarification", "recommended": False},
            ],
            timeline="Appeal must typically be filed within 30-90 days depending on the court and nature of order.",
            suggestedQuestions=[
                "Can I appeal this order?",
                "What is the time limit for appeal?",
                "Do I need to comply immediately?",
                "What happens if I don't comply?",
            ],
            documentType=doc_type,
        )

    else:  # LEGAL_NOTICE, SUMMONS, BAIL_ORDER, GENERAL_LEGAL
        return ExplanationResponse(
            summary=(
                "This is a legal notice which is a formal communication about a legal issue. "
                "It is often the first step before filing a case."
            ),
            parties={
                "sender": "The party sending the notice",
                "recipient": "The party receiving the notice",
            },
            stage="Legal notice has been sent/received - This is a pre-litigation stage.",
            nextSteps=[
                "Respond to the notice within the time specified (usually 7-30 days)",
                "Consult a lawyer to draft response",
                "Try to resolve the matter amicably if possible",
                "If no resolution, the sender may file a case in court",
            ],
            options=[
                {"title": "Respond to Notice",     "description": "Send a reply through your lawyer addressing the issues raised", "recommended": True},
                {"title": "Negotiate Settlement",  "description": "Try to resolve the matter outside court", "recommended": True},
                {"title": "Prepare for Litigation","description": "If settlement fails, prepare for court case", "recommended": False},
            ],
            timeline="Response should be sent within 7-30 days. If case is filed, it may take 6-18 months for resolution.",
            suggestedQuestions=[
                "Do I have to respond?",
                "What happens if I ignore it?",
                "Can I settle this matter?",
                "Do I need a lawyer?",
            ],
            documentType=doc_type,
        )


def _fallback_hindi(doc_type: str, doc_info: Dict) -> ExplanationResponse:
    """Original Hindi deterministic explanations."""

    if doc_type == 'FIR':
        return ExplanationResponse(
            summary=(
                "yah ek pratham soochana report (FIR) hai jo aparadhik nyaya prakriya ka pehla kadam hai. "
                "yah ek sangyeya apradh ke baare mein shikayat darj karti hai."
            ),
            parties={
                "complainant": "shikayatkarta - jisne shikayat darj ki hai",
                "accused": "aaropi - jiske khilaf shikayat darj ki gayi hai",
            },
            stage="FIR darj ki gayi hai - yah prarambhik charan hai. Police jaanch shuru ho gayi hai.",
            nextSteps=[
                "Police aaropon ki jaanch karegi aur saakshya ekatrit karegi",
                "aaropi ko poochhataachh ke liye bulaya ja sakta hai",
                "yadi saboot milte hain to aaropi ko giraftaar kiya ja sakta hai",
                "paryapt saboot milne par aarop patra dayar kiya jayega",
                "mamla nyayalaya mein sunwai ke liye jayega",
            ],
            options=[
                {"title": "mamla jaari rakhen",    "description": "Police jaanch aur nyayalaya ki karyawahi jaari rakhne den", "recommended": True},
                {"title": "madhyastha/Lok Adalat", "description": "shaman yogya aparadhon ke liye madhyastha ke maadhyam se samjhauta", "recommended": False},
                {"title": "kanooni sahayta",       "description": "DLSA ke maadhyam se muft kanooni sahayta ke liye aavedan karen", "recommended": True},
            ],
            highlightedSections=[
                {"section": sec, "explanation": "is mamle par laagu kanooni pravdhan"}
                for sec in doc_info['sections'][:3]
            ] if doc_info['sections'] else None,
            timeline="FIR jaanch mein aamtaur par 2-3 mahine lagte hain. Poorn mamle ka samadhan 12-18 mahine lag sakte hain.",
            suggestedQuestions=[
                "kya mujhe is star par vakeel ki zaroorat hai?",
                "mujhe kaun se saboot dene honge?",
                "kya FIR radd ki ja sakti hai?",
                "jaanch ke dauran mere kya adhikar hain?",
            ],
            documentType=doc_type,
        )

    elif doc_type == 'COURT_ORDER':
        return ExplanationResponse(
            summary=(
                "yah ek nyayalaya aadesh hai jo nyayik pradhikaran dwara jaari kiya gaya hai. "
                "ismen aapke mamle mein vishisht mamlon par nirdesh ya nirnay hote hain."
            ),
            parties={
                "petitioner": "yachikakarta - jisne mamla/yaachika dayar ki",
                "respondent": "prativadi - jiske khilaf mamla dayar kiya gaya hai",
            },
            stage="nyayalaya aadesh jaari kiya gaya hai - nyayalaya ne prastut mamle par nirnay liya hai.",
            nextSteps=[
                "aadesh mein diye gaye nirdeshon ka palan karen",
                "yadi asantusht hain, to nirdharit samay ke bheetar appeal dayar kar sakte hain",
                "yadi ullekh hai to agli sunwai ki taareekh par upasthit hon",
                "agle kadmon ke baare mein apne vakeel se paramarsh karen",
            ],
            options=[
                {"title": "aadesh ka palan karen", "description": "nyayalaya dwara diye gaye nirdeshon ka palan karen", "recommended": True},
                {"title": "appeal dayar karen",    "description": "samay seema ke bheetar ucch nyayalaya mein appeal karen", "recommended": False},
                {"title": "spashteekaran maangen", "description": "yadi aadesh aspasht hai, to spashteekaran ke liye aavedan dayar karen", "recommended": False},
            ],
            timeline="appeal aamtaur par 30-90 dinon ke bheetar dayar ki jani chahiye.",
            suggestedQuestions=[
                "kya main is aadesh ke khilaf appeal kar sakta hoon?",
                "appeal ke liye samay seema kya hai?",
                "kya mujhe turant palan karna hoga?",
                "yadi main palan nahi karta to kya hoga?",
            ],
            documentType=doc_type,
        )

    else:
        return ExplanationResponse(
            summary=(
                "yah ek kanooni notice hai jo kanooni mudde ke baare mein aupcharik sanchar hai. "
                "yah aksar mamla dayar karne se pehle ka pehla kadam hota hai."
            ),
            parties={
                "sender": "notice bhejne wala paksh",
                "recipient": "notice prapt karne wala paksh",
            },
            stage="kanooni notice bheja/prapt kiya gaya hai - yah mukadma-poorv charan hai.",
            nextSteps=[
                "nirdisht samay ke bheetar notice ka jawab den (aamtaur par 7-30 din)",
                "jawab taiyar karne ke liye vakeel se paramarsh karen",
                "yadi sambhav ho to mamle ko sauhardapoorv hal karne ka prayas karen",
                "yadi koi samadhan nahi hota hai, to bhejne wala nyayalaya mein mamla dayar kar sakta hai",
            ],
            options=[
                {"title": "notice ka jawab den",    "description": "apne vakeel ke maadhyam se jawab bhejen", "recommended": True},
                {"title": "samjhaute par baatachit karen", "description": "nyayalaya ke bahar mamle ko hal karne ka prayas karen", "recommended": True},
                {"title": "mukadme ki taiyari karen","description": "yadi samjhauta vifal ho jata hai, to nyayalaya mamle ke liye taiyari karen", "recommended": False},
            ],
            timeline="jawab 7-30 dinon ke bheetar bheja jana chahiye. Yadi mamla dayar kiya jata hai, to samadhan mein 6-18 mahine lag sakte hain.",
            suggestedQuestions=[
                "kya mujhe jawab dena hoga?",
                "agar main ise nazarandaz karoon to kya hoga?",
                "kya main is mamle ko sulajha sakta hoon?",
                "kya mujhe vakeel ki zaroorat hai?",
            ],
            documentType=doc_type,
        )


# ── API Endpoints ─────────────────────────────────────────────────────────────

@app.get("/", response_model=HealthResponse)
async def root():
    """Health check - root."""
    status = model_loader.get_model_status()
    return HealthResponse(
        status="healthy",
        message="NyayaGPT Lite API is running",
        timestamp=datetime.now().isoformat(),
        inference_mode=status["inference_mode"],
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Detailed health check including model status."""
    status = model_loader.get_model_status()
    return HealthResponse(
        status="healthy",
        message=f"All systems operational | inference_mode={status['inference_mode']}",
        timestamp=datetime.now().isoformat(),
        inference_mode=status["inference_mode"],
    )


@app.get("/api/model-status")
async def model_status_endpoint():
    """
    Expose detailed model status for operators / dashboards.
    Not consumed by the frontend; for monitoring only.
    """
    return model_loader.get_model_status()


@app.post("/api/explain-document", response_model=ExplanationResponse)
async def explain_document(request: DocumentRequest):
    """
    Explain a legal document in simple language.

    Internally uses LLM inference when available, deterministic fallback otherwise.
    The `source` field in the response ("llm" | "fallback") indicates which path ran.
    """
    try:
        if not request.text or len(request.text.strip()) < 50:
            raise HTTPException(
                status_code=400,
                detail="Document text is too short. Please provide a complete legal document.",
            )

        doc_type = detect_document_type(request.text)

        # generate_explanation handles the LLM -> fallback decision internally.
        # It never raises; a 500 here would mean something truly unexpected.
        explanation = generate_explanation(request.text, request.language, doc_type)
        return explanation

    except HTTPException:
        raise  # re-raise validation errors unchanged
    except Exception as exc:
        logger.error(
            "Unexpected error in /api/explain-document: %s", exc, exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Error processing document: {str(exc)}",
        )


@app.post("/api/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """Extract text from an uploaded PDF."""
    try:
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")

        contents = await file.read()
        text = ""
        with pdfplumber.open(io.BytesIO(contents)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"
            page_count = len(pdf.pages)

        if not text.strip():
            raise HTTPException(
                status_code=400,
                detail="Could not extract text from PDF. Please ensure the PDF contains readable text.",
            )

        doc_type = detect_document_type(text)
        return {
            "text": text.strip(),
            "documentType": doc_type,
            "pageCount": page_count,
            "message": "PDF processed successfully",
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Error processing PDF: {str(exc)}"
        )


@app.get("/api/document-types")
async def get_document_types():
    """Get list of supported document types."""
    return {
        "documentTypes": [
            {"type": "FIR",           "name": "First Information Report", "description": "Initial police report filed for cognizable offenses"},
            {"type": "COURT_ORDER",   "name": "Court Order",              "description": "Judicial order or judgment from a court"},
            {"type": "LEGAL_NOTICE",  "name": "Legal Notice",             "description": "Formal legal communication before filing case"},
            {"type": "SUMMONS",       "name": "Summons",                  "description": "Court order to appear before court"},
            {"type": "BAIL_ORDER",    "name": "Bail Order",               "description": "Court order granting or denying bail"},
            {"type": "GENERAL_LEGAL", "name": "General Legal Document",   "description": "Other legal documents"},
        ]
    }


@app.get("/api/languages")
async def get_supported_languages():
    """Get list of supported languages."""
    return {
        "languages": [
            {"code": "english", "name": "English", "nativeName": "English"},
            {"code": "hindi",   "name": "Hindi",   "nativeName": "Hindi"},
        ]
    }


if __name__ == "__main__":
    import uvicorn
    # Pass as import string ("main:app") so --reload works during development
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
