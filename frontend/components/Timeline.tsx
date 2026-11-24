import type { TimelineEvent } from "@/lib/types";
import { formatDateTime } from "@/lib/format";

const EVENT_STYLES: Record<string, { dot: string; label: string }> = {
  DOCUMENT_UPLOADED: { dot: "bg-ink-faint", label: "Document" },
  AI_REPORT_GENERATED: { dot: "bg-teal", label: "AI report" },
  RISK_ALERT: { dot: "bg-rust", label: "Alert" },
};

export default function Timeline({ events }: { events: TimelineEvent[] }) {
  if (events.length === 0) {
    return (
      <p className="text-sm text-ink-faint py-1">
        No activity yet — upload a document or generate an AI report to start building this company's timeline.
      </p>
    );
  }

  return (
    <ol className="space-y-3">
      {events.map((event, i) => {
        const style = EVENT_STYLES[event.event_type];
        return (
          <li key={i} className="flex gap-3">
            <div className="flex flex-col items-center pt-1.5">
              <span className={`w-2 h-2 rounded-full ${style.dot}`} />
              {i < events.length - 1 && <span className="w-px flex-1 bg-line mt-1" />}
            </div>
            <div className="pb-2">
              <div className="flex items-baseline gap-2">
                <span className="text-[10px] uppercase tracking-wide text-ink-faint">{style.label}</span>
                <span className="text-[11px] text-ink-faint">{formatDateTime(event.occurred_at)}</span>
              </div>
              <p className="text-sm">{event.title}</p>
              <p className="text-xs text-ink-faint">{event.description}</p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
