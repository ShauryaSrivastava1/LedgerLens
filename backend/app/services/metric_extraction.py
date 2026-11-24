"""
Baseline financial metric extraction: regex patterns over raw page text,
producing *candidates* only — never written directly to FinancialMetric.

This is deliberately conservative. Indian financial documents report
figures in crore/lakh with inconsistent formatting, and a regex has no
real understanding of context (a "Revenue" mentioned in a five-year
comparison table is not the same as this period's revenue). Confidence
scores here are rough heuristics meant to help a human reviewer triage,
not a substitute for their judgment. Replacing this with LLM-assisted
extraction (with the same review gate) is planned for a later milestone.
"""

import re
from dataclasses import dataclass

from app.services.text_extraction import PageText

# Each entry: (metric_name matching FinancialMetric column names, list of label patterns)
_METRIC_PATTERNS: dict[str, list[str]] = {
    "revenue": [r"total\s+revenue(?:\s+from\s+operations)?", r"total\s+income"],
    "pat": [r"profit\s+after\s+tax", r"net\s+profit"],
    "ebitda": [r"ebitda"],
    "roce": [r"roce", r"return\s+on\s+capital\s+employed"],
    "roe": [r"roe", r"return\s+on\s+equity"],
    "debt_equity": [r"debt[\s\-]*(?:to)?[\s\-]*equity\s+ratio"],
}

# Matches a number like "1,234.56" or "1234" possibly followed by a unit word
_NUMBER_RE = r"([\d,]+\.?\d*)\s*(crore|cr\.?|lakh|lakhs|%|percent)?"

# Fiscal-year mentions ("FY26", "FY 2025-26") are digit sequences that sit
# between a metric label and its actual value extremely often in Indian
# financial documents ("ROCE for FY26 was 24.3%"). Left alone, the gap
# regex below stops at the first digit it sees and misreads "26" as the
# metric value. Blanking these tokens out (same length, so char offsets
# used for snippet extraction stay valid) before matching avoids that.
_FISCAL_YEAR_RE = re.compile(r"fy\s?\d{2,4}(-\d{2,4})?", re.IGNORECASE)


def _blank_fiscal_year_mentions(text: str) -> str:
    return _FISCAL_YEAR_RE.sub(lambda m: " " * len(m.group(0)), text)


@dataclass
class MetricCandidate:
    metric_name: str
    extracted_value: float
    unit_note: str | None
    raw_text_snippet: str
    page_number: int
    confidence: float


def _clean_number(raw: str) -> float:
    return float(raw.replace(",", ""))


def extract_candidates(pages: list[PageText]) -> list[MetricCandidate]:
    candidates: list[MetricCandidate] = []

    for page in pages:
        text = page.text
        if not text:
            continue
        lowered = _blank_fiscal_year_mentions(text.lower())

        for metric_name, label_patterns in _METRIC_PATTERNS.items():
            for label_pattern in label_patterns:
                pattern = re.compile(
                    label_pattern + r"[^\d\n]{0,40}" + _NUMBER_RE, re.IGNORECASE
                )
                for match in pattern.finditer(lowered):
                    try:
                        value = _clean_number(match.group(1))
                    except ValueError:
                        continue

                    unit = match.group(2)
                    # Snippet pulled from the original (non-lowercased) text
                    # so the evidence shown to the reviewer is faithful.
                    start = max(0, match.start() - 20)
                    end = min(len(text), match.end() + 20)
                    snippet = text[start:end].strip().replace("\n", " ")

                    # Heuristic confidence: a labeled ratio/percentage metric
                    # found close to its label is fairly reliable; a bare
                    # number after a common label like "revenue" is riskier
                    # because tables list many numbers near that word.
                    confidence = 0.6
                    if unit in ("%", "percent") and metric_name in ("roce", "roe", "debt_equity"):
                        confidence = 0.75
                    if unit in ("crore", "cr", "cr.") and metric_name in ("revenue", "pat", "ebitda"):
                        confidence = 0.65

                    candidates.append(
                        MetricCandidate(
                            metric_name=metric_name,
                            extracted_value=value,
                            unit_note=unit,
                            raw_text_snippet=snippet[:512],
                            page_number=page.page_number,
                            confidence=confidence,
                        )
                    )

    return candidates
