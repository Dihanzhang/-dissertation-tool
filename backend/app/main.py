"""
FastAPI backend — Build Step 2.

Endpoints:
  GET  /api/health
  POST /api/check/text        — Module 2 + 3 (free, deterministic)
  POST /api/check/docx        — Module 2 + 3 on uploaded .docx (free)
  POST /api/review/estimate   — word count + credit cost estimate (no LLM call)
  POST /api/review            — Module 1 (LLM, metered via credits)
"""

from __future__ import annotations

import math
import os
import re
import tempfile
from pathlib import Path

# Load .env in development (no-op if python-dotenv not installed or file absent)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .modules.prose_extractor import ProseParagraph, extract_prose, QUOTE_MASK
from .modules.module2_apa_checker import check_paragraphs, Finding, _load_config
from .modules.module3_citation_matcher import (
    CitationMatchResult,
    run_citation_check,
    run_citation_check_paragraphs,
)
from .modules.module1_editor import run_module1, EditSuggestion
from .modules.text_splitter import count_words, split_into_chunks, estimate_chunks
from .modules import credits as credit_store

app = FastAPI(
    title="Dissertation APA 7 Review API",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_CONFIG_PATH = Path(__file__).parent / "config" / "prof_checklist.yaml"
WORD_CAP = int(os.getenv("WORD_CAP_PER_CREDIT", "5000"))
FREE_TRIAL_CAP = int(os.getenv("FREE_TRIAL_WORD_CAP", "3000"))
TEST_MODE = os.getenv("TEST_MODE", "false").lower() in ("true", "1", "yes")


def _cfg():
    return _load_config(str(_CONFIG_PATH))


# ---------------------------------------------------------------------------
# Pydantic models — check endpoints (Modules 2 + 3)
# ---------------------------------------------------------------------------

class TextCheckRequest(BaseModel):
    body_text: str
    reference_text: str = ""
    levenshtein_threshold: int = 2


class FindingOut(BaseModel):
    rule_id: str
    severity: str
    paragraph_index: int
    message: str
    suggested_fix: str = ""
    autofixable: bool = False
    excerpt: str = ""
    location_hint: str = ""


class CheckResponse(BaseModel):
    apa_findings: list[FindingOut]
    missing_references: list[dict]
    uncited_references: list[dict]
    year_mismatches: list[dict]
    spelling_mismatches: list[dict]
    co_author_only_matches: list[dict]
    scope_warning: str = ""
    stats: dict


# ---------------------------------------------------------------------------
# Pydantic models — review endpoint (Module 1)
# ---------------------------------------------------------------------------

class ReviewRequest(BaseModel):
    body_text: str
    request_id: str
    user_id: str = "anonymous"
    tier: str = "paid"    # "free" | "paid"
    confirmed_oversized: bool = False  # user confirmed multi-credit split


class SuggestionOut(BaseModel):
    original: str
    revised: str
    reason: str
    edit_type: str        # "light" | "heavy"
    change_ratio: float


class ReviewResponse(BaseModel):
    status: str           # "ok" | "oversized_confirmation" | "no_credits" | "error"
    suggestions: list[SuggestionOut] = []
    # Oversized confirmation fields
    word_count: int = 0
    chunk_count: int = 0
    credits_required: int = 0
    credits_remaining: int = 0
    # Stats
    model_used: str = ""
    rejected_by_citation_lock: int = 0
    rejected_sentence_not_found: int = 0
    message: str = ""
    test_mode: bool = False


class EstimateRequest(BaseModel):
    body_text: str
    user_id: str = "anonymous"
    tier: str = "paid"


class EstimateResponse(BaseModel):
    word_count: int
    chunk_count: int
    credits_required: int
    credits_remaining: int
    word_cap_per_credit: int
    free_trial_cap: int
    test_mode: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _finding_to_out(f: Finding) -> FindingOut:
    return FindingOut(
        rule_id=f.rule_id,
        severity=f.severity.value,
        paragraph_index=f.paragraph_index,
        message=f.message,
        suggested_fix=f.suggested_fix,
        autofixable=f.autofixable,
        excerpt=f.excerpt,
        location_hint=f.location_hint,
    )


def _suggestion_to_out(s: EditSuggestion) -> SuggestionOut:
    return SuggestionOut(
        original=s.original,
        revised=s.revised,
        reason=s.reason,
        edit_type=s.edit_type,
        change_ratio=s.change_ratio,
    )


_SENTENCE_END = re.compile(r'[.!?]\s*$')
_LIST_ITEM = re.compile(r'^[\d]+[.)]\s|^[-•*–]\s')
_PAREN_YEAR_IN_TEXT = re.compile(r'\(\d{4}[a-z]?\)')


def _is_likely_heading(text: str) -> bool:
    """
    Heuristic for pasted plain text (no .docx style info): detect heading-like lines.
    Prevents prose rules (P001, N001, etc.) from firing on titles and section headings.

    Matches:
    - ALL-CAPS lines up to 200 chars (common for top-level headings)
    - Short mixed-case lines (≤ 200 chars) with no terminal sentence punctuation
    Excludes list items and lines with parenthetical citation years.
    """
    stripped = text.strip()
    if not stripped:
        return False
    if '\n' in stripped:                        # multi-line → body paragraph
        return False
    if _LIST_ITEM.match(stripped):              # numbered/bulleted list item
        return False
    if _PAREN_YEAR_IN_TEXT.search(stripped):    # contains a citation year → body prose
        return False
    # ALL CAPS short line → heading/title label
    letters = [c for c in stripped if c.isalpha()]
    if letters and all(c.isupper() for c in letters) and len(stripped) <= 200:
        return True
    # Mixed-case: short with no terminal sentence punctuation
    if len(stripped) > 200:
        return False
    if _SENTENCE_END.search(stripped):          # ends with . ! ? → sentence, not heading
        return False
    return True


def _build_paragraphs(text: str) -> list[ProseParagraph]:
    """Build minimal ProseParagraph list from raw text (no .docx structure)."""
    paras = []
    for i, raw in enumerate(text.split("\n\n")):
        raw = raw.strip()
        if not raw:
            continue
        masked = re.sub(r'“[^”]*?”|"[^"]*?"', QUOTE_MASK, raw)
        heading_level = 1 if _is_likely_heading(raw) else None
        paras.append(ProseParagraph(
            index=i,
            style_name="Heading 1" if heading_level else "Normal",
            raw_text=raw,
            masked_text=masked,
            heading_level=heading_level,
            is_reference_entry=False,
        ))
    return paras


def _empty_citation_result(note: str) -> CitationMatchResult:
    return CitationMatchResult(
        citations=[], references=[],
        missing_references=[], uncited_references=[],
        year_mismatches=[], spelling_mismatches=[],
        co_author_only_matches=[], formatting_issues=[],
        scope_warning=note,
    )


# ---------------------------------------------------------------------------
# Endpoints — Modules 2 + 3 (free)
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    return {"status": "ok", "build_step": 2, "test_mode": TEST_MODE}


@app.post("/api/check/text", response_model=CheckResponse)
async def check_text(req: TextCheckRequest):
    """Module 2 + 3 on plain text — free, no LLM."""
    cfg = _cfg()
    prose_cfg = cfg.get("prose_rules", {})
    heading_cfg = cfg.get("heading_rules", {})
    citation_cfg = cfg.get("citation_rules", {})
    threshold = req.levenshtein_threshold or citation_cfg.get("spelling_mismatch_threshold", 2)

    paragraphs = _build_paragraphs(req.body_text)
    apa_findings = check_paragraphs(paragraphs, prose_cfg, heading_cfg)

    citation_result = (
        run_citation_check(req.body_text, req.reference_text, levenshtein_threshold=threshold)
        if req.reference_text
        else _empty_citation_result("No reference list provided — citation matching skipped.")
    )

    return CheckResponse(
        apa_findings=[_finding_to_out(f) for f in apa_findings],
        missing_references=citation_result.missing_references,
        uncited_references=citation_result.uncited_references,
        year_mismatches=citation_result.year_mismatches,
        spelling_mismatches=citation_result.spelling_mismatches,
        co_author_only_matches=citation_result.co_author_only_matches,
        scope_warning=citation_result.scope_warning,
        stats={
            "paragraphs_checked": len(paragraphs),
            "apa_findings_count": len(apa_findings),
            "citations_found": len(citation_result.citations),
            "references_parsed": len(citation_result.references),
        },
    )


@app.post("/api/check/docx", response_model=CheckResponse)
async def check_docx(
    file: UploadFile = File(...),
    reference_text: str = Form(default=""),
    levenshtein_threshold: int = Form(default=2),
):
    """Module 2 + 3 on an uploaded .docx — free. Uploaded file deleted after processing."""
    if not file.filename or not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx files are supported.")

    cfg = _cfg()
    prose_cfg = cfg.get("prose_rules", {})
    heading_cfg = cfg.get("heading_rules", {})
    citation_cfg = cfg.get("citation_rules", {})
    threshold = levenshtein_threshold or citation_cfg.get("spelling_mismatch_threshold", 2)

    content = await file.read()
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        from docx import Document
        doc = Document(tmp_path)
        paragraphs = extract_prose(doc)
        apa_findings = check_paragraphs(paragraphs, prose_cfg, heading_cfg)

        effective_ref = reference_text or "\n".join(
            p.raw_text for p in paragraphs if p.is_reference_entry
        )
        citation_result = (
            run_citation_check_paragraphs(paragraphs, effective_ref, levenshtein_threshold=threshold)
            if effective_ref
            else _empty_citation_result("No reference list found — citation matching skipped.")
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    return CheckResponse(
        apa_findings=[_finding_to_out(f) for f in apa_findings],
        missing_references=citation_result.missing_references,
        uncited_references=citation_result.uncited_references,
        year_mismatches=citation_result.year_mismatches,
        spelling_mismatches=citation_result.spelling_mismatches,
        co_author_only_matches=citation_result.co_author_only_matches,
        scope_warning=citation_result.scope_warning,
        stats={
            "paragraphs_checked": len(paragraphs),
            "apa_findings_count": len(apa_findings),
            "citations_found": len(citation_result.citations),
            "references_parsed": len(citation_result.references),
        },
    )


# ---------------------------------------------------------------------------
# Endpoints — Module 1 (LLM, metered)
# ---------------------------------------------------------------------------

@app.post("/api/review/estimate", response_model=EstimateResponse)
async def review_estimate(req: EstimateRequest):
    """Return word count and credit cost estimate. No LLM call — free."""
    word_count = count_words(req.body_text)
    cap = FREE_TRIAL_CAP if req.tier == "free" else WORD_CAP
    chunks = math.ceil(word_count / cap) if word_count > 0 else 1
    return EstimateResponse(
        word_count=word_count,
        chunk_count=chunks,
        credits_required=chunks,
        credits_remaining=credit_store.get_balance(req.user_id),
        word_cap_per_credit=cap,
        free_trial_cap=FREE_TRIAL_CAP,
        test_mode=TEST_MODE,
    )


@app.post("/api/review", response_model=ReviewResponse)
async def review(req: ReviewRequest):
    """
    Module 1 — LLM-based clarity/voice editing, metered by credits.

    Flow:
    1. Check word count. If oversized and not confirmed → return confirmation prompt.
    2. Check credits.
    3. Split into chunks if oversized and confirmed.
    4. Run Module 1 per chunk; citation-lock each result.
    5. Decrement credit per successful chunk only.
    6. Return merged suggestions. Text is not retained after response.
    """
    is_trial = req.tier == "free"
    word_count = count_words(req.body_text)
    cap = FREE_TRIAL_CAP if is_trial else WORD_CAP
    chunk_count = math.ceil(word_count / cap) if word_count > 0 else 1
    balance = credit_store.get_balance(req.user_id)

    # Oversized: require explicit confirmation before spending multiple credits
    if chunk_count > 1 and not req.confirmed_oversized:
        return ReviewResponse(
            status="oversized_confirmation",
            word_count=word_count,
            chunk_count=chunk_count,
            credits_required=chunk_count,
            credits_remaining=balance,
            message=(
                f"This submission is ~{word_count:,} words and will be split into "
                f"{chunk_count} sections, using {chunk_count} credits. "
                f"You have {balance} credits remaining. Confirm to proceed."
            ),
            test_mode=TEST_MODE,
        )

    # Check if enough credits for all chunks
    if not TEST_MODE and not is_trial and balance < chunk_count:
        return ReviewResponse(
            status="no_credits",
            word_count=word_count,
            chunk_count=chunk_count,
            credits_required=chunk_count,
            credits_remaining=balance,
            message=(
                f"This submission needs {chunk_count} credits but you have {balance}. "
                "Top up to continue."
            ),
            test_mode=TEST_MODE,
        )

    # Credit gate (single-chunk or confirmed oversized)
    status = credit_store.check(
        user_id=req.user_id,
        request_id=req.request_id,
        word_count=min(word_count, cap),  # per-chunk check
        is_trial=is_trial,
    )
    if not status.allowed and not TEST_MODE:
        return ReviewResponse(
            status="no_credits",
            credits_remaining=status.credits_remaining,
            message=_credit_reason_message(status.reason),
            test_mode=TEST_MODE,
        )

    # Split text into chunks
    chunks = split_into_chunks(req.body_text, word_cap=cap)

    # Resolve provider once
    try:
        from .modules.provider import get_provider
        provider = get_provider(tier=req.tier)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))

    all_suggestions: list[SuggestionOut] = []
    total_rejected_lock = 0
    total_rejected_nf = 0
    model_used = ""
    completed_chunks = 0

    for i, chunk in enumerate(chunks):
        chunk_request_id = f"{req.request_id}_chunk{i}"

        try:
            result = run_module1(chunk, provider=provider, tier=req.tier)
        except Exception as e:
            # Partial failure: report how many chunks succeeded
            return ReviewResponse(
                status="error",
                suggestions=all_suggestions,
                message=(
                    f"Error on chunk {i + 1}/{len(chunks)}: {e}. "
                    f"{completed_chunks} chunk(s) processed; credits charged: {completed_chunks}."
                ),
                model_used=model_used,
                rejected_by_citation_lock=total_rejected_lock,
                rejected_sentence_not_found=total_rejected_nf,
                test_mode=TEST_MODE,
            )

        # Decrement credit only after successful chunk
        credit_store.commit(
            user_id=req.user_id,
            request_id=chunk_request_id,
            is_trial=is_trial,
        )
        completed_chunks += 1
        model_used = result.model_used
        total_rejected_lock += result.rejected_by_citation_lock
        total_rejected_nf += result.rejected_sentence_not_found
        all_suggestions.extend(_suggestion_to_out(s) for s in result.suggestions)

    # Text is processed and not retained after this point
    return ReviewResponse(
        status="ok",
        suggestions=all_suggestions,
        word_count=word_count,
        chunk_count=len(chunks),
        credits_required=len(chunks),
        credits_remaining=credit_store.get_balance(req.user_id),
        model_used=model_used,
        rejected_by_citation_lock=total_rejected_lock,
        rejected_sentence_not_found=total_rejected_nf,
        message=f"Review complete. {len(all_suggestions)} suggestion(s) found.",
        test_mode=TEST_MODE,
    )


def _credit_reason_message(reason: str) -> str:
    if reason == "trial_already_used":
        return "Free trial already used. Purchase to continue."
    if reason == "no_credits":
        return "Credits used — top up to continue. APA rule checking remains free."
    if reason == "duplicate_request_id":
        return "This request was already processed."
    return f"Credits unavailable: {reason}"
