"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { TelemetrySample } from "@/lib/api";

interface Props {
  traces: { label: string; color: string; data: TelemetrySample[] }[];
  syncId?: string;
}

export default function GearTrace({ traces, syncId }: Props) {
  return (
    <ResponsiveContainer width="100%" height={150}>
      <LineChart syncId={syncId} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
        <XAxis
          dataKey="distance_m"
          type="number"
          domain={["dataMin", "dataMax"]}
          tick={{ fill: "#888899", fontSize: 11 }}
          axisLine={{ stroke: "#2a2a3a" }}
          allowDuplicatedCategory={false}
        />
        <YAxis
          domain={[0, 8]}
          ticks={[1, 2, 3, 4, 5, 6, 7, 8]}
          tick={{ fill: "#888899", fontSize: 11 }}
          axisLine={{ stroke: "#2a2a3a" }}
          label={{ value: "Gear", angle: -90, position: "insideLeft", fill: "#888899", fontSize: 11 }}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "#1a1a24",
            border: "1px solid #2a2a3a",
            borderRadius: 8,
            fontSize: 12,
          }}
        />
        {traces.map((t) => (
          <Line
            key={t.label}
            data={t.data}
            dataKey="gear"
            name={t.label}
            stroke={t.color}
            dot={false}
            strokeWidth={1.5}
            isAnimationActive={false}
            type="stepAfter"
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
