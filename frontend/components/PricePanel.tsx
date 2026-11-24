"use client";

import { useEffect, useState } from "react";
import { api, APIError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { PriceHistoryPoint } from "@/lib/types";
import { formatDate } from "@/lib/format";
import PriceHistoryChart from "./charts/PriceHistoryChart";

export default function PricePanel({ companyId }: { companyId: string }) {
  const { token } = useAuth();
  const [prices, setPrices] = useState<PriceHistoryPoint[]>([]);
  const [myBuyPrice, setMyBuyPrice] = useState<number | undefined>(undefined);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadSummary, setUploadSummary] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    try {
      setPrices(await api.listPrices(companyId));
      if (token) {
        const holdings = await api.listHoldings(token);
        const match = holdings.find((h) => h.company_id === companyId);
        setMyBuyPrice(match ? Number(match.average_buy_price) : undefined);
      }
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Could not load price data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [companyId, token]);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    setUploadSummary(null);
    try {
      const result = await api.bulkUploadPrices(companyId, file);
      setUploadSummary(
        `${result.rows_added} added, ${result.rows_skipped_duplicate} already on file` +
          (result.rows_with_errors ? `, ${result.rows_with_errors} rows had errors` : "")
      );
      await refresh();
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  const latest = prices[0];

  return (
    <div>
      <p className="text-xs text-ink-faint mb-3">
        No live price feed — upload a CSV export (date + close columns) to enable mark-to-market
        portfolio valuation and price-aware AI report context.
      </p>

      <div className="flex items-center gap-3 mb-4">
        <label className="rounded bg-ink text-paper px-3 py-1.5 text-sm cursor-pointer hover:bg-ink-soft transition-colors">
          {uploading ? "Uploading…" : "Upload price CSV"}
          <input type="file" accept=".csv,text/csv" onChange={handleUpload} disabled={uploading} className="hidden" />
        </label>
        {latest && (
          <span className="text-sm text-ink-soft">
            Latest: <span className="font-mono">₹{latest.close_price}</span> as of {formatDate(latest.price_date)}
          </span>
        )}
      </div>

      {uploadSummary && <p className="text-sm text-teal mb-2">{uploadSummary}</p>}
      {error && <p className="text-sm text-rust mb-2">{error}</p>}

      {prices.length >= 2 && (
        <div className="mb-4">
          <PriceHistoryChart prices={prices} buyPrice={myBuyPrice} />
        </div>
      )}

      {!loading && prices.length === 0 && (
        <p className="text-sm text-ink-faint">No price data on file yet.</p>
      )}

      {prices.length > 0 && (
        <details className="text-sm">
          <summary className="cursor-pointer text-ink-soft">
            {prices.length} price point{prices.length !== 1 ? "s" : ""} on file
          </summary>
          <table className="w-full text-sm mt-2 border-collapse">
            <tbody>
              {prices.slice(0, 15).map((p) => (
                <tr key={p.id} className="border-b border-line/60">
                  <td className="py-1">{formatDate(p.price_date)}</td>
                  <td className="py-1 text-right font-mono tabular">₹{p.close_price}</td>
                  <td className="py-1 text-right text-[11px] text-ink-faint">{p.source}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      )}
    </div>
  );
}
