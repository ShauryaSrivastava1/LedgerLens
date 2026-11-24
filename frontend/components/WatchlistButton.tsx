"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export default function WatchlistButton({ companyId }: { companyId: string }) {
  const { token, user } = useAuth();
  const [itemId, setItemId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!token) return;
    api.listWatchlist(token).then((items) => {
      const match = items.find((i) => i.company_id === companyId);
      setItemId(match?.id ?? null);
    });
  }, [token, companyId]);

  if (!user) return null; // company research is public; watchlisting isn't

  async function toggle() {
    if (!token) return;
    setLoading(true);
    try {
      if (itemId) {
        await api.removeFromWatchlist(token, itemId);
        setItemId(null);
      } else {
        const item = await api.addToWatchlist(token, companyId);
        setItemId(item.id);
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <button
      onClick={toggle}
      disabled={loading}
      className={`rounded border px-2.5 py-1 text-xs transition-colors disabled:opacity-50 ${
        itemId ? "border-teal/40 text-teal bg-teal-soft" : "border-line text-ink-soft hover:bg-line/30"
      }`}
    >
      {itemId ? "★ On watchlist" : "☆ Add to watchlist"}
    </button>
  );
}
