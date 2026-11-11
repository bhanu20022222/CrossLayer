import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid,
  Legend,
} from "recharts";
import type { Series } from "../api/types";
import { EmptyState } from "./EmptyState";

const PALETTE = ["#3d9a8a", "#c4a35a", "#6ea4d4", "#c47a6a", "#8f8ad4", "#7aae6a"];

function merge(series: Series[]) {
  const byTime = new Map<number, Record<string, number | string>>();
  for (const s of series) {
    for (const p of s.points) {
      const row = byTime.get(p.t) ?? { t: p.t };
      row[s.name] = p.v;
      byTime.set(p.t, row);
    }
  }
  return [...byTime.values()].sort((a, b) => Number(a.t) - Number(b.t));
}

export function TimeSeriesChart({
  series,
  yLabel,
  emptyHint,
}: {
  series: Series[];
  yLabel: string;
  emptyHint: string;
}) {
  const usable = series.filter((s) => s.points.length > 0);
  if (usable.length === 0) {
    return <EmptyState title="No measured points" detail={emptyHint} />;
  }
  const data = merge(usable);
  return (
    <div style={{ width: "100%", height: 280 }}>
      <ResponsiveContainer>
        <LineChart data={data}>
          <CartesianGrid stroke="#2a3848" strokeDasharray="3 3" />
          <XAxis
            dataKey="t"
            tickFormatter={(v) => new Date(Number(v) * 1000).toLocaleTimeString()}
            stroke="#93a4b5"
            minTickGap={24}
          />
          <YAxis stroke="#93a4b5" />
          <Tooltip
            labelFormatter={(v) => new Date(Number(v) * 1000).toLocaleString()}
            contentStyle={{ background: "#151d27", border: "1px solid #2a3848" }}
          />
          <Legend />
          {usable.map((s, i) => (
            <Line
              key={s.name}
              type="monotone"
              dataKey={s.name}
              stroke={PALETTE[i % PALETTE.length]}
              dot={false}
              strokeWidth={2}
              name={s.name}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
      <div className="hint" style={{ color: "#93a4b5", fontSize: "0.75rem" }}>
        {yLabel}
      </div>
    </div>
  );
}
