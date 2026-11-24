"use client";

import { useEffect, useState } from "react";
import { api, APIError } from "@/lib/api";
import type { DocumentType, EquityDocument, MetricCandidate } from "@/lib/types";
import { formatDateTime } from "@/lib/format";

const DOCUMENT_TYPES: { value: DocumentType; label: string }[] = [
  { value: "ANNUAL_REPORT", label: "Annual report" },
  { value: "QUARTERLY_RESULT", label: "Quarterly result" },
  { value: "INVESTOR_PRESENTATION", label: "Investor presentation" },
  { value: "EARNINGS_CALL_TRANSCRIPT", label: "Earnings call transcript" },
  { value: "CORPORATE_ANNOUNCEMENT", label: "Corporate announcement" },
  { value: "OTHER", label: "Other" },
];

const STATUS_STYLES: Record<string, string> = {
  PENDING: "text-ink-faint bg-line/30",
  PROCESSING: "text-amber bg-amber-soft",
  PROCESSED: "text-teal bg-teal-soft",
  FAILED: "text-rust bg-rust-soft",
};

export default function DocumentsPanel({ companyId }: { companyId: string }) {
  const [documents, setDocuments] = useState<EquityDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploadType, setUploadType] = useState<DocumentType>("ANNUAL_REPORT");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    try {
      const docs = await api.listDocuments(companyId);
      setDocuments(docs);
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Could not load documents.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [companyId]);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError(null);
    setUploading(true);
    try {
      await api.uploadDocument(companyId, file, uploadType);
      await refresh();
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  return (
    <div>
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <select
          value={uploadType}
          onChange={(e) => setUploadType(e.target.value as DocumentType)}
          className="rounded border border-line px-2.5 py-1.5 text-sm bg-paper-raised focus:border-ink outline-none"
        >
          {DOCUMENT_TYPES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
        <label className="rounded bg-ink text-paper px-3 py-1.5 text-sm cursor-pointer hover:bg-ink-soft transition-colors">
          {uploading ? "Uploading…" : "Upload PDF"}
          <input type="file" accept="application/pdf" onChange={handleUpload} disabled={uploading} className="hidden" />
        </label>
      </div>

      {error && <p className="text-sm text-rust mb-3">{error}</p>}

      {loading ? (
        <p className="text-sm text-ink-faint">Loading documents…</p>
      ) : documents.length === 0 ? (
        <p className="text-sm text-ink-faint">
          No documents uploaded yet. Upload an annual report or quarterly result PDF to begin.
        </p>
      ) : (
        <ul className="space-y-2">
          {documents.map((doc) => (
            <li key={doc.id} className="rounded border border-line bg-paper-raised">
              <button
                onClick={() => setExpandedId(expandedId === doc.id ? null : doc.id)}
                className="w-full flex items-center justify-between gap-3 px-3 py-2.5 text-left"
              >
                <div className="min-w-0">
                  <div className="text-sm truncate">{doc.original_filename}</div>
                  <div className="text-[11px] text-ink-faint">
                    {doc.document_type.replace(/_/g, " ").toLowerCase()} · uploaded {formatDateTime(doc.uploaded_at)}
                    {doc.page_count !== null && ` · ${doc.page_count} pages`}
                  </div>
                </div>
                <span className={`shrink-0 rounded px-2 py-0.5 text-[11px] font-mono ${STATUS_STYLES[doc.status]}`}>
                  {doc.status}
                </span>
              </button>
              {doc.status === "FAILED" && doc.error_message && (
                <p className="px-3 pb-2.5 text-xs text-rust">{doc.error_message}</p>
              )}
              {expandedId === doc.id && doc.status === "PROCESSED" && (
                <div className="border-t border-line px-3 py-3">
                  <MetricCandidatesReview companyId={companyId} documentId={doc.id} />
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function MetricCandidatesReview({ companyId, documentId }: { companyId: string; documentId: string }) {
  const [candidates, setCandidates] = useState<MetricCandidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [promoting, setPromoting] = useState<string | null>(null);
  const [promoteForm, setPromoteForm] = useState({ period_type: "ANNUAL", period_end_date: "", fiscal_year: "" });

  async function refresh() {
    setLoading(true);
    const data = await api.listMetricCandidates(companyId, documentId);
    setCandidates(data);
    setLoading(false);
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentId]);

  async function act(candidateId: string, action: "accept" | "reject") {
    setBusyId(candidateId);
    try {
      if (action === "accept") await api.acceptMetricCandidate(companyId, documentId, candidateId);
      else await api.rejectMetricCandidate(companyId, documentId, candidateId);
      await refresh();
    } finally {
      setBusyId(null);
    }
  }

  async function promote(candidateId: string) {
    if (!promoteForm.period_end_date || !promoteForm.fiscal_year) return;
    setBusyId(candidateId);
    try {
      await api.promoteMetricCandidate(companyId, documentId, candidateId, promoteForm);
      setPromoting(null);
      await refresh();
    } finally {
      setBusyId(null);
    }
  }

  if (loading) return <p className="text-sm text-ink-faint">Loading extracted figures…</p>;
  if (candidates.length === 0)
    return <p className="text-sm text-ink-faint">No figures were extracted from this document.</p>;

  return (
    <div className="space-y-2">
      <p className="text-[11px] uppercase tracking-wide text-ink-faint mb-1">
        Figures found in this document — review before they count as verified metrics
      </p>
      {candidates.map((c) => (
        <div key={c.id} className="rounded border border-line px-3 py-2 text-sm">
          <div className="flex items-center justify-between gap-3">
            <div>
              <span className="font-mono text-ink-soft">{c.metric_name}</span>{" "}
              <span className="font-mono tabular">{c.extracted_value}</span>{" "}
              {c.unit_note && <span className="text-ink-faint">{c.unit_note}</span>}
              <span className="ml-2 text-[11px] text-ink-faint">page {c.page_number ?? "?"}</span>
            </div>
            <StatusPill status={c.status} promoted={!!c.promoted_financial_metric_id} />
          </div>
          <p className="text-xs text-ink-faint italic mt-1">"{c.raw_text_snippet}"</p>

          {c.status === "PENDING_REVIEW" && (
            <div className="flex gap-2 mt-2">
              <button
                onClick={() => act(c.id, "accept")}
                disabled={busyId === c.id}
                className="rounded bg-teal text-paper px-2.5 py-1 text-xs hover:opacity-90 disabled:opacity-50"
              >
                Accept
              </button>
              <button
                onClick={() => act(c.id, "reject")}
                disabled={busyId === c.id}
                className="rounded border border-line px-2.5 py-1 text-xs text-ink-soft hover:bg-line/30 disabled:opacity-50"
              >
                Reject
              </button>
            </div>
          )}

          {c.status === "ACCEPTED" && !c.promoted_financial_metric_id && (
            <div className="mt-2">
              {promoting === c.id ? (
                <div className="flex flex-wrap items-end gap-2">
                  <MiniField label="Period end">
                    <input
                      type="date"
                      value={promoteForm.period_end_date}
                      onChange={(e) => setPromoteForm({ ...promoteForm, period_end_date: e.target.value })}
                      className="rounded border border-line px-2 py-1 text-xs"
                    />
                  </MiniField>
                  <MiniField label="Fiscal year">
                    <input
                      value={promoteForm.fiscal_year}
                      onChange={(e) => setPromoteForm({ ...promoteForm, fiscal_year: e.target.value })}
                      placeholder="FY2024-25"
                      className="rounded border border-line px-2 py-1 text-xs w-28"
                    />
                  </MiniField>
                  <MiniField label="Period type">
                    <select
                      value={promoteForm.period_type}
                      onChange={(e) => setPromoteForm({ ...promoteForm, period_type: e.target.value })}
                      className="rounded border border-line px-2 py-1 text-xs"
                    >
                      <option value="ANNUAL">Annual</option>
                      <option value="QUARTERLY">Quarterly</option>
                    </select>
                  </MiniField>
                  <button
                    onClick={() => promote(c.id)}
                    disabled={busyId === c.id}
                    className="rounded bg-ink text-paper px-2.5 py-1 text-xs disabled:opacity-50"
                  >
                    Confirm
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setPromoting(c.id)}
                  className="rounded border border-teal/40 text-teal px-2.5 py-1 text-xs hover:bg-teal-soft"
                >
                  Promote to verified metric
                </button>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function StatusPill({ status, promoted }: { status: string; promoted: boolean }) {
  if (promoted) return <span className="text-[11px] font-mono text-teal">promoted</span>;
  const styles: Record<string, string> = {
    PENDING_REVIEW: "text-amber",
    ACCEPTED: "text-teal",
    REJECTED: "text-ink-faint",
  };
  return <span className={`text-[11px] font-mono ${styles[status]}`}>{status.toLowerCase().replace("_", " ")}</span>;
}

function MiniField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="block text-[10px] uppercase tracking-wide text-ink-faint mb-0.5">{label}</span>
      {children}
    </label>
  );
}
