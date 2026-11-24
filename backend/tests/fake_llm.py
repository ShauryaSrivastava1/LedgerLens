"""
Deterministic fake LLM for tests. Never makes a network call. By default
returns a well-formed report referencing whatever document_id/period
strings appear in the prompt it's given, so citation-verification tests
can exercise both the "verified" and "unverified" paths deterministically.
"""

import re

from app.services.llm.base import LLMClient


class FakeLLMClient(LLMClient):
    def __init__(self, canned_response: str | None = None):
        self._canned_response = canned_response
        self.last_system_prompt: str | None = None
        self.last_user_prompt: str | None = None

    def complete(self, system_prompt: str, user_prompt: str, max_tokens: int = 4096) -> str:
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt

        if self._canned_response is not None:
            return self._canned_response

        # Milestone 9's assistant system prompt asks for a different JSON
        # shape (answer/citations/confidence/insufficient_evidence) than
        # report generation's (scores/flags/...). "insufficient_evidence"
        # only appears in the assistant's schema, so it's a reliable way
        # to tell the two prompts apart without threading an extra flag
        # through LLMClient's provider-agnostic interface.
        if "insufficient_evidence" in system_prompt:
            return self._complete_assistant(user_prompt)
        return self._complete_report(user_prompt)

    def _complete_assistant(self, user_prompt: str) -> str:
        import json

        doc_match = re.search(r"document_id=([0-9a-fA-F-]+)", user_prompt)
        document_id = doc_match.group(1) if doc_match else None
        page_match = re.search(r"page=(\d+)", user_prompt)
        page_number = int(page_match.group(1)) if page_match else None

        period_match = re.search(r"Period: (.+?) \|", user_prompt)
        period = period_match.group(1) if period_match else None

        citations = []
        if document_id:
            citations.append(
                {
                    "source_type": "document",
                    "document_id": document_id,
                    "page_number": page_number,
                    "period": None,
                    "reference": "Retrieved document excerpt",
                    "confidence": 0.75,
                }
            )
        if period:
            citations.append(
                {
                    "source_type": "financial_metric",
                    "document_id": None,
                    "page_number": None,
                    "period": period,
                    "reference": "Financial metric for the period",
                    "confidence": 0.7,
                }
            )

        if not citations:
            answer = {
                "answer": "I don't have enough evidence on this platform to answer that.",
                "citations": [],
                "confidence": 0.0,
                "insufficient_evidence": True,
            }
        else:
            answer = {
                "answer": "This is a deterministic test answer grounded in the retrieved evidence.",
                "citations": citations,
                "confidence": 0.72,
                "insufficient_evidence": False,
            }
        return json.dumps(answer)

    def _complete_report(self, user_prompt: str) -> str:
        # Pull a real document_id and period out of the prompt so the
        # generated flags are citation-verifiable against the actual context.
        doc_match = re.search(r"document_id=([0-9a-fA-F-]+)", user_prompt)
        document_id = doc_match.group(1) if doc_match else None
        page_match = re.search(r"page=(\d+)", user_prompt)
        page_number = int(page_match.group(1)) if page_match else None

        period_match = re.search(r"Period: (.+?) \|", user_prompt)
        period = period_match.group(1) if period_match else None

        green_flags = []
        if document_id:
            green_flags.append(
                {
                    "statement": "The company highlights a durable distribution moat.",
                    "evidence": "Excerpt describes strong distribution network.",
                    "source_type": "document",
                    "document_id": document_id,
                    "page_number": page_number,
                    "period": None,
                    "confidence": 0.8,
                }
            )
        if period:
            green_flags.append(
                {
                    "statement": "ROCE is healthy for the period.",
                    "evidence": "ROCE figure from financial metrics.",
                    "source_type": "financial_metric",
                    "document_id": None,
                    "page_number": None,
                    "period": period,
                    "confidence": 0.7,
                }
            )

        red_flags = [
            {
                "statement": "A figure was cited that does not appear in the provided context.",
                "evidence": "This should fail citation verification.",
                "source_type": "document",
                "document_id": "not-a-real-document-id",
                "page_number": 999,
                "period": None,
                "confidence": 0.5,
            }
        ]

        report = {
            "scores": {
                "overall": 70, "financial_health": 72, "growth": 65, "profitability": 68,
                "governance": 75, "moat": 80, "valuation": 60, "risk": 40, "confidence": 0.66,
            },
            "green_flags": green_flags,
            "red_flags": red_flags,
            "questions_investors_should_ask": ["How sustainable is the current margin trend?"],
            "things_to_verify": ["Confirm the latest promoter pledge percentage."],
            "potential_risks": ["Sector-wide demand slowdown."],
            "summary": "This is a deterministic test summary, not a real analysis.",
        }
        import json

        return json.dumps(report)

    @property
    def provider_name(self) -> str:
        return "fake"

    @property
    def model_name(self) -> str:
        return "fake-model-v1"
