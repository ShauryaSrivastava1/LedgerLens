"use client";

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import type { FinancialMetric } from "@/lib/types";
import { CHART_COLORS } from "@/lib/chart-colors";

export default function RatioTrendChart({ metrics }: { metrics: FinancialMetric[] }) {
  const data = [...metrics]
    .reverse()
    .map((m) => ({
      period: m.fiscal_year,
      ROCE: m.roce ? Number(m.roce) : null,
      ROE: m.roe ? Number(m.roe) : null,
      "Net margin": m.net_margin ? Number(m.net_margin) : null,
    }));

  const hasData = data.some((d) => d.ROCE !== null || d.ROE !== null || d["Net margin"] !== null);
  if (!hasData || data.length < 2) {
    return <p className="text-xs text-ink-faint">Need at least two periods with ROCE/ROE/margin data to chart a trend.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.line} vertical={false} />
        <XAxis dataKey="period" tick={{ fontSize: 11, fill: CHART_COLORS.inkFaint }} axisLine={{ stroke: CHART_COLORS.line }} tickLine={false} />
        <YAxis
          tick={{ fontSize: 11, fill: CHART_COLORS.inkFaint }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => `${v}%`}
        />
        <Tooltip
          formatter={(value: number) => `${value.toFixed(1)}%`}
          contentStyle={{
            background: CHART_COLORS.paper,
            border: `1px solid ${CHART_COLORS.line}`,
            borderRadius: 4,
            fontSize: 12,
          }}
        />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        <Line type="monotone" dataKey="ROCE" stroke={CHART_COLORS.teal} strokeWidth={2} dot={{ r: 3 }} connectNulls />
        <Line type="monotone" dataKey="ROE" stroke={CHART_COLORS.ink} strokeWidth={2} dot={{ r: 3 }} connectNulls />
        <Line type="monotone" dataKey="Net margin" stroke={CHART_COLORS.amber} strokeWidth={2} dot={{ r: 3 }} connectNulls />
      </LineChart>
    </ResponsiveContainer>
  );
}
