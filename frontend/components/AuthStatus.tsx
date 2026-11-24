"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth-context";

export default function AuthStatus() {
  const { user, loading, logout } = useAuth();

  if (loading) return <div className="px-5 py-3 text-[11px] text-paper/40">…</div>;

  if (!user) {
    return (
      <div className="px-5 py-3">
        <Link
          href="/login"
          className="block text-center rounded border border-white/20 px-3 py-1.5 text-xs text-paper/80 hover:bg-white/5"
        >
          Log in
        </Link>
      </div>
    );
  }

  return (
    <div className="px-5 py-3 flex items-center justify-between gap-2">
      <span className="text-xs text-paper/70 truncate" title={user.email}>
        {user.full_name || user.email}
      </span>
      <button onClick={logout} className="text-[11px] text-paper/50 hover:text-paper shrink-0">
        Log out
      </button>
    </div>
  );
}
