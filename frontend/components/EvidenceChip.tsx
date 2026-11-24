import type { FlagItem } from "@/lib/types";

/**
 * The recurring visual signature of the platform: every claim gets a
 * small ledger-style citation tag, styled after a footnote marker rather
 * than a generic "source" badge. Verified citations (the document/page or
 * period actually appeared in what the model was given) render in teal;
 * anything the backend couldn't verify renders in amber with a flag,
 * rather than being hidden.
 */
export default function EvidenceChip({ flag }: { flag: FlagItem }) {
  const label =
    flag.source_type === "document"
      ? `p.${flag.page_number ?? "?"}`
      : flag.period ?? "financial data";

  if (!flag.citation_verified) {
    return (
      <span
        className="inline-flex items-center gap-1 rounded-sm border border-amber/40 bg-amber-soft px-1.5 py-0.5 text-[11px] font-mono text-amber"
        title="This citation could not be matched against the data the model was actually given. Treat with caution."
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
