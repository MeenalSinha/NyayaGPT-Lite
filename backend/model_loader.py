"""
NyayaGPT Lite - Model Loader
Loads Mistral-7B-Instruct-v0.2 + LoRA adapter trained in Kaggle notebook.

FOLDER STRUCTURE THIS FILE EXPECTS:
  nyayagpt-lite/
  ├── backend/
  │   ├── main.py
  │   ├── model_loader.py          ← this file
  │   └── ...
  └── models/                      ← your actual folder (downloaded from Kaggle)
      ├── adapter_model.safetensors
      ├── adapter_config.json
      ├── tokenizer.json
      ├── tokenizer_config.json
      └── chat_template.jinja

  The LORA_ADAPTER_PATH below points one level up from backend/ into models/.
  Adjust the env var LORA_ADAPTER_PATH if your layout differs.

WHAT IS IN models/ vs WHAT IS MISSING:
  ✅  LoRA adapter weights  (adapter_model.safetensors  ~80 MB)
  ✅  Adapter config        (adapter_config.json)
  ✅  Tokenizer             (tokenizer.json, tokenizer_config.json)
  ❌  Base model weights    (NOT stored locally — downloaded from HuggingFace Hub
                             on first run: mistralai/Mistral-7B-Instruct-v0.2, ~14 GB)

  On first startup with a GPU the base model will be downloaded automatically.
  You need ~20 GB free disk space and an internet connection on first run.
  Subsequent runs load from the HuggingFace cache (~/.cache/huggingface/).

TRAINING HYPERPARAMETERS (from your Kaggle notebook — must match exactly):
  Base model : mistralai/Mistral-7B-Instruct-v0.2
  LoRA r     : 16
  LoRA alpha : 32
  LoRA target: q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj
  Quantize   : 4-bit NF4, compute dtype bfloat16
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Global state — written once at startup, read-only thereafter
# ---------------------------------------------------------------------------
MODEL_AVAILABLE: bool = False   # True only when model + tokenizer both loaded
_model = None                   # PeftModel (LoRA-wrapped Mistral)
_tokenizer = None               # Mistral tokenizer

# ---------------------------------------------------------------------------
# Paths & identifiers
# ---------------------------------------------------------------------------

# The adapter lives in models/ which is a sibling of backend/.
# __file__ = .../nyayagpt-lite/backend/model_loader.py
# So ../models resolves to  .../nyayagpt-lite/models/
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_ADAPTER_PATH = os.path.join(_BACKEND_DIR, "..", "models")

LORA_ADAPTER_PATH: str = os.path.normpath(
    os.getenv("LORA_ADAPTER_PATH", _DEFAULT_ADAPTER_PATH)
)

# Base model must match exactly what was used during fine-tuning.
# Your Kaggle notebook uses: mistralai/Mistral-7B-Instruct-v0.2
BASE_MODEL_ID: str = os.getenv(
    "BASE_MODEL_ID",
    "mistralai/Mistral-7B-Instruct-v0.2",
)

# ---------------------------------------------------------------------------
# Generation parameters — conservative for reliable legal explanation output
# ---------------------------------------------------------------------------
MAX_NEW_TOKENS: int = 512
# bfloat16 matches training compute dtype (BNB_4BIT_COMPUTE_DTYPE = "bfloat16")
# Using float16 here instead would cause a dtype mismatch warning
COMPUTE_DTYPE_STR: str = "bfloat16"

# ---------------------------------------------------------------------------
# Safety system prompt — injected server-side into every inference call.
# Users cannot override or remove this. It enforces the same guardrails
# that were baked into training data but adds a runtime layer of safety.
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are NyayaGPT Lite, an AI assistant that helps Indian citizens
understand their legal documents in plain, simple language.

STRICT RULES — follow without exception:
1. EXPLAIN ONLY. Describe what the document says. Do NOT give legal advice.
2. NO VERDICT PREDICTION. Never say who will win or lose a case.
3. SUGGEST only: consulting a qualified lawyer, approaching Lok Adalat,
   or applying for free legal aid. Nothing beyond this.
4. Use simple, everyday language. Avoid legal jargon.
5. Do NOT repeat sensitive personal information verbatim — paraphrase it.
6. Always end your response with this exact disclaimer:
   "DISCLAIMER: This is a simplified explanation for understanding only.
   It is not legal advice. Please consult a qualified lawyer."

Structure your response under these headings:
Case Summary
Parties Involved
Current Stage
What Usually Happens Next
Available Options
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_model() -> None:
    """
    Attempt to load tokenizer + base model + LoRA adapter at application startup.

    Call this once from FastAPI's lifespan startup hook (see main.py).
    This function NEVER raises — every failure path is caught and logged.
    On any failure, MODEL_AVAILABLE stays False and the app uses
    deterministic fallback logic automatically.

    Failure modes handled:
      • models/ folder missing or empty
      • torch / transformers / peft / bitsandbytes not installed
      • No CUDA GPU available (7B model is impractical on CPU)
      • Base model download fails (no internet, disk full)
      • LoRA adapter incompatible with base model
      • Any other unexpected exception
    """
    global MODEL_AVAILABLE, _model, _tokenizer

    # ── Guard 1: adapter directory ─────────────────────────────────────────
    # Check this before importing torch so startup is instant on CPU servers.
    logger.info("Looking for LoRA adapter at: %s", LORA_ADAPTER_PATH)
    adapter_config = os.path.join(LORA_ADAPTER_PATH, "adapter_config.json")
    adapter_weights = os.path.join(LORA_ADAPTER_PATH, "adapter_model.safetensors")

    if not os.path.isdir(LORA_ADAPTER_PATH):
        logger.warning(
            "Adapter directory not found: '%s'\n"
            "  Expected layout:\n"
            "    nyayagpt-lite/models/adapter_model.safetensors\n"
            "    nyayagpt-lite/models/adapter_config.json\n"
            "    nyayagpt-lite/models/tokenizer.json\n"
            "  Download these from your Kaggle output: nyayagpt-mistral-lora/final/\n"
            "  Starting in FALLBACK mode.",
            LORA_ADAPTER_PATH,
        )
        return

    if not os.path.isfile(adapter_config):
        logger.warning(
            "adapter_config.json missing in '%s'. "
            "Re-download the full output folder from Kaggle. "
            "Starting in FALLBACK mode.",
            LORA_ADAPTER_PATH,
        )
        return

    if not os.path.isfile(adapter_weights):
        logger.warning(
            "adapter_model.safetensors missing in '%s'. "
            "The file is ~80 MB — it may not have downloaded completely. "
            "Starting in FALLBACK mode.",
            LORA_ADAPTER_PATH,
        )
        return

    # ── Guard 2: optional ML dependencies ─────────────────────────────────
    # Deferred import so the app starts without them if they're absent.
    try:
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
        from peft import PeftModel
    except ImportError as exc:
        logger.warning(
            "ML libraries not installed (%s).\n"
            "  Install them with:\n"
            "    pip install torch transformers peft bitsandbytes accelerate\n"
            "  Starting in FALLBACK mode.",
            exc,
        )
        return

    # ── Guard 3: GPU availability ──────────────────────────────────────────
    # Mistral-7B in 4-bit needs ~5-6 GB VRAM. Running on CPU would take
    # minutes per request and appear broken to users.
    if not torch.cuda.is_available():
        logger.warning(
            "No CUDA GPU detected. Mistral-7B inference on CPU is impractically slow.\n"
            "  If you have a GPU, check your CUDA / driver installation.\n"
            "  Starting in FALLBACK mode."
        )
        return

    gpu_name = torch.cuda.get_device_name(0)
    vram_gb = torch.cuda.get_device_properties(0).total_memory / 1024 ** 3
    logger.info("GPU detected: %s (%.1f GB VRAM)", gpu_name, vram_gb)

    if vram_gb < 5.0:
        logger.warning(
            "GPU has only %.1f GB VRAM. Minimum ~5 GB needed for 4-bit Mistral-7B. "
            "Starting in FALLBACK mode.",
            vram_gb,
        )
        return

    # ── Step 1: load tokenizer ─────────────────────────────────────────────
    # Three attempts in order of preference:
    #
    # Attempt A — local models/ folder, fast tokenizer
    #   Works when tokenizer_config.json is compatible with installed transformers.
    #
    # Attempt B — local models/ folder, slow (pure-Python) tokenizer
    #   The tokenizer_config.json saved by Kaggle notebooks sometimes references
    #   "TokenizersBackend" which only exists in newer transformers builds.
    #   use_fast=False bypasses that class lookup entirely and uses the
    #   pure-Python SentencePiece tokenizer instead — always compatible.
    #
    # Attempt C — load directly from HuggingFace Hub
    #   If the local tokenizer files are corrupted or incompatible, fall back
    #   to the canonical Mistral tokenizer from the Hub. Requires internet on
    #   first run but is cached after that (~3 MB, fast).
    #
    tokenizer = None
    tokenizer_source = None

    for attempt, (source, kwargs) in enumerate([
        ("local fast",  {"pretrained_model_name_or_path": LORA_ADAPTER_PATH,  "use_fast": True}),
        ("local slow",  {"pretrained_model_name_or_path": LORA_ADAPTER_PATH,  "use_fast": False}),
        ("hub",         {"pretrained_model_name_or_path": BASE_MODEL_ID,       "use_fast": False}),
    ], start=1):
        try:
            logger.info("Tokenizer attempt %d/3 (%s)...", attempt, source)
            tokenizer = AutoTokenizer.from_pretrained(
                trust_remote_code=False,
                **kwargs,
            )
            tokenizer_source = source
            logger.info("Tokenizer loaded via '%s'. Vocab size: %d",
                        source, tokenizer.vocab_size)
            break
        except Exception as exc:
            logger.warning("Tokenizer attempt %d (%s) failed: %s", attempt, source, exc)

    if tokenizer is None:
        logger.warning(
            "All 3 tokenizer loading attempts failed.\n"
            "  This is unexpected. Check that transformers is installed correctly.\n"
            "  Starting in FALLBACK mode."
        )
        return

    # Mistral tokenizer has no pad token by default — use eos as pad.
    # This matches how your Kaggle training notebook configured it.
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id
        logger.debug("Set pad_token = eos_token ('%s')", tokenizer.eos_token)

    # ── Step 2: load base model in 4-bit ──────────────────────────────────
    # The base model is NOT in your models/ folder — it is downloaded from
    # HuggingFace Hub on first run (~14 GB) and cached for future runs.
    # Quantisation config must match training: 4-bit NF4, bfloat16 compute.
    try:
        logger.info(
            "Loading base model '%s' in 4-bit NF4 quantisation...\n"
            "  First run will download ~14 GB — this is normal.",
            BASE_MODEL_ID,
        )

        # Map compute dtype string to torch dtype
        _dtype_map = {"bfloat16": "torch.bfloat16", "float16": "torch.float16"}
        compute_dtype = (
            torch.bfloat16
            if COMPUTE_DTYPE_STR == "bfloat16"
            else torch.float16
        )

        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",           # matches training notebook
            bnb_4bit_use_double_quant=True,       # saves ~0.4 bits/param extra
            bnb_4bit_compute_dtype=compute_dtype, # bfloat16 — matches training
        )

        base_model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL_ID,
            quantization_config=bnb_config,
            device_map="auto",       # spreads layers across GPU (and CPU if needed)
            trust_remote_code=False, # never execute remote code
            low_cpu_mem_usage=True,  # stream weights to reduce peak RAM during load
        )
        logger.info("Base model loaded successfully.")
    except Exception as exc:
        logger.warning(
            "Base model failed to load: %s\n"
            "  Common causes:\n"
            "    - No internet connection (first run needs HF Hub access)\n"
            "    - Insufficient disk space (need ~20 GB free)\n"
            "    - Insufficient VRAM (need ~5-6 GB)\n"
            "    - bitsandbytes not installed correctly for your CUDA version\n"
            "  Starting in FALLBACK mode.",
            exc,
        )
        return

    # ── Step 3: apply LoRA adapter ─────────────────────────────────────────
    # This is what makes it NyayaGPT — the legal explanation fine-tuning.
    try:
        logger.info("Applying LoRA adapter from: %s", LORA_ADAPTER_PATH)
        model = PeftModel.from_pretrained(
            base_model,
            LORA_ADAPTER_PATH,
            is_trainable=False,  # inference only, no gradients
        )
        model.eval()
        logger.info("LoRA adapter applied. Model is in eval mode.")
    except Exception as exc:
        logger.warning(
            "LoRA adapter failed to apply: %s\n"
            "  This usually means the adapter was trained on a different base model.\n"
            "  Your adapter was trained on: mistralai/Mistral-7B-Instruct-v0.2\n"
            "  Make sure BASE_MODEL_ID matches exactly.\n"
            "  Starting in FALLBACK mode.",
            exc,
        )
        return

    # ── Commit — only reached if all three steps succeeded ─────────────────
    _tokenizer = tokenizer
    _model = model
    MODEL_AVAILABLE = True
    logger.info(
        "NyayaGPT LLM inference is ENABLED. "
        "GPU: %s | Adapter: %s",
        gpu_name,
        LORA_ADAPTER_PATH,
    )


def run_inference(document_text: str, language: str, doc_type: str) -> Optional[str]:
    """
    Run fine-tuned Mistral inference for a single document.

    Returns:
        str  — the model's plain-text explanation if inference succeeds.
        None — if inference fails for any reason (caller uses fallback).

    This function NEVER raises. GPU OOM, CUDA errors, decode errors are all
    caught, logged with full traceback, and converted to a None return.
    The safety system prompt is assembled server-side and cannot be
    altered by user input.
    """
    if not MODEL_AVAILABLE or _model is None or _tokenizer is None:
        # Defensive check — main.py should not call this when MODEL_AVAILABLE is False
        return None

    try:
        import torch

        # ── Build prompt ───────────────────────────────────────────────────
        lang_instruction = (
            "Provide the explanation in simple Hindi (Devanagari script)."
            if language == "hindi"
            else "Provide the explanation in simple English."
        )

        # Truncate document to avoid exceeding context window.
        # Mistral supports 32k tokens but we cap at ~2500 chars to:
        #   (a) keep VRAM usage predictable
        #   (b) stay within MAX_SEQ_LENGTH=1024 set during training
        MAX_DOC_CHARS = 2500
        doc_text = document_text[:MAX_DOC_CHARS]
        if len(document_text) > MAX_DOC_CHARS:
            doc_text += "\n[Document truncated]"

        user_content = (
            f"Document Type: {doc_type}\n\n"
            f"Legal Document Text:\n{doc_text}\n\n"
            f"{lang_instruction}"
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_content},
        ]

        # Use tokenizer's chat template if present (saved by your Kaggle notebook
        # as chat_template.jinja) — otherwise fall back to Mistral's [INST] format.
        try:
            prompt = _tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        except Exception:
            # Manual Mistral Instruct v0.2 format as fallback
            prompt = (
                f"<s>[INST] {SYSTEM_PROMPT}\n\n{user_content} [/INST]"
            )

        # ── Tokenise ───────────────────────────────────────────────────────
        inputs = _tokenizer(
            prompt,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=1024,   # matches MAX_SEQ_LENGTH from training
        ).to(_model.device)

        input_len = inputs["input_ids"].shape[1]
        logger.debug("Prompt token length: %d", input_len)

        # ── Generate ───────────────────────────────────────────────────────
        with torch.no_grad():
            output_ids = _model.generate(
                **inputs,
                max_new_tokens=MAX_NEW_TOKENS,
                do_sample=True,
                temperature=0.3,         # low = more focused, less hallucination
                top_p=0.9,               # nucleus sampling
                repetition_penalty=1.1,  # mild penalty against repetitive output
                pad_token_id=_tokenizer.eos_token_id,
                eos_token_id=_tokenizer.eos_token_id,
            )

        # ── Decode — strip prompt tokens from output ───────────────────────
        new_ids = output_ids[0][input_len:]
        explanation = _tokenizer.decode(new_ids, skip_special_tokens=True).strip()

        if not explanation:
            logger.warning("Model returned empty string. Using fallback.")
            return None

        logger.info("LLM inference complete. Output length: %d chars.", len(explanation))
        return explanation

    except Exception as exc:
        # Catch GPU OOM, CUDA device-side assertion errors, etc.
        # Log the full stack trace for debugging without crashing the request.
        logger.error(
            "LLM inference failed at runtime: %s — falling back to deterministic logic.",
            exc,
            exc_info=True,
        )
        return None


def get_model_status() -> dict:
    """Return a status dict for the /health and /api/model-status endpoints."""
    return {
        "llm_available": MODEL_AVAILABLE,
        "inference_mode": "llm" if MODEL_AVAILABLE else "fallback",
        "adapter_path": LORA_ADAPTER_PATH,
        "base_model": BASE_MODEL_ID if MODEL_AVAILABLE else "not loaded",
    }
