"use client";

import { useEffect, useState } from "react";
import { api, APIError, downloadAuthenticatedFile } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import RequireAuth from "@/components/RequireAuth";
import type { Company, PortfolioSummary } from "@/lib/types";
import { formatPercent, formatDate } from "@/lib/format";

export default function PortfolioPage() {
  return (
    <div className="px-8 py-8 max-w-4xl">
      <header className="mb-8">
        <h1 className="font-display text-2xl">Portfolio</h1>
        <p className="text-ink-soft text-sm mt-1">
          Holdings tracked by cost basis — there's no live price feed yet, so allocation reflects money invested, not current value.
        </p>
      </header>
      <RequireAuth>
        <PortfolioContent />
      </RequireAuth>
    </div>
  );
}

function PortfolioContent() {
  const { token } = useAuth();
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ company_id: "", quantity: "", average_buy_price: "", target_allocation_pct: "" });
  const [submitting, setSubmitting] = useState(false);

  async function refresh() {
    if (!token) return;
    try {
      const [s, c] = await Promise.all([api.getPortfolioSummary(token), api.listCompanies()]);
      setSummary(s);
      setCompanies(c);
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Could not load portfolio.");
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;
    setSubmitting(true);
    setError(null);
    try {
      await api.addHolding(token, {
        company_id: form.company_id,
        quantity: form.quantity,
        average_buy_price: form.average_buy_price,
        target_allocation_pct: form.target_allocation_pct || undefined,
      });
      setForm({ company_id: "", quantity: "", average_buy_price: "", target_allocation_pct: "" });
      setShowForm(false);
      await refresh();
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Could not add holding.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(holdingId: string) {
    if (!token) return;
    await api.deleteHolding(token, holdingId);
    await refresh();
  }

  return (
    <div>
      {error && <p className="text-sm text-rust mb-4">{error}</p>}

      {summary && (
        <div className="flex flex-wrap gap-4 mb-6">
          <div className="rounded border border-line bg-paper-raised px-4 py-3">
            <div className="text-[11px] uppercase tracking-wide text-ink-faint">Total invested</div>
            <div className="font-mono text-xl tabular">₹{Number(summary.total_invested).toLocaleString("en-IN")}</div>
          </div>
          {summary.total_current_value !== null && (
            <div className="rounded border border-line bg-paper-raised px-4 py-3">
              <div className="text-[11px] uppercase tracking-wide text-ink-faint">
                Current value {!summary.all_holdings_priced && "(partial)"}
              </div>
              <div className="font-mono text-xl tabular">
                ₹{Number(summary.total_current_value).toLocaleString("en-IN")}
              </div>
              {summary.total_unrealized_pnl_pct !== null && (
                <div className={`text-xs font-mono mt-0.5 ${summary.total_unrealized_pnl_pct >= 0 ? "text-teal" : "text-rust"}`}>
                  {summary.total_unrealized_pnl_pct >= 0 ? "+" : ""}
                  {summary.total_unrealized_pnl_pct.toFixed(1)}%
                </div>
              )}
            </div>
          )}
        </div>
      )}
      {summary && summary.total_current_value !== null && (
        <p className="text-xs text-ink-faint mb-4">{summary.price_data_note}</p>
      )}

      <div className="mb-6 flex items-center gap-2">
        {!showForm ? (
          <button
            onClick={() => setShowForm(true)}
            className="rounded bg-ink text-paper px-3 py-1.5 text-sm hover:bg-ink-soft"
          >
            + Add holding
          </button>
        ) : (
          <form onSubmit={handleAdd} className="rounded border border-line bg-paper-raised p-4 space-y-3 max-w-md">
            <label className="block">
              <span className="block text-[11px] uppercase tracking-wide text-ink-faint mb-1">Company</span>
              <select
                required
                value={form.company_id}
                onChange={(e) => setForm({ ...form, company_id: e.target.value })}
                className="w-full rounded border border-line px-2.5 py-1.5 text-sm"
              >
                <option value="">Select…</option>
                {companies.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.symbol} — {c.name}
                  </option>
                ))}
              </select>
            </label>
            <div className="grid grid-cols-3 gap-2">
              <NumField label="Quantity" value={form.quantity} onChange={(v) => setForm({ ...form, quantity: v })} />
              <NumField
                label="Avg buy price"
                value={form.average_buy_price}
                onChange={(v) => setForm({ ...form, average_buy_price: v })}
              />
              <NumField
                label="Target %"
                value={form.target_allocation_pct}
                onChange={(v) => setForm({ ...form, target_allocation_pct: v })}
                required={false}
              />
            </div>
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={submitting}
                className="rounded bg-ink text-paper px-3 py-1.5 text-sm disabled:opacity-50"
              >
                Add
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="rounded px-3 py-1.5 text-sm text-ink-soft hover:bg-line/40"
              >
                Cancel
              </button>
            </div>
          </form>
        )}
        {!showForm && summary && summary.holdings.length > 0 && (
          <button
            onClick={() => token && downloadAuthenticatedFile("/portfolio/export.csv", token, "portfolio.csv")}
            className="rounded border border-line px-3 py-1.5 text-sm text-ink-soft hover:bg-line/30"
          >
            Export CSV
          </button>
        )}
      </div>

      {summary && summary.holdings.length > 0 && (
        <>
          <table className="w-full text-sm border-collapse mb-8">
            <thead>
              <tr className="border-b border-line text-[11px] uppercase tracking-wide text-ink-faint">
                <th className="text-left py-2">Company</th>
                <th className="text-right py-2">Qty</th>
                <th className="text-right py-2">Avg price</th>
                <th className="text-right py-2">Invested</th>
                <th className="text-right py-2">Current value</th>
                <th className="text-right py-2">P&amp;L</th>
                <th className="text-right py-2">Actual %</th>
                <th className="text-right py-2">Target %</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {summary.holdings.map((h) => (
                <tr key={h.holding_id} className="border-b border-line/60">
                  <td className="py-1.5">
                    <span className="font-mono text-xs text-ink-soft mr-1">{h.symbol}</span>
                    {h.name}
                  </td>
                  <td className="text-right py-1.5 font-mono tabular">{h.quantity}</td>
                  <td className="text-right py-1.5 font-mono tabular">₹{h.average_buy_price}</td>
                  <td className="text-right py-1.5 font-mono tabular">
                    ₹{Number(h.invested_amount).toLocaleString("en-IN", { maximumFractionDigits: 0 })}
                  </td>
                  <td className="text-right py-1.5 font-mono tabular">
                    {h.current_value !== null ? (
                      <>
                        ₹{Number(h.current_value).toLocaleString("en-IN", { maximumFractionDigits: 0 })}
                        {h.price_staleness_days !== null && h.price_staleness_days > 30 && (
                          <span className="block text-[10px] text-amber normal-case">
                            price {h.price_staleness_days}d old
                          </span>
                        )}
                      </>
                    ) : (
                      <span className="text-ink-faint">no price data</span>
                    )}
                  </td>
                  <td className={`text-right py-1.5 font-mono tabular ${h.down_significantly_from_buy ? "text-rust" : ""}`}>
                    {h.unrealized_pnl_pct !== null ? (
                      <>
                        {h.unrealized_pnl_pct >= 0 ? "+" : ""}
                        {h.unrealized_pnl_pct.toFixed(1)}%
                      </>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="text-right py-1.5 font-mono tabular">
                    {formatPercent(h.actual_allocation_pct)}
                  </td>
                  <td className="text-right py-1.5 font-mono tabular">{formatPercent(h.target_allocation_pct)}</td>
                  <td className="text-right py-1.5">
                    <button onClick={() => handleDelete(h.holding_id)} className="text-xs text-rust hover:underline">
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <h2 className="font-display text-lg mb-3">Sector allocation</h2>
          <ul className="space-y-1">
            {summary.sector_allocation.map((s) => (
              <li key={s.sector} className="flex items-center gap-3 text-sm">
                <span className="w-40 shrink-0">{s.sector}</span>
                <div className="flex-1 h-2 bg-line/40 rounded overflow-hidden">
                  <div
                    className="h-full bg-teal"
                    style={{ width: `${Math.min(100, Number(s.actual_allocation_pct))}%` }}
                  />
                </div>
                <span className="font-mono tabular w-14 text-right">
                  {formatPercent(s.actual_allocation_pct)}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}

      {summary && summary.holdings.length === 0 && (
        <p className="text-sm text-ink-faint">No holdings yet. Add one above.</p>
      )}
    </div>
  );
}

function NumField({
  label,
  value,
  onChange,
  required = true,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  required?: boolean;
}) {
  return (
    <label className="block">
      <span className="block text-[11px] uppercase tracking-wide text-ink-faint mb-1">{label}</span>
      <input
        type="number"
        step="any"
        required={required}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded border border-line px-2.5 py-1.5 text-sm font-mono"
      />
    </label>
  );
}
