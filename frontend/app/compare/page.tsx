import { api } from "@/lib/api";
import ComparePanel from "@/components/ComparePanel";
import type { Company } from "@/lib/types";

export default async function ComparePage() {
  let companies: Company[];
  let loadError: string | null = null;
  try {
    companies = await api.listCompanies();
  } catch {
    companies = [];
    loadError = "Could not reach the API. Is the backend running?";
  }

  return (
    <div className="px-8 py-8 max-w-5xl">
      <header className="mb-8">
        <h1 className="font-display text-2xl">Compare companies</h1>
        <p className="text-ink-soft text-sm mt-1">
          Growth, margins, leverage, and the AI report's scores, side by side.
        </p>
      </header>

      {loadError && (
        <p className="rounded border border-rust/30 bg-rust-soft text-rust px-3 py-2 text-sm mb-6">{loadError}</p>
      )}

      {!loadError && companies.length < 2 && (
        <p className="text-sm text-ink-faint">Add at least two companies before you can compare them.</p>
      )}

      {companies.length >= 2 && <ComparePanel companies={companies} />}
    </div>
  );
}
