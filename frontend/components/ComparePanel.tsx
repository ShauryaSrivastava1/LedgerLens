"use client";

import { useState } from "react";
import { api, APIError } from "@/lib/api";
import type { Company, ComparisonRow } from "@/lib/types";
import { formatCrore, formatPercent, formatNumber } from "@/lib/format";

export default function ComparePanel({ companies }: { companies: Company[] }) {
  const [selected, setSelected] = useState<string[]>([]);
  const [rows, setRows] = useState<ComparisonRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function toggle(symbol: string) {
    setSelected((prev) => (prev.includes(symbol) ? prev.filter((s) => s !== symbol) : [...prev, symbol]));
  }

  async function handleCompare() {
    setError(null);
    if (selected.length < 2) {
      setError("Select at least 2 companies to compare.");
      return;
    }
    setLoading(true);
    try {
      const response = await api.compareCompanies(selected);
      setRows(response.rows);
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Comparison failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="flex flex-wrap gap-2 mb-4">
        {companies.map((c) => (
          <button
            key={c.id}
            onClick={() => toggle(c.symbol)}
            className={`rounded border px-2.5 py-1 text-xs font-mono transition-colors ${
              selected.includes(c.symbol)
                ? "border-ink bg-ink text-paper"
                : "border-line text-ink-soft hover:border-ink/40"
            }`}
          >
            {c.symbol}
          </button>
        ))}
      </div>

      <button
        onClick={handleCompare}
        disabled={loading}
        className="rounded bg-ink text-paper px-3 py-1.5 text-sm hover:bg-ink-soft transition-colors disabled:opacity-50 mb-6"
      >
        {loading ? "Comparing…" : "Compare selected"}
      </button>

      {error && <p className="text-sm text-rust mb-4">{error}</p>}

      {rows && <CompareTable rows={rows} />}
    </div>
  );
}

const METRIC_ROWS: { label: string; key: keyof ComparisonRow; format: (v: unknown) => string }[] = [
  { label: "Latest period", key: "latest_period_label", format: (v) => (v as string) ?? "—" },
  { label: "Revenue", key: "revenue", format: (v) => formatCrore(v as string | null) },
  { label: "Revenue growth", key: "revenue_growth_pct", format: (v) => (v === null ? "—" : `${(v as number).toFixed(1)}%`) },
  { label: "PAT", key: "pat", format: (v) => formatCrore(v as string | null) },
  { label: "PAT growth", key: "pat_growth_pct", format: (v) => (v === null ? "—" : `${(v as number).toFixed(1)}%`) },
  { label: "ROCE", key: "roce", format: (v) => formatPercent(v as string | null) },
  { label: "ROE", key: "roe", format: (v) => formatPercent(v as string | null) },
  { label: "EBITDA margin", key: "ebitda_margin", format: (v) => formatPercent(v as string | null) },
  { label: "Debt / Equity", key: "debt_equity", format: (v) => formatNumber(v as string | null, 2) },
  { label: "Promoter holding", key: "promoter_holding_pct", format: (v) => formatPercent(v as string | null) },
  { label: "Pledge", key: "pledge_pct", format: (v) => formatPercent(v as string | null) },
  { label: "Overall score (AI)", key: "overall_score", format: (v) => formatNumber(v as string | null, 0) },
  { label: "Moat score (AI)", key: "moat_score", format: (v) => formatNumber(v as string | null, 0) },
  { label: "Governance score (AI)", key: "governance_score", format: (v) => formatNumber(v as string | null, 0) },
];

function CompareTable({ rows }: { rows: ComparisonRow[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="border-b border-line">
            <th className="text-left font-normal text-ink-faint py-2 pr-4 text-[11px] uppercase tracking-wide">
              Metric
            </th>
            {rows.map((r) => (
              <th key={r.company_id} className="text-right font-normal py-2 pl-4 min-w-[140px]">
                <div className="font-mono text-ink-soft text-xs">{r.symbol}</div>
                <div className="font-display text-sm normal-case">{r.name}</div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {METRIC_ROWS.map((row) => (
            <tr key={row.key as string} className="border-b border-line/60">
              <td className="py-1.5 pr-4 text-ink-soft">{row.label}</td>
              {rows.map((r) => (
                <td key={r.company_id} className="py-1.5 pl-4 text-right font-mono tabular">
                  {row.format(r[row.key])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
