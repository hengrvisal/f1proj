"use client";

import { useMemo } from "react";
import {
  ComposedChart,
  Area,
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

export default function ThrottleBrakeTrace({ traces, syncId }: Props) {
  const primary = traces[0];

  const data = useMemo(() => {
    if (!primary) return [];

    // Build a lookup map for the second trace by distance_m
    const secondMap = new Map<number, TelemetrySample>();
    if (traces[1]) {
      for (const s of traces[1].data) {
        secondMap.set(s.distance_m, s);
      }
    }

    // Collect all unique distance values from both traces
    const allDistances = new Set<number>();
    for (const s of primary.data) allDistances.add(s.distance_m);
    for (const d of secondMap.keys()) allDistances.add(d);

    const primaryMap = new Map<number, TelemetrySample>();
    for (const s of primary.data) primaryMap.set(s.distance_m, s);

    return Array.from(allDistances)
      .sort((a, b) => a - b)
      .map((dist) => {
        const p = primaryMap.get(dist);
        const s = secondMap.get(dist);
        return {
          distance_m: dist,
          throttle: p?.throttle ?? undefined,
          brake: p ? (p.brake ? 100 : 0) : undefined,
          throttle2: s?.throttle ?? undefined,
          brake2: s ? (s.brake ? 100 : 0) : undefined,
        };
      });
  }, [primary, traces]);

  if (!primary || !data.length) return null;

  return (
    <ResponsiveContainer width="100%" height={180}>
      <ComposedChart syncId={syncId} data={data} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
        <XAxis
          dataKey="distance_m"
          type="number"
          domain={["dataMin", "dataMax"]}
          tick={{ fill: "#888899", fontSize: 11 }}
          axisLine={{ stroke: "#2a2a3a" }}
          allowDuplicatedCategory={false}
        />
        <YAxis
          domain={[0, 100]}
          tick={{ fill: "#888899", fontSize: 11 }}
          axisLine={{ stroke: "#2a2a3a" }}
          label={{ value: "%", angle: -90, position: "insideLeft", fill: "#888899", fontSize: 11 }}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "#1a1a24",
            border: "1px solid #2a2a3a",
            borderRadius: 8,
            fontSize: 12,
          }}
        />
        <Area
          dataKey="throttle"
          name={`${primary.label} Throttle`}
          stroke="#43B02A"
          fill="#43B02A"
          fillOpacity={0.2}
          dot={false}
          strokeWidth={1.5}
          isAnimationActive={false}
          connectNulls
        />
        <Line
          dataKey="brake"
          name={`${primary.label} Brake`}
          stroke="#E10600"
          dot={false}
          strokeWidth={1.5}
          isAnimationActive={false}
          connectNulls
        />
        {traces[1] && (
          <>
            <Area
              dataKey="throttle2"
              name={`${traces[1].label} Throttle`}
              stroke="#00D2BE"
              fill="#00D2BE"
              fillOpacity={0.1}
              dot={false}
              strokeWidth={1}
              strokeDasharray="4 2"
              isAnimationActive={false}
              connectNulls
            />
            <Line
              dataKey="brake2"
              name={`${traces[1].label} Brake`}
              stroke="#FF8000"
              dot={false}
              strokeWidth={1}
              strokeDasharray="4 2"
              isAnimationActive={false}
              connectNulls
            />
          </>
        )}
      </ComposedChart>
    </ResponsiveContainer>
  );
}
