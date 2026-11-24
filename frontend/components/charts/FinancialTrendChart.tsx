"use client";

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import type { FinancialMetric } from "@/lib/types";
import { CHART_COLORS } from "@/lib/chart-colors";

export default function FinancialTrendChart({ metrics }: { metrics: FinancialMetric[] }) {
  // metrics arrives most-recent-first; charts read left-to-right chronologically.
  const data = [...metrics]
    .reverse()
    .map((m) => ({
      period: m.fiscal_year,
      Revenue: m.revenue ? Number(m.revenue) / 10_000_000 : null, // to ₹ crore
      PAT: m.pat ? Number(m.pat) / 10_000_000 : null,
    }))
    .filter((d) => d.Revenue !== null || d.PAT !== null);

  if (data.length < 2) {
    return <p className="text-xs text-ink-faint">Need at least two periods with revenue/PAT to chart a trend.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.line} vertical={false} />
        <XAxis dataKey="period" tick={{ fontSize: 11, fill: CHART_COLORS.inkFaint }} axisLine={{ stroke: CHART_COLORS.line }} tickLine={false} />
        <YAxis
          tick={{ fontSize: 11, fill: CHART_COLORS.inkFaint }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => `₹${v}Cr`}
        />
        <Tooltip
          formatter={(value: number) => `₹${value.toLocaleString("en-IN", { maximumFractionDigits: 1 })} Cr`}
          contentStyle={{
            background: CHART_COLORS.paper,
            border: `1px solid ${CHART_COLORS.line}`,
            borderRadius: 4,
            fontSize: 12,
          }}
        />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        <Bar dataKey="Revenue" fill={CHART_COLORS.ink} radius={[2, 2, 0, 0]} />
        <Bar dataKey="PAT" fill={CHART_COLORS.teal} radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
