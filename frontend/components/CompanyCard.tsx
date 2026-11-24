import Link from "next/link";
import type { Company } from "@/lib/types";

export default function CompanyCard({ company }: { company: Company }) {
  return (
    <Link
      href={`/companies/${company.id}`}
      className="block rounded border border-line bg-paper-raised px-4 py-3 hover:border-ink/30 transition-colors"
    >
      <div className="flex items-baseline justify-between gap-3">
        <span className="font-mono text-sm text-ink-soft">{company.symbol}</span>
        {company.sector && (
          <span className="text-[11px] text-ink-faint uppercase tracking-wide">{company.sector}</span>
        )}
      </div>
      <div className="font-display text-base mt-0.5">{company.name}</div>
    </Link>
  );
}
