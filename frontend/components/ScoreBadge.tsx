export default function ScoreBadge({ label, value }: { label: string; value: string | number | null }) {
  const numeric = value === null ? null : typeof value === "string" ? parseFloat(value) : value;

  let colorClass = "text-ink-faint bg-line/40 border-line";
  if (numeric !== null && !Number.isNaN(numeric)) {
    if (numeric >= 66) colorClass = "text-teal bg-teal-soft border-teal/30";
    else if (numeric >= 40) colorClass = "text-amber bg-amber-soft border-amber/30";
    else colorClass = "text-rust bg-rust-soft border-rust/30";
  }

  return (
    <div className={`rounded border px-3 py-2 ${colorClass}`}>
      <div className="text-[10px] uppercase tracking-wide opacity-70">{label}</div>
      <div className="font-mono text-lg tabular leading-tight">
        {numeric === null || Number.isNaN(numeric) ? "—" : numeric.toFixed(0)}
      </div>
    </div>
  );
}
