"use client";

import {
  Radar,
  RadarChart as RechartsRadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from "recharts";
import { getTeamColor } from "@/lib/teams";

const FEATURE_LABELS: Record<string, string> = {
  brake_point_rel_mean: "Late Braking",
  corner_entry_speed_rel: "Entry Speed",
  corner_apex_speed_rel: "Apex Speed",
  corner_exit_speed_rel: "Exit Speed",
  throttle_delay_after_apex: "Throttle App.",
  trail_braking_score: "Trail Braking",
  avg_tyre_deg_rate: "Tyre Mgmt",
  overtake_aggression: "Aggression",
  consistency_score: "Consistency",
};

interface DriverData {
  code: string;
  team?: string;
  features: Record<string, number>;
}

interface Props {
  drivers: DriverData[];
}

export default function RadarChart({ drivers }: Props) {
  // Normalize features to 0-100 scale across all drivers
  const featureKeys = Object.keys(FEATURE_LABELS);
  const allValues: Record<string, number[]> = {};
  for (const key of featureKeys) {
    allValues[key] = drivers.map((d) => d.features[key] ?? 0);
  }

  const data = featureKeys.map((key) => {
    const values = allValues[key];
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;

    const point: Record<string, string | number> = {
      feature: FEATURE_LABELS[key],
    };
    for (const d of drivers) {
      const raw = d.features[key] ?? 0;
      point[d.code] = Math.round(((raw - min) / range) * 100);
    }
    return point;
  });

  const colors = ["#E10600", "#00D2BE", "#FF8700", "#0090FF"];

  return (
    <ResponsiveContainer width="100%" height={450}>
      <RechartsRadarChart data={data} cx="50%" cy="50%" outerRadius="75%">
        <PolarGrid stroke="#2a2a3a" />
        <PolarAngleAxis
          dataKey="feature"
          tick={{ fill: "#888899", fontSize: 11 }}
        />
        <PolarRadiusAxis
          angle={30}
          domain={[0, 100]}
          tick={{ fill: "#555", fontSize: 10 }}
          axisLine={false}
        />
        {drivers.map((d, i) => (
          <Radar
            key={d.code}
            name={d.code}
            dataKey={d.code}
            stroke={d.team ? getTeamColor(d.team) : colors[i % colors.length]}
            fill={d.team ? getTeamColor(d.team) : colors[i % colors.length]}
            fillOpacity={0.15}
            strokeWidth={2}
          />
        ))}
        <Legend
          wrapperStyle={{ color: "#888899", fontSize: 13 }}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "#1a1a24",
            border: "1px solid #2a2a3a",
            borderRadius: 8,
          }}
        />
      </RechartsRadarChart>
    </ResponsiveContainer>
  );
}
