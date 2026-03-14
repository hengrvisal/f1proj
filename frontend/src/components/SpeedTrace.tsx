"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceArea,
} from "recharts";
import { TelemetrySample, Corner } from "@/lib/api";

interface Props {
  traces: { label: string; color: string; data: TelemetrySample[] }[];
  corners?: Corner[];
  syncId?: string;
}

export default function SpeedTrace({ traces, corners, syncId }: Props) {
  return (
    <ResponsiveContainer width="100%" height={250}>
      <LineChart syncId={syncId} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
        <XAxis
          dataKey="distance_m"
          type="number"
          domain={["dataMin", "dataMax"]}
          tick={{ fill: "#888899", fontSize: 11 }}
          axisLine={{ stroke: "#2a2a3a" }}
          label={{ value: "Distance (m)", position: "bottom", fill: "#888899", fontSize: 11 }}
          allowDuplicatedCategory={false}
        />
        <YAxis
          tick={{ fill: "#888899", fontSize: 11 }}
          axisLine={{ stroke: "#2a2a3a" }}
          label={{ value: "Speed (km/h)", angle: -90, position: "insideLeft", fill: "#888899", fontSize: 11 }}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "#1a1a24",
            border: "1px solid #2a2a3a",
            borderRadius: 8,
            fontSize: 12,
          }}
          labelFormatter={(v) => `${v}m`}
        />
        {corners?.map((c) => (
          <ReferenceArea
            key={c.corner_number}
            x1={c.entry_distance_m}
            x2={c.exit_distance_m}
            fill="#ffffff08"
            strokeOpacity={0}
            label={{ value: `T${c.corner_number}`, fill: "#555", fontSize: 10, position: "insideTop" }}
          />
        ))}
        {traces.map((t) => (
          <Line
            key={t.label}
            data={t.data}
            dataKey="speed"
            name={t.label}
            stroke={t.color}
            dot={false}
            strokeWidth={1.5}
            isAnimationActive={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
