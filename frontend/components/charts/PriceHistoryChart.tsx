"use client";

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";
import type { PriceHistoryPoint } from "@/lib/types";
import { CHART_COLORS } from "@/lib/chart-colors";

export default function PriceHistoryChart({
  prices,
  buyPrice,
}: {
  prices: PriceHistoryPoint[];
  buyPrice?: number;
}) {
  // prices arrives most-recent-first; charts read left-to-right chronologically.
  const data = [...prices]
    .reverse()
    .map((p) => ({ date: p.price_date, close: Number(p.close_price) }));

  if (data.length < 2) {
    return <p className="text-xs text-ink-faint">Need at least two price points to chart a trend.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.line} vertical={false} />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 10, fill: CHART_COLORS.inkFaint }}
          axisLine={{ stroke: CHART_COLORS.line }}
          tickLine={false}
          minTickGap={40}
        />
        <YAxis
          tick={{ fontSize: 11, fill: CHART_COLORS.inkFaint }}
          axisLine={false}
          tickLine={false}
          domain={["auto", "auto"]}
          tickFormatter={(v) => `₹${v}`}
        />
        <Tooltip
          formatter={(value: number) => [`₹${value.toLocaleString("en-IN")}`, "Close"]}
          contentStyle={{
            background: CHART_COLORS.paper,
            border: `1px solid ${CHART_COLORS.line}`,
            borderRadius: 4,
            fontSize: 12,
          }}
        />
        {buyPrice !== undefined && (
          <ReferenceLine
            y={buyPrice}
            stroke={CHART_COLORS.amber}
            strokeDasharray="4 4"
            label={{ value: "Your avg buy", position: "insideTopLeft", fontSize: 10, fill: CHART_COLORS.amber }}
          />
        )}
        <Line type="monotone" dataKey="close" stroke={CHART_COLORS.ink} strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
