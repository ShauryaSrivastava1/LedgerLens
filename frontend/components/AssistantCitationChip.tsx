import type { AssistantCitation } from "@/lib/types";

/**
 * Assistant equivalent of EvidenceChip — same footnote-style visual
 * language (teal = verified against what was actually retrieved, amber =
 * couldn't be verified, shown rather than hidden), adapted for
 * AssistantCitation's shape (reference text instead of statement/evidence).
 */
export default function AssistantCitationChip({ citation }: { citation: AssistantCitation }) {
  const label =
    citation.source_type === "document"
      ? `p.${citation.page_number ?? "?"}`
      : citation.period ?? "financial data";

  if (!citation.citation_verified) {
    return (
      <span
        className="inline-flex items-center gap-1 rounded-sm border border-amber/40 bg-amber-soft px-1.5 py-0.5 text-[11px] font-mono text-amber"
        title="This citation could not be matched against the data actually retrieved for this question. Treat with caution."
      >
        ⚠ {label} unverified
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1 rounded-sm border border-teal/30 bg-teal-soft px-1.5 py-0.5 text-[11px] font-mono text-teal">
      [{label}]
    </span>
  );
}
