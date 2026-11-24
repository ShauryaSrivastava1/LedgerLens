import { api } from "@/lib/api";
import CompanyCard from "@/components/CompanyCard";
import AddCompanyForm from "@/components/AddCompanyForm";
import type { Company } from "@/lib/types";

export default async function DashboardPage() {
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
        <h1 className="font-display text-2xl">Companies</h1>
        <p className="text-ink-soft text-sm mt-1">
          Every score on this platform traces back to a filing, a page, and a number — not a hunch.
        </p>
      </header>

      <div className="mb-6">
        <AddCompanyForm />
      </div>

      {loadError && (
        <p className="rounded border border-rust/30 bg-rust-soft text-rust px-3 py-2 text-sm mb-6">
          {loadError}
        </p>
      )}

      {!loadError && companies.length === 0 && (
        <div className="rounded border border-dashed border-line px-6 py-10 text-center">
          <p className="font-display text-lg text-ink-soft">No companies yet</p>
          <p className="text-sm text-ink-faint mt-1">
            Add one above to start uploading annual reports and generating evidence-backed analysis.
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {companies.map((c) => (
          <CompanyCard key={c.id} company={c} />
        ))}
      </div>
    </div>
  );
}
