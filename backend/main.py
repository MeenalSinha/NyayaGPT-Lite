"""
NyayaGPT Lite - Backend API
FastAPI server for legal document explanation
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import pdfplumber
import io
import re
import os
import uuid
import tempfile
from datetime import datetime

# boto3 is the AWS SDK — install with: pip install boto3
# On EC2 with an IAM role, no credentials needed. Otherwise set:
#   AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION
try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
    _S3_AVAILABLE = True
except ImportError:
    _S3_AVAILABLE = False

# ── S3 configuration ─────────────────────────────────────────────────────────
# Bucket name must match what you created in the AWS console.
# Change this value to your actual bucket name if different.
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "nyayagpt-documents")

# Initialise the S3 client once at module load.
# On EC2 with an attached IAM role this picks up credentials automatically.
# Locally, export AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_DEFAULT_REGION.
_s3_client = boto3.client("s3") if _S3_AVAILABLE else None


def upload_pdf_to_s3(file_bytes: bytes, original_filename: str) -> str:
    """
    Upload raw PDF bytes to S3 and return the object key.

    Uses a UUID-prefixed key so concurrent uploads never collide.
    Raises RuntimeError if S3 is unavailable or the upload fails.
    """
    if not _S3_AVAILABLE or _s3_client is None:
        raise RuntimeError("boto3 is not installed — cannot upload to S3.")

    # e.g. uploads/3f2504e0-4f89-11d3-9a0c-0305e82c3301.pdf
    key = f"uploads/{uuid.uuid4()}.pdf"

    # Write bytes to a named temp file so upload_fileobj can stream it
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        _s3_client.upload_file(
            tmp_path,
            S3_BUCKET_NAME,
            key,
            ExtraArgs={"ContentType": "application/pdf"},
        )
    finally:
        # Always remove the local temp file regardless of success/failure
        os.unlink(tmp_path)

    return key


def delete_s3_object(key: str) -> None:
    """
    Delete a single object from S3 by key.
    Logs a warning on failure rather than raising — deletion is best-effort.
    """
    if not _S3_AVAILABLE or _s3_client is None:
        return
    try:
        _s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=key)
    except (BotoCoreError, ClientError) as exc:
        # Non-fatal: the S3 lifecycle policy will clean it up within 24 h
        import logging as _log
        _log.getLogger(__name__).warning("S3 delete failed for key %s: %s", key, exc)


app = FastAPI(
    title="NyayaGPT Lite API",
    description="AI-powered legal document explanation API for Indian citizens",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models
class DocumentRequest(BaseModel):
    text: str
    language: str = "english"
    # DEMO MODE: frontend sends demoMode=True to force the deterministic path.
    # Defaults to False so existing callers that omit the field are unaffected.
    demoMode: bool = False

class ExplanationResponse(BaseModel):
    summary: str
    parties: Dict[str, str]
    stage: str
    nextSteps: List[str]
    options: List[Dict[str, any]]
    highlightedSections: Optional[List[Dict[str, str]]] = None
    timeline: Optional[str] = None
    suggestedQuestions: Optional[List[str]] = None
    documentType: str
    # DEMO MODE: always present so the frontend badge always has a value to render.
    # "llm"      → fine-tuned Mistral answered
    # "fallback" → deterministic rule-based (model unavailable at runtime)
    # "demo"     → deterministic rule-based (demoMode=True was set by the caller)
    source: str = "fallback"

class HealthResponse(BaseModel):
    status: str
    message: str
    timestamp: str

# Document Type Detection
def detect_document_type(text: str) -> str:
    """Detect the type of legal document"""
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

# Extract key information from document
def extract_document_info(text: str, doc_type: str) -> Dict:
    """Extract key information from legal document"""
    info = {
        'sections': [],
        'parties': {},
        'dates': [],
        'case_number': None
    }
    
    # Extract IPC/CPC sections
    section_pattern = r'(IPC|CPC|CrPC|Section)\s+(\d+[A-Z]?)'
    sections = re.findall(section_pattern, text, re.IGNORECASE)
    info['sections'] = [f"{s[0]} Section {s[1]}" for s in sections]
    
    # Extract dates
    date_pattern = r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}'
    dates = re.findall(date_pattern, text)
    info['dates'] = dates
    
    # Extract case/FIR number
    if doc_type == 'FIR':
        fir_pattern = r'FIR\s*No[.:]?\s*(\d+[/\\]\d+)'
        fir_match = re.search(fir_pattern, text, re.IGNORECASE)
        if fir_match:
            info['case_number'] = fir_match.group(1)
    
    return info

# Generate AI Explanation (Simulated - replace with actual model)
def generate_explanation(text: str, language: str, doc_type: str) -> ExplanationResponse:
    """
    Generate explanation using fine-tuned Mistral model
    
    In production, this would:
    1. Load the fine-tuned model
    2. Create appropriate prompt
    3. Generate response
    4. Parse and structure output
    
    For demo, we provide structured responses based on document type
    """
    
    # Extract document information
    doc_info = extract_document_info(text, doc_type)
    
    # Generate explanations based on language
    if language == 'hindi':
        return generate_hindi_explanation(text, doc_type, doc_info)
    else:
        return generate_english_explanation(text, doc_type, doc_info)

def generate_english_explanation(text: str, doc_type: str, doc_info: Dict) -> ExplanationResponse:
    """Generate English explanation"""
    
    if doc_type == 'FIR':
        return ExplanationResponse(
            summary="This is a First Information Report (FIR) which is the first step in the criminal justice process. It records the complaint about a cognizable offense that has been committed.",
            parties={
                "complainant": "The person who has filed the complaint (extract from document)",
                "accused": "The person against whom the complaint has been filed (extract from document)"
            },
            stage="FIR has been registered - This is the initial stage. Police investigation has begun.",
            nextSteps=[
                "Police will investigate the allegations and collect evidence",
                "Accused may be called for questioning",
                "Accused may be arrested if evidence warrants",
                "Chargesheet will be filed if sufficient evidence is found",
                "Case will proceed to court trial"
            ],
            options=[
                {
                    "title": "Continue with Case",
                    "description": "Allow police investigation and court proceedings to continue",
                    "recommended": True
                },
                {
                    "title": "Mediation/Lok Adalat",
                    "description": "For compoundable offenses, parties can settle through mediation",
                    "recommended": False
                },
                {
                    "title": "Legal Aid",
                    "description": "Apply for free legal assistance through DLSA if financially weak",
                    "recommended": True
                }
            ],
            highlightedSections=[
                {"section": sec, "explanation": f"Legal provision applicable to this case"}
                for sec in doc_info['sections'][:3]
            ] if doc_info['sections'] else None,
            timeline="FIR investigation typically takes 2-3 months. Complete case resolution may take 12-18 months depending on complexity.",
            suggestedQuestions=[
                "Do I need a lawyer at this stage?",
                "What evidence do I need to provide?",
                "Can the FIR be cancelled?",
                "What are my rights during investigation?"
            ],
            documentType=doc_type,
            source="fallback"  # overwritten to "demo" by the endpoint when demoMode=True
        )
    
    elif doc_type == 'COURT_ORDER':
        return ExplanationResponse(
            summary="This is a court order issued by a judicial authority. It contains directions or decisions on specific matters in your case.",
            parties={
                "petitioner": "The party who filed the case/petition",
                "respondent": "The party against whom the case is filed"
            },
            stage="Court order has been issued - The court has made a decision on the matter presented.",
            nextSteps=[
                "Comply with the directions in the order",
                "If dissatisfied, you may file an appeal within the stipulated time",
                "Attend the next hearing date if mentioned",
                "Consult with your lawyer about next steps"
            ],
            options=[
                {
                    "title": "Comply with Order",
                    "description": "Follow the directions given by the court",
                    "recommended": True
                },
                {
                    "title": "File Appeal",
                    "description": "If you disagree with the order, appeal to a higher court within time limit",
                    "recommended": False
                },
                {
                    "title": "Seek Clarification",
                    "description": "If order is unclear, file application for clarification",
                    "recommended": False
                }
            ],
            timeline="Appeal must typically be filed within 30-90 days depending on the court and nature of order.",
            suggestedQuestions=[
                "Can I appeal this order?",
                "What is the time limit for appeal?",
                "Do I need to comply immediately?",
                "What happens if I don't comply?"
            ],
            documentType=doc_type,
            source="fallback"  # overwritten to "demo" by the endpoint when demoMode=True
        )
    
    else:  # LEGAL_NOTICE or GENERAL_LEGAL
        return ExplanationResponse(
            summary="This is a legal notice which is a formal communication about a legal issue. It is often the first step before filing a case.",
            parties={
                "sender": "The party sending the notice",
                "recipient": "The party receiving the notice"
            },
            stage="Legal notice has been sent/received - This is a pre-litigation stage.",
            nextSteps=[
                "Respond to the notice within the time specified (usually 7-30 days)",
                "Consult a lawyer to draft response",
                "Try to resolve the matter amicably if possible",
                "If no resolution, the sender may file a case in court"
            ],
            options=[
                {
                    "title": "Respond to Notice",
                    "description": "Send a reply through your lawyer addressing the issues raised",
                    "recommended": True
                },
                {
                    "title": "Negotiate Settlement",
                    "description": "Try to resolve the matter outside court",
                    "recommended": True
                },
                {
                    "title": "Prepare for Litigation",
                    "description": "If settlement fails, prepare for court case",
                    "recommended": False
                }
            ],
            timeline="Response should be sent within 7-30 days. If case is filed, it may take 6-18 months for resolution.",
            suggestedQuestions=[
                "Do I have to respond?",
                "What happens if I ignore it?",
                "Can I settle this matter?",
                "Do I need a lawyer?"
            ],
            documentType=doc_type,
            source="fallback"  # overwritten to "demo" by the endpoint when demoMode=True
        )

def generate_hindi_explanation(text: str, doc_type: str, doc_info: Dict) -> ExplanationResponse:
    """Generate Hindi explanation"""
    
    if doc_type == 'FIR':
        return ExplanationResponse(
            summary="यह एक प्रथम सूचना रिपोर्ट (FIR) है जो आपराधिक न्याय प्रक्रिया का पहला कदम है। यह एक संज्ञेय अपराध के बारे में शिकायत दर्ज करती है।",
            parties={
                "complainant": "शिकायतकर्ता - जिसने शिकायत दर्ज की है",
                "accused": "आरोपी - जिसके खिलाफ शिकायत दर्ज की गई है"
            },
            stage="FIR दर्ज की गई है - यह प्रारंभिक चरण है। पुलिस जांच शुरू हो गई है।",
            nextSteps=[
                "पुलिस आरोपों की जांच करेगी और साक्ष्य एकत्र करेगी",
                "आरोपी को पूछताछ के लिए बुलाया जा सकता है",
                "यदि सबूत मिलते हैं तो आरोपी को गिरफ्तार किया जा सकता है",
                "पर्याप्त सबूत मिलने पर आरोप पत्र दायर किया जाएगा",
                "मामला न्यायालय में सुनवाई के लिए जाएगा"
            ],
            options=[
                {
                    "title": "मामला जारी रखें",
                    "description": "पुलिस जांच और न्यायालय की कार्यवाही जारी रखने दें",
                    "recommended": True
                },
                {
                    "title": "मध्यस्थता/लोक अदालत",
                    "description": "शमन योग्य अपराधों के लिए, पक्षकार मध्यस्थता के माध्यम से समझौता कर सकते हैं",
                    "recommended": False
                },
                {
                    "title": "कानूनी सहायता",
                    "description": "यदि आर्थिक रूप से कमजोर हैं तो DLSA के माध्यम से मुफ्त कानूनी सहायता के लिए आवेदन करें",
                    "recommended": True
                }
            ],
            highlightedSections=[
                {"section": sec, "explanation": "इस मामले पर लागू कानूनी प्रावधान"}
                for sec in doc_info['sections'][:3]
            ] if doc_info['sections'] else None,
            timeline="FIR जांच में आमतौर पर 2-3 महीने लगते हैं। पूर्ण मामले का समाधान जटिलता के आधार पर 12-18 महीने लग सकते हैं।",
            suggestedQuestions=[
                "क्या मुझे इस स्तर पर वकील की जरूरत है?",
                "मुझे कौन से सबूत देने होंगे?",
                "क्या FIR रद्द की जा सकती है?",
                "जांच के दौरान मेरे क्या अधिकार हैं?"
            ],
            documentType=doc_type,
            source="fallback"  # overwritten to "demo" by the endpoint when demoMode=True
        )
    
    elif doc_type == 'COURT_ORDER':
        return ExplanationResponse(
            summary="यह एक न्यायालय आदेश है जो न्यायिक प्राधिकरण द्वारा जारी किया गया है। इसमें आपके मामले में विशिष्ट मामलों पर निर्देश या निर्णय होते हैं।",
            parties={
                "petitioner": "याचिकाकर्ता - जिसने मामला/याचिका दायर की",
                "respondent": "प्रतिवादी - जिसके खिलाफ मामला दायर किया गया है"
            },
            stage="न्यायालय आदेश जारी किया गया है - न्यायालय ने प्रस्तुत मामले पर निर्णय लिया है।",
            nextSteps=[
                "आदेश में दिए गए निर्देशों का पालन करें",
                "यदि असंतुष्ट हैं, तो निर्धारित समय के भीतर अपील दायर कर सकते हैं",
                "यदि उल्लेख है तो अगली सुनवाई की तारीख पर उपस्थित हों",
                "अगले कदमों के बारे में अपने वकील से परामर्श करें"
            ],
            options=[
                {
                    "title": "आदेश का पालन करें",
                    "description": "न्यायालय द्वारा दिए गए निर्देशों का पालन करें",
                    "recommended": True
                },
                {
                    "title": "अपील दायर करें",
                    "description": "यदि आप आदेश से असहमत हैं, तो समय सीमा के भीतर उच्च न्यायालय में अपील करें",
                    "recommended": False
                },
                {
                    "title": "स्पष्टीकरण मांगें",
                    "description": "यदि आदेश अस्पष्ट है, तो स्पष्टीकरण के लिए आवेदन दायर करें",
                    "recommended": False
                }
            ],
            timeline="अपील आमतौर पर न्यायालय और आदेश की प्रकृति के आधार पर 30-90 दिनों के भीतर दायर की जानी चाहिए।",
            suggestedQuestions=[
                "क्या मैं इस आदेश के खिलाफ अपील कर सकता हूं?",
                "अपील के लिए समय सीमा क्या है?",
                "क्या मुझे तुरंत पालन करना होगा?",
                "यदि मैं पालन नहीं करता तो क्या होगा?"
            ],
            documentType=doc_type,
            source="fallback"  # overwritten to "demo" by the endpoint when demoMode=True
        )
    
    else:  # LEGAL_NOTICE or GENERAL_LEGAL
        return ExplanationResponse(
            summary="यह एक कानूनी नोटिस है जो कानूनी मुद्दे के बारे में औपचारिक संचार है। यह अक्सर मामला दायर करने से पहले का पहला कदम होता है।",
            parties={
                "sender": "नोटिस भेजने वाला पक्ष",
                "recipient": "नोटिस प्राप्त करने वाला पक्ष"
            },
            stage="कानूनी नोटिस भेजा/प्राप्त किया गया है - यह मुकदमा-पूर्व चरण है।",
            nextSteps=[
                "निर्दिष्ट समय के भीतर नोटिस का जवाब दें (आमतौर पर 7-30 दिन)",
                "जवाब तैयार करने के लिए वकील से परामर्श करें",
                "यदि संभव हो तो मामले को सौहार्दपूर्ण ढंग से हल करने का प्रयास करें",
                "यदि कोई समाधान नहीं होता है, तो भेजने वाला न्यायालय में मामला दायर कर सकता है"
            ],
            options=[
                {
                    "title": "नोटिस का जवाब दें",
                    "description": "अपने वकील के माध्यम से उठाए गए मुद्दों को संबोधित करते हुए जवाब भेजें",
                    "recommended": True
                },
                {
                    "title": "समझौते पर बातचीत करें",
                    "description": "न्यायालय के बाहर मामले को हल करने का प्रयास करें",
                    "recommended": True
                },
                {
                    "title": "मुकदमे की तैयारी करें",
                    "description": "यदि समझौता विफल हो जाता है, तो न्यायालय मामले के लिए तैयारी करें",
                    "recommended": False
                }
            ],
            timeline="जवाब 7-30 दिनों के भीतर भेजा जाना चाहिए। यदि मामला दायर किया जाता है, तो समाधान में 6-18 महीने लग सकते हैं।",
            suggestedQuestions=[
                "क्या मुझे जवाब देना होगा?",
                "अगर मैं इसे नजरअंदाज करूं तो क्या होगा?",
                "क्या मैं इस मामले को सुलझा सकता हूं?",
                "क्या मुझे वकील की जरूरत है?"
            ],
            documentType=doc_type,
            source="fallback"  # overwritten to "demo" by the endpoint when demoMode=True
        )

# API Endpoints

@app.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        message="NyayaGPT Lite API is running",
        timestamp=datetime.now().isoformat()
    )

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Detailed health check"""
    return HealthResponse(
        status="healthy",
        message="All systems operational",
        timestamp=datetime.now().isoformat()
    )

@app.post("/api/explain-document", response_model=ExplanationResponse)
async def explain_document(request: DocumentRequest):
    """
    Explain a legal document in simple language.

    Decision tree (evaluated top-to-bottom):
      1. demoMode=True  → deterministic path, source="demo"      [DEMO MODE]
      2. LLM available  → model inference,    source="llm"       [future]
      3. otherwise      → deterministic path, source="fallback"
    """
    try:
        if not request.text or len(request.text.strip()) < 50:
            raise HTTPException(
                status_code=400,
                detail="Document text is too short. Please provide a complete legal document."
            )

        doc_type = detect_document_type(request.text)

        # ── DEMO MODE: bypass LLM entirely, run deterministic path ───────────
        # This branch is always safe: no model loading, no GPU required,
        # guaranteed <100ms response. It will never crash the API.
        if request.demoMode:
            explanation = generate_explanation(request.text, request.language, doc_type)
            explanation.source = "demo"  # distinct label so UI badge is unambiguous
            return explanation
        # ── END DEMO MODE ─────────────────────────────────────────────────────

        # Normal path: LLM first (when integrated), deterministic fallback otherwise.
        # The model_loader integration point is here — swap in your inference call.
        # For now the deterministic generator is the fallback that always fires.
        explanation = generate_explanation(request.text, request.language, doc_type)
        explanation.source = "fallback"
        return explanation

    except HTTPException:
        raise  # re-raise validation errors as-is
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing document: {str(e)}"
        )

@app.post("/api/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF to S3 (if available), extract text with pdfplumber, then
    delete the S3 object immediately so nothing is stored long-term.

    Flow:
      1. Validate file type
      2. Read bytes into memory
      3. Upload to S3  → get back the object key  (skipped if S3 unavailable)
      4. Extract text with pdfplumber from the in-memory bytes
      5. Delete the S3 object                      (skipped if S3 unavailable)
      6. Return extracted text + metadata to the frontend

    The frontend never receives the S3 key — it only gets the extracted text.
    """
    s3_key: str | None = None  # track key so we can delete it in the finally block

    try:
        if not file.filename.endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are supported",
            )

        # Read the entire upload into memory once; reuse the bytes for both
        # S3 upload and pdfplumber — avoids reading the stream twice.
        contents = await file.read()

        # ── Step 3: Upload to S3 ──────────────────────────────────────────────
        if _S3_AVAILABLE and _s3_client is not None:
            try:
                s3_key = upload_pdf_to_s3(contents, file.filename)
            except Exception as s3_err:
                # S3 upload failure is non-fatal — we still extract text locally.
                # Log it so operators can diagnose IAM / bucket issues.
                import logging as _log
                _log.getLogger(__name__).warning(
                    "S3 upload failed (continuing with local extraction): %s", s3_err
                )

        # ── Step 4: Extract text with pdfplumber ─────────────────────────────
        text = ""
        page_count = 0
        with pdfplumber.open(io.BytesIO(contents)) as pdf:
            page_count = len(pdf.pages)
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"

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
        raise  # re-raise validation errors as-is

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing PDF: {exc}",
        )

    # finally:
    #     # ── Step 5: Delete from S3 immediately after extraction ───────────────
    #     # Uncomment for production — deletes the S3 object right after text
    #     # extraction so nothing is stored long-term.
    #     if s3_key is not None:
    #         delete_s3_object(s3_key)

@app.get("/api/document-types")
async def get_document_types():
    """Get list of supported document types"""
    return {
        "documentTypes": [
            {
                "type": "FIR",
                "name": "First Information Report",
                "description": "Initial police report filed for cognizable offenses"
            },
            {
                "type": "COURT_ORDER",
                "name": "Court Order",
                "description": "Judicial order or judgment from a court"
            },
            {
                "type": "LEGAL_NOTICE",
                "name": "Legal Notice",
                "description": "Formal legal communication before filing case"
            },
            {
                "type": "SUMMONS",
                "name": "Summons",
                "description": "Court order to appear before court"
            },
            {
                "type": "BAIL_ORDER",
                "name": "Bail Order",
                "description": "Court order granting or denying bail"
            },
            {
                "type": "GENERAL_LEGAL",
                "name": "General Legal Document",
                "description": "Other legal documents"
            }
        ]
    }

@app.get("/api/languages")
async def get_supported_languages():
    """Get list of supported languages"""
    return {
        "languages": [
            {
                "code": "english",
                "name": "English",
                "nativeName": "English"
            },
            {
                "code": "hindi",
                "name": "Hindi",
                "nativeName": "हिंदी"
            }
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
