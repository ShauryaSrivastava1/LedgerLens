"""
Schema the LLM's JSON output is validated against, plus citation
verification against what was actually retrieved.

This exists specifically to enforce "every conclusion must cite evidence"
and "no black-box decisions" beyond just asking nicely in the prompt: a
flag whose document_id/period doesn't match anything we actually gave the
model as context gets marked unverified rather than trusted, because a
prompt instruction is not a guarantee.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class FlagSourceType(str, Enum):
    DOCUMENT = "document"
    FINANCIAL_METRIC = "financial_metric"


class LLMFlagItem(BaseModel):
    statement: str
    evidence: str
    source_type: FlagSourceType
    document_id: Optional[str] = None
    page_number: Optional[int] = None
    period: Optional[str] = None
    confidence: float = Field(ge=0, le=1)


class LLMReportScores(BaseModel):
    overall: float = Field(ge=0, le=100)
    financial_health: float = Field(ge=0, le=100)
    growth: float = Field(ge=0, le=100)
    profitability: float = Field(ge=0, le=100)
    governance: float = Field(ge=0, le=100)
    moat: float = Field(ge=0, le=100)
    valuation: float = Field(ge=0, le=100)
    risk: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)


class LLMReportOutput(BaseModel):
    scores: LLMReportScores
    green_flags: list[LLMFlagItem] = []
    red_flags: list[LLMFlagItem] = []
    questions_investors_should_ask: list[str] = []
    things_to_verify: list[str] = []
    potential_risks: list[str] = []
    summary: str


def _citation_is_verified(
    source_type: FlagSourceType,
    document_id: Optional[str],
    period: Optional[str],
    known_document_ids: set[str],
    known_periods: set[str],
) -> bool:
    """
    The one place that decides whether a claimed citation actually matches
    what was retrieved and sent to the model. Shared by both AI-report flag
    verification (Milestone 3) and AI-assistant citation verification
    (Milestone 9) so "what counts as verified" can never quietly drift
    between the two call sites.
    """
    if source_type == FlagSourceType.DOCUMENT:
        return document_id in known_document_ids
    elif source_type == FlagSourceType.FINANCIAL_METRIC:
        return period in known_periods
    return False


def verify_and_annotate_flags(
    flags: list[LLMFlagItem],
    known_document_ids: set[str],
    known_periods: set[str],
) -> list[dict]:
    """
    Cross-checks each flag's citation against what was actually included
    in the context sent to the model. Returns plain dicts (ready for JSON
    storage) with an added `citation_verified` field — never silently
    drops an unverifiable flag, since that's information the reviewer
    needs, not something to hide.
    """
    annotated = []
    for flag in flags:
        verified = _citation_is_verified(
            flag.source_type, flag.document_id, flag.period, known_document_ids, known_periods
        )
        item = flag.model_dump()
        item["citation_verified"] = verified
        annotated.append(item)
    return annotated


# ============================================================
# Milestone 9: AI Assistant
# ============================================================
#
# Same citation-verification principle as above ("a prompt instruction is
# not a guarantee — check it in code"), applied to single-question answers
# instead of report flags. The shape is smaller (no statement/evidence
# text, just what's being cited and why) since an assistant answer is one
# piece of prose with supporting citations, not a list of discrete flags.

class AssistantCitationItem(BaseModel):
    source_type: FlagSourceType
    document_id: Optional[str] = None
    page_number: Optional[int] = None
    period: Optional[str] = None
    reference: str  # short description of what this citation supports, e.g. "ROCE figure"
    confidence: float = Field(ge=0, le=1)


class AssistantAnswerOutput(BaseModel):
    answer: str
    citations: list[AssistantCitationItem] = []
    confidence: float = Field(ge=0, le=1)
    # The model's own signal that the retrieved context didn't answer the
    # question. Not trusted blindly — answer_question() in assistant.py
    # also independently forces this when zero citations verify — but
    # having the model state it explicitly lets it decline cleanly rather
    # than padding an answer with unsupported generalities.
    insufficient_evidence: bool = False


def verify_and_annotate_citations(
    citations: list[AssistantCitationItem],
    known_document_ids: set[str],
    known_periods: set[str],
) -> list[dict]:
    """
    Assistant equivalent of verify_and_annotate_flags: cross-checks each
    citation against the document IDs and financial periods actually
    retrieved for this question, and returns annotated dicts. Never drops
    an unverifiable citation — the caller decides what to do with an
    answer that has none verified (see assistant.answer_question).
    """
    annotated = []
    for citation in citations:
        verified = _citation_is_verified(
            citation.source_type,
            citation.document_id,
            citation.period,
            known_document_ids,
            known_periods,
        )
        item = citation.model_dump()
        item["citation_verified"] = verified
        annotated.append(item)
    return annotated
