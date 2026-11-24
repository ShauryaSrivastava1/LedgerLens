"use client";

import { useState } from "react";
import { api, APIError } from "@/lib/api";
import type { AssistantAnswer } from "@/lib/types";
import AssistantCitationChip from "./AssistantCitationChip";

const EXAMPLE_QUESTIONS = [
  "What are the biggest red flags for this company?",
  "How is the company's governance record?",
  "What does the evidence say about its competitive moat?",
];

/**
 * Grounded Q&A for a single company. Deliberately stateless on the
 * frontend too, not just the API: each question is sent on its own, with
 * no prior question/answer history attached to the request. The panel
 * only keeps the most recent answer in local state so the person can read
 * it — that's just what's on screen, not a conversation being replayed to
 * the model.
 */
export default function AssistantPanel({ companyId }: { companyId: string }) {
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [answer, setAnswer] = useState<AssistantAnswer | null>(null);

  async function handleAsk(q?: string) {
    const finalQuestion = (q ?? question).trim();
    if (finalQuestion.length < 3) {
      setError("Ask a slightly longer question — at least 3 characters.");
      return;
    }
    setError(null);
    setAsking(true);
    try {
      const result = await api.askAssistant(companyId, finalQuestion);
      setAnswer(result);
      setQuestion(finalQuestion);
    } catch (err) {
      setError(err instanceof APIError ? err.message : "The assistant couldn't answer that.");
      setAnswer(null);
    } finally {
      setAsking(false);
    }
  }

  return (
    <div>
      <p className="text-xs text-ink-faint mb-3">
        Ask a question about this company only. Answers are grounded in its ingested documents
        and financial data, with every claim cited — nothing is answered from general knowledge,
        and nothing is carried over between questions.
      </p>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleAsk();
        }}
        className="flex flex-col sm:flex-row gap-2 mb-3"
      >
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. Why is promoter pledging a concern here?"
          className="flex-1 rounded border border-line px-3 py-1.5 text-sm bg-paper-raised"
          maxLength={1000}
        />
        <button
          type="submit"
          disabled={asking}
          className="rounded bg-ink text-paper px-3 py-1.5 text-sm hover:bg-ink-soft transition-colors disabled:opacity-50 shrink-0"
        >
          {asking ? "Thinking…" : "Ask"}
        </button>
      </form>

      {!answer && (
        <div className="flex flex-wrap gap-2 mb-4">
          {EXAMPLE_QUESTIONS.map((q) => (
            <button
              key={q}
              onClick={() => {
                setQuestion(q);
                handleAsk(q);
              }}
              disabled={asking}
              className="text-[11px] text-ink-faint border border-line rounded-sm px-2 py-1 hover:bg-line/30 disabled:opacity-50"
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {error && <p className="text-sm text-rust mb-3">{error}</p>}

      {answer && <AssistantAnswerDetail answer={answer} />}
    </div>
  );
}

function AssistantAnswerDetail({ answer }: { answer: AssistantAnswer }) {
  return (
    <div className="border-l-2 border-l-line pl-4 space-y-3">
      <div>
        <p className="text-[11px] uppercase tracking-wide text-ink-faint mb-1">Question</p>
        <p className="text-sm italic text-ink-soft">{answer.question}</p>
      </div>

      <div>
        <div className="flex items-center justify-between gap-3 mb-1">
          <p className="text-[11px] uppercase tracking-wide text-ink-faint">Answer</p>
          <span className="text-[11px] text-ink-faint">
            confidence {(answer.confidence * 100).toFixed(0)}%
          </span>
        </div>
        {answer.insufficient_evidence ? (
          <p className="text-sm leading-relaxed text-amber">{answer.answer}</p>
        ) : (
          <p className="text-sm leading-relaxed">{answer.answer}</p>
        )}
      </div>

      {answer.citations.length > 0 && (
        <div>
          <p className="text-[11px] uppercase tracking-wide text-ink-faint mb-2">Citations</p>
          <div className="flex flex-wrap gap-2">
            {answer.citations.map((c, i) => (
              <div key={i} className="flex items-center gap-1.5">
                <AssistantCitationChip citation={c} />
                <span className="text-xs text-ink-faint">{c.reference}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <p className="text-[11px] text-ink-faint">
        {answer.context_snapshot.chunks_retrieved} document excerpt
        {answer.context_snapshot.chunks_retrieved === 1 ? "" : "s"} retrieved for this question.
      </p>
    </div>
  );
}
