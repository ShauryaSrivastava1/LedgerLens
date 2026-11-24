import type { FinancialMetric } from "@/lib/types";
import { formatCrore, formatPercent, formatNumber } from "@/lib/format";

const ROWS: { label: string; key: keyof FinancialMetric; format: (v: string | null) => string }[] = [
  { label: "Revenue", key: "revenue", format: formatCrore },
  { label: "PAT", key: "pat", format: formatCrore },
  { label: "EBITDA margin", key: "ebitda_margin", format: formatPercent },
  { label: "Net margin", key: "net_margin", format: formatPercent },
  { label: "ROCE", key: "roce", format: formatPercent },
  { label: "ROE", key: "roe", format: formatPercent },
  { label: "Debt / Equity", key: "debt_equity", format: (v) => formatNumber(v, 2) },
  { label: "Free cash flow", key: "free_cash_flow", format: formatCrore },
  { label: "Receivable days", key: "receivable_days", format: (v) => formatNumber(v, 0) },
];

export default function MetricsTable({ metrics }: { metrics: FinancialMetric[] }) {
  if (metrics.length === 0) {
    return (
      <p className="text-sm text-ink-faint py-3">
        No financial metrics on file yet. Upload a document or add metrics manually via the API.
      </p>
    );
  }

  const periods = metrics.slice(0, 6); // most recent first, capped for width

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="border-b border-line">
            <th className="text-left font-normal text-ink-faint py-2 pr-4 text-[11px] uppercase tracking-wide">
              Metric
            </th>
            {periods.map((m) => (
              <th
                key={m.id}
                className="text-right font-normal text-ink-faint py-2 pl-4 text-[11px] uppercase tracking-wide whitespace-nowrap"
              >
                {m.fiscal_year}
                <div className="text-[10px] normal-case">{m.period_type}</div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {ROWS.map((row) => (
            <tr key={row.key as string} className="border-b border-line/60">
              <td className="py-1.5 pr-4 text-ink-soft">{row.label}</td>
              {periods.map((m) => (
                <td key={m.id} className="py-1.5 pl-4 text-right font-mono tabular">
                  {row.format(m[row.key] as string | null)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
