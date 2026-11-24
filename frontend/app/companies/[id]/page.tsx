import { notFound } from "next/navigation";
import { api, APIError } from "@/lib/api";
import MetricsTable from "@/components/MetricsTable";
import ShareholdingSummary from "@/components/ShareholdingSummary";
import DocumentsPanel from "@/components/DocumentsPanel";
import ReportPanel from "@/components/ReportPanel";
import WatchlistButton from "@/components/WatchlistButton";
import RiskAlertsList from "@/components/RiskAlertsList";
import PricePanel from "@/components/PricePanel";
import Timeline from "@/components/Timeline";
import AssistantPanel from "@/components/AssistantPanel";
import FinancialTrendChart from "@/components/charts/FinancialTrendChart";
import RatioTrendChart from "@/components/charts/RatioTrendChart";

export default async function CompanyDetailPage({ params }: { params: { id: string } }) {
  let company;
  try {
    company = await api.getCompany(params.id);
  } catch (err) {
    if (err instanceof APIError && err.status === 404) notFound();
    throw err;
  }

  const [alerts, timeline] = await Promise.all([
    api.listCompanyAlerts(company.id).catch(() => []),
    api.getCompanyTimeline(company.id).catch(() => []),
  ]);

  return (
    <div className="px-8 py-8 max-w-5xl">
      <header className="mb-8 flex items-start justify-between gap-4">
        <div>
          <div className="flex items-baseline gap-3">
            <span className="font-mono text-sm text-ink-soft">{company.symbol}</span>
            {company.sector && (
              <span className="text-[11px] text-ink-faint uppercase tracking-wide">{company.sector}</span>
            )}
          </div>
          <h1 className="font-display text-2xl mt-0.5">{company.name}</h1>
        </div>
        <WatchlistButton companyId={company.id} />
      </header>

      {alerts.length > 0 && (
        <Section title="Risk alerts">
          <RiskAlertsList alerts={alerts} />
        </Section>
      )}

      <Section title="Shareholding pattern">
        <ShareholdingSummary records={company.shareholding_records} />
      </Section>

      <Section title="Financial metrics">
        <div className="grid sm:grid-cols-2 gap-6 mb-4">
          <div>
            <p className="text-[11px] uppercase tracking-wide text-ink-faint mb-1">Revenue &amp; PAT</p>
            <FinancialTrendChart metrics={company.financial_metrics} />
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-wide text-ink-faint mb-1">ROCE / ROE / Net margin</p>
            <RatioTrendChart metrics={company.financial_metrics} />
          </div>
        </div>
        <MetricsTable metrics={company.financial_metrics} />
      </Section>

      <Section title="Price data">
        <PricePanel companyId={company.id} />
      </Section>

      <Section title="Documents">
        <DocumentsPanel companyId={company.id} />
      </Section>

      <Section title="AI analysis">
        <ReportPanel companyId={company.id} />
      </Section>

      <Section title="Ask the AI Assistant">
        <AssistantPanel companyId={company.id} />
      </Section>

      <Section title="Timeline">
        <Timeline events={timeline} />
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-10">
      <h2 className="font-display text-lg mb-3 pb-2 border-b border-line">{title}</h2>
      {children}
    </section>
  );
}
