"use client";

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import type { AIReport } from "@/lib/types";
import { CHART_COLORS } from "@/lib/chart-colors";

export default function ScoreHistoryChart({ reports }: { reports: AIReport[] }) {
  // reports arrives most-recent-first; charts read left-to-right chronologically.
  const data = [...reports]
    .reverse()
    .map((r) => ({
      date: new Date(r.generated_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "2-digit" }),
      Overall: r.overall_score !== null ? Number(r.overall_score) : null,
      Governance: r.governance_score !== null ? Number(r.governance_score) : null,
      Moat: r.moat_score !== null ? Number(r.moat_score) : null,
    }));

  const hasData = data.some((d) => d.Overall !== null);
  if (!hasData || data.length < 2) {
    return <p className="text-xs text-ink-faint">Need at least two generated reports to chart score history.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.line} vertical={false} />
        <XAxis dataKey="date" tick={{ fontSize: 10, fill: CHART_COLORS.inkFaint }} axisLine={{ stroke: CHART_COLORS.line }} tickLine={false} />
        <YAxis
          domain={[0, 100]}
          tick={{ fontSize: 11, fill: CHART_COLORS.inkFaint }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          contentStyle={{
            background: CHART_COLORS.paper,
            border: `1px solid ${CHART_COLORS.line}`,
            borderRadius: 4,
            fontSize: 12,
          }}
        />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        <Line type="monotone" dataKey="Overall" stroke={CHART_COLORS.ink} strokeWidth={2} dot={{ r: 3 }} connectNulls />
        <Line type="monotone" dataKey="Governance" stroke={CHART_COLORS.rust} strokeWidth={2} dot={{ r: 3 }} connectNulls />
        <Line type="monotone" dataKey="Moat" stroke={CHART_COLORS.teal} strokeWidth={2} dot={{ r: 3 }} connectNulls />
      </LineChart>
    </ResponsiveContainer>
  );
}
