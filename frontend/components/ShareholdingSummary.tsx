import type { ShareholdingPattern } from "@/lib/types";
import { formatPercent, formatDate } from "@/lib/format";

export default function ShareholdingSummary({ records }: { records: ShareholdingPattern[] }) {
  if (records.length === 0) {
    return <p className="text-sm text-ink-faint py-3">No shareholding pattern data on file yet.</p>;
  }

  const latest = records[0];
  const pledge = latest.pledge_pct ? parseFloat(latest.pledge_pct) : 0;

  return (
    <div className="flex flex-wrap gap-3">
      <Stat label="Promoter holding" value={formatPercent(latest.promoter_holding_pct)} />
      <Stat
        label="Pledge"
        value={formatPercent(latest.pledge_pct)}
        warn={pledge > 0}
      />
      <Stat label="Institutions" value={formatPercent(latest.institution_holding_pct)} />
      <Stat label="As of" value={formatDate(latest.period_end_date)} mono={false} />
    </div>
  );
}

function Stat({ label, value, warn, mono = true }: { label: string; value: string; warn?: boolean; mono?: boolean }) {
  return (
    <div className={`rounded border px-3 py-2 ${warn ? "border-rust/30 bg-rust-soft" : "border-line bg-paper-raised"}`}>
      <div className="text-[10px] uppercase tracking-wide text-ink-faint">{label}</div>
      <div className={`${mono ? "font-mono" : ""} text-sm tabular ${warn ? "text-rust" : "text-ink"}`}>{value}</div>
    </div>
  );
}
