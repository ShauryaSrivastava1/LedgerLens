"use client";

import { useEffect, useState } from "react";
import { api, APIError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import RequireAuth from "@/components/RequireAuth";
import type { RiskAlert } from "@/lib/types";
import { formatDateTime } from "@/lib/format";

const SEVERITY_STYLES: Record<string, string> = {
  HIGH: "border-l-rust text-rust",
  MEDIUM: "border-l-amber text-amber",
  LOW: "border-l-ink-faint text-ink-faint",
};

export default function AlertsPage() {
  return (
    <div className="px-8 py-8 max-w-3xl">
      <header className="mb-8">
        <h1 className="font-display text-2xl">Alerts</h1>
        <p className="text-ink-soft text-sm mt-1">
          Automatic flags for companies in your portfolio or watchlist — pledge increases, promoter selling, and score drops between AI reports.
        </p>
      </header>
      <RequireAuth>
        <AlertsContent />
      </RequireAuth>
    </div>
  );
}

function AlertsContent() {
  const { token } = useAuth();
  const [alerts, setAlerts] = useState<RiskAlert[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    if (!token) return;
    try {
      setAlerts(await api.listMyAlerts(token));
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Could not load alerts.");
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  async function handleAcknowledge(alertId: string) {
    if (!token) return;
    await api.acknowledgeAlert(token, alertId);
    await refresh();
  }

  if (error) return <p className="text-sm text-rust">{error}</p>;

  if (alerts.length === 0) {
    return (
      <p className="text-sm text-ink-faint">
        No alerts. Add companies to your portfolio or watchlist, and alerts will appear here automatically
        when something changes — a pledge increase, promoter selling, or a governance/overall score drop
        between AI reports.
      </p>
    );
  }

  const unacknowledged = alerts.filter((a) => !a.acknowledged);
  const acknowledged = alerts.filter((a) => a.acknowledged);

  return (
    <div className="space-y-8">
      {unacknowledged.length > 0 && (
        <AlertGroup title="Needs review" alerts={unacknowledged} onAcknowledge={handleAcknowledge} />
      )}
      {acknowledged.length > 0 && (
        <AlertGroup title="Acknowledged" alerts={acknowledged} onAcknowledge={handleAcknowledge} dimmed />
      )}
    </div>
  );
}

function AlertGroup({
  title,
  alerts,
  onAcknowledge,
  dimmed,
}: {
  title: string;
  alerts: RiskAlert[];
  onAcknowledge: (id: string) => void;
  dimmed?: boolean;
}) {
  return (
    <div>
      <h2 className="text-[11px] uppercase tracking-wide text-ink-faint mb-2">{title}</h2>
      <ul className={`space-y-2 ${dimmed ? "opacity-60" : ""}`}>
        {alerts.map((alert) => (
          <li
            key={alert.id}
            className={`border-l-2 pl-3 py-2 rounded-r bg-paper-raised border border-line ${SEVERITY_STYLES[alert.severity]}`}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm text-ink font-medium">{alert.message}</p>
                <p className="text-xs text-ink-faint mt-0.5">{alert.evidence}</p>
                <p className="text-[11px] text-ink-faint mt-1">{formatDateTime(alert.triggered_at)}</p>
              </div>
              {!alert.acknowledged && (
                <button
                  onClick={() => onAcknowledge(alert.id)}
                  className="shrink-0 rounded border border-line px-2 py-1 text-xs text-ink-soft hover:bg-line/30"
                >
                  Acknowledge
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
