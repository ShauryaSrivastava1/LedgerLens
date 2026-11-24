"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, APIError } from "@/lib/api";

export default function AddCompanyForm() {
  const router = useRouter();
  const [symbol, setSymbol] = useState("");
  const [name, setName] = useState("");
  const [sector, setSector] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [open, setOpen] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const company = await api.createCompany({ symbol, name, sector: sector || undefined });
      setSymbol("");
      setName("");
      setSector("");
      setOpen(false);
      router.push(`/companies/${company.id}`);
      router.refresh();
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Could not add company.");
    } finally {
      setSubmitting(false);
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="rounded border border-ink/20 bg-ink text-paper px-4 py-2 text-sm hover:bg-ink-soft transition-colors"
      >
        + Add company
      </button>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="rounded border border-line bg-paper-raised p-4 space-y-3 max-w-md">
      <div className="grid grid-cols-2 gap-3">
        <Field label="Symbol">
          <input
            required
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            placeholder="DMART"
            className="w-full rounded border border-line px-2.5 py-1.5 text-sm font-mono uppercase focus:border-ink outline-none"
          />
        </Field>
        <Field label="Sector (optional)">
          <input
            value={sector}
            onChange={(e) => setSector(e.target.value)}
            placeholder="Retail"
            className="w-full rounded border border-line px-2.5 py-1.5 text-sm focus:border-ink outline-none"
          />
        </Field>
      </div>
      <Field label="Company name">
        <input
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Avenue Supermarts Ltd"
          className="w-full rounded border border-line px-2.5 py-1.5 text-sm focus:border-ink outline-none"
        />
      </Field>
      {error && <p className="text-sm text-rust">{error}</p>}
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={submitting}
          className="rounded bg-ink text-paper px-3 py-1.5 text-sm hover:bg-ink-soft transition-colors disabled:opacity-50"
        >
          {submitting ? "Adding…" : "Add company"}
        </button>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="rounded px-3 py-1.5 text-sm text-ink-soft hover:bg-line/40 transition-colors"
        >
          Cancel
        </button>
      </div>
    </form>
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
