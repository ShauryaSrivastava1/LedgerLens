import type { FlagItem } from "@/lib/types";
import EvidenceChip from "./EvidenceChip";

export default function FlagCard({ flag, tone }: { flag: FlagItem; tone: "green" | "red" }) {
  const border = tone === "green" ? "border-l-teal" : "border-l-rust";
  return (
    <div className={`border-l-2 ${border} pl-3 py-1.5`}>
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm leading-snug">{flag.statement}</p>
        <EvidenceChip flag={flag} />
      </div>
      <p className="text-xs text-ink-faint mt-1">{flag.evidence}</p>
    </div>
  );
}
