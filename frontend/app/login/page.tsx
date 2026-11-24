"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

export default function LoginPage() {
  const router = useRouter();
  const { login, register } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (mode === "login") await login(email, password);
      else await register(email, password, fullName);
      router.push("/portfolio");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="px-8 py-16 max-w-sm mx-auto">
      <h1 className="font-display text-2xl mb-1">{mode === "login" ? "Log in" : "Create an account"}</h1>
      <p className="text-sm text-ink-faint mb-6">
        Needed for your portfolio, watchlist, and alerts — company research stays open to everyone.
      </p>

      <form onSubmit={handleSubmit} className="space-y-3">
        {mode === "register" && (
          <Field label="Name (optional)">
            <input
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full rounded border border-line px-2.5 py-1.5 text-sm focus:border-ink outline-none"
            />
          </Field>
        )}
        <Field label="Email">
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded border border-line px-2.5 py-1.5 text-sm focus:border-ink outline-none"
          />
        </Field>
        <Field label="Password">
          <input
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded border border-line px-2.5 py-1.5 text-sm focus:border-ink outline-none"
          />
        </Field>

        {error && <p className="text-sm text-rust">{error}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded bg-ink text-paper px-3 py-2 text-sm hover:bg-ink-soft transition-colors disabled:opacity-50"
        >
          {submitting ? "Please wait…" : mode === "login" ? "Log in" : "Create account"}
        </button>
      </form>

      <button
        onClick={() => setMode(mode === "login" ? "register" : "login")}
        className="mt-4 text-sm text-ink-soft hover:text-ink underline underline-offset-2"
      >
        {mode === "login" ? "Need an account? Register" : "Already have an account? Log in"}
      </button>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="block text-[11px] uppercase tracking-wide text-ink-faint mb-1">{label}</span>
      {children}
    </label>
  );
}
