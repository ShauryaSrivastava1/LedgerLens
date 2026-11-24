"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth-context";

export default function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();

  if (loading) return <p className="text-sm text-ink-faint px-8 py-8">Loading…</p>;

  if (!user) {
    return (
      <div className="px-8 py-16 max-w-md">
        <p className="font-display text-lg mb-2">Log in to continue</p>
        <p className="text-sm text-ink-faint mb-4">
          This page tracks your personal portfolio, watchlist, or alerts — log in or create an account first.
        </p>
        <Link href="/login" className="rounded bg-ink text-paper px-3 py-1.5 text-sm inline-block hover:bg-ink-soft">
          Log in
        </Link>
      </div>
    );
  }

  return <>{children}</>;
}
