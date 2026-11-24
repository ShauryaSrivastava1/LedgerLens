"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, APIError, downloadAuthenticatedFile } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import RequireAuth from "@/components/RequireAuth";
import type { Company, WatchlistItem } from "@/lib/types";
import { formatDate } from "@/lib/format";

export default function WatchlistPage() {
  return (
    <div className="px-8 py-8 max-w-3xl">
      <header className="mb-8">
        <h1 className="font-display text-2xl">Watchlist</h1>
        <p className="text-ink-soft text-sm mt-1">Companies you're keeping an eye on, without holding them yet.</p>
      </header>
      <RequireAuth>
        <WatchlistContent />
      </RequireAuth>
    </div>
  );
}

function WatchlistContent() {
  const { token } = useAuth();
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [companies, setCompanies] = useState<Record<string, Company>>({});
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    if (!token) return;
    try {
      const [watchlist, allCompanies] = await Promise.all([api.listWatchlist(token), api.listCompanies()]);
      setItems(watchlist);
      setCompanies(Object.fromEntries(allCompanies.map((c) => [c.id, c])));
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Could not load watchlist.");
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  async function handleRemove(itemId: string) {
    if (!token) return;
    await api.removeFromWatchlist(token, itemId);
    await refresh();
  }

  if (error) return <p className="text-sm text-rust">{error}</p>;

  if (items.length === 0) {
    return (
      <p className="text-sm text-ink-faint">
        Nothing on your watchlist yet. Visit a company's page to add it.
      </p>
    );
  }

  return (
    <div>
      <div className="mb-4">
        <button
          onClick={() => token && downloadAuthenticatedFile("/watchlist/export.csv", token, "watchlist.csv")}
          className="rounded border border-line px-3 py-1.5 text-sm text-ink-soft hover:bg-line/30"
        >
          Export CSV
        </button>
      </div>
      <ul className="space-y-2">
        {items.map((item) => {
          const company = companies[item.company_id];
          return (
            <li key={item.id} className="rounded border border-line bg-paper-raised px-4 py-3 flex items-start justify-between gap-3">
              <div>
                {company ? (
                  <Link href={`/companies/${company.id}`} className="font-display text-base hover:underline">
                    <span className="font-mono text-xs text-ink-soft mr-2">{company.symbol}</span>
                    {company.name}
                  </Link>
                ) : (
                  <span className="text-ink-faint">Unknown company</span>
                )}
                {item.note && <p className="text-sm text-ink-soft mt-1">{item.note}</p>}
                <p className="text-[11px] text-ink-faint mt-1">Added {formatDate(item.added_at)}</p>
              </div>
              <button onClick={() => handleRemove(item.id)} className="text-xs text-rust hover:underline shrink-0">
                Remove
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
