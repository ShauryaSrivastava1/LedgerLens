"use client";

import { useEffect, useState } from "react";
import { api, APIError, API_BASE_URL } from "@/lib/api";
import type { AIReport } from "@/lib/types";
import { formatDateTime } from "@/lib/format";
import ScoreBadge from "./ScoreBadge";
import FlagCard from "./FlagCard";
import ScoreHistoryChart from "./charts/ScoreHistoryChart";

export default function ReportPanel({ companyId }: { companyId: string }) {
  const [reports, setReports] = useState<AIReport[]>([]);
  const [selected, setSelected] = useState<AIReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    try {
      const data = await api.listReports(companyId);
      setReports(data);
      setSelected((prev) => prev ?? data[0] ?? null);
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Could not load reports.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [companyId]);

  async function handleGenerate() {
    setError(null);
    setGenerating(true);
    try {
      const report = await api.generateReport(companyId);
      setReports((prev) => [report, ...prev]);
      setSelected(report);
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Report generation failed.");
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="rounded bg-ink text-paper px-3 py-1.5 text-sm hover:bg-ink-soft transition-colors disabled:opacity-50"
        >
          {generating ? "Analyzing…" : "Generate new report"}
        </button>
        {reports.length > 1 && (
          <select
            value={selected?.id}
            onChange={(e) => setSelected(reports.find((r) => r.id === e.target.value) ?? null)}
            className="rounded border border-line px-2 py-1 text-xs bg-paper-raised"
          >
            {reports.map((r) => (
              <option key={r.id} value={r.id}>
                {formatDateTime(r.generated_at)}
              </option>
            ))}
          </select>
        )}
      </div>

      {error && <p className="text-sm text-rust mb-3">{error}</p>}
      {loading && <p className="text-sm text-ink-faint">Loading…</p>}

      {reports.length >= 2 && (
        <div className="mb-6">
          <ScoreHistoryChart reports={reports} />
        </div>
      )}

      {!loading && !selected && (
        <p className="text-sm text-ink-faint">
          No report generated yet. Upload documents and/or add financial metrics, then generate one.
        </p>
      )}

      {selected && <ReportDetail report={selected} companyId={companyId} />}
    </div>
  );
}

function ReportDetail({ report, companyId }: { report: AIReport; companyId: string }) {
  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center justify-between gap-3 mb-2">
          <div className="flex items-center gap-2 text-[11px] text-ink-faint">
            <span>{formatDateTime(report.generated_at)}</span>
            <span>·</span>
            <span className="font-mono">
              {report.llm_provider}/{report.llm_model}
            </span>
            <span>·</span>
            <span>confidence {(parseFloat(report.confidence_score) * 100).toFixed(0)}%</span>
          </div>
          <a
            href={`${API_BASE_URL}/companies/${companyId}/ai-reports/${report.id}/pdf`}
            className="text-xs text-ink-soft border border-line rounded px-2 py-1 hover:bg-line/30 shrink-0"
          >
            Download PDF
          </a>
        </div>
        <p className="text-sm leading-relaxed">{report.summary}</p>
      </div>

      <div className="grid grid-cols-4 sm:grid-cols-8 gap-2">
        <ScoreBadge label="Overall" value={report.overall_score} />
        <ScoreBadge label="Financial" value={report.financial_health_score} />
        <ScoreBadge label="Growth" value={report.growth_score} />
        <ScoreBadge label="Profit" value={report.profitability_score} />
        <ScoreBadge label="Governance" value={report.governance_score} />
        <ScoreBadge label="Moat" value={report.moat_score} />
        <ScoreBadge label="Valuation" value={report.valuation_score} />
        <ScoreBadge label="Risk" value={report.risk_score} />
      </div>

      {report.green_flags.length > 0 && (
        <FlagSection title="Green flags" flags={report.green_flags} tone="green" />
      )}
      {report.red_flags.length > 0 && <FlagSection title="Red flags" flags={report.red_flags} tone="red" />}

      <TextListSection title="Questions investors should ask" items={report.questions_investors_should_ask} />
      <TextListSection title="Things to verify" items={report.things_to_verify} />
      <TextListSection title="Potential risks" items={report.potential_risks} />
    </div>
  );
}

function FlagSection({ title, flags, tone }: { title: string; flags: AIReport["green_flags"]; tone: "green" | "red" }) {
  return (
    <div>
      <h3 className="text-[11px] uppercase tracking-wide text-ink-faint mb-2">{title}</h3>
      <div className="space-y-2">
        {flags.map((f, i) => (
          <FlagCard key={i} flag={f} tone={tone} />
        ))}
      </div>
    </div>
  );
}

function TextListSection({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div>
      <h3 className="text-[11px] uppercase tracking-wide text-ink-faint mb-2">{title}</h3>
      <ul className="space-y-1">
        {items.map((item, i) => (
          <li key={i} className="text-sm text-ink-soft pl-3 relative before:content-['—'] before:absolute before:left-0 before:text-ink-faint">
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}
