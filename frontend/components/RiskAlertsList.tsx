import type { RiskAlert } from "@/lib/types";
import { formatDateTime } from "@/lib/format";

const SEVERITY_STYLES: Record<string, string> = {
  HIGH: "border-l-rust",
  MEDIUM: "border-l-amber",
  LOW: "border-l-ink-faint",
};

export default function RiskAlertsList({ alerts }: { alerts: RiskAlert[] }) {
  if (alerts.length === 0) {
    return <p className="text-sm text-ink-faint py-1">No alerts on record for this company.</p>;
  }

  return (
    <ul className="space-y-2">
      {alerts.map((alert) => (
        <li
          key={alert.id}
          className={`border-l-2 pl-3 py-1.5 ${SEVERITY_STYLES[alert.severity]}`}
        >
          <p className="text-sm">{alert.message}</p>
          <p className="text-xs text-ink-faint mt-0.5">
            {alert.evidence} · {formatDateTime(alert.triggered_at)}
          </p>
        </li>
      ))}
    </ul>
  );
}
