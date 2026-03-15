"use client";

import { useState } from "react";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  Label,
} from "recharts";
import { ClusterDriver, PcaInfo } from "@/lib/api";
import { getTeamColor, CLUSTER_COLORS } from "@/lib/teams";

// Map feature keys to plain-English pole descriptions [low ←, → high]
const FEATURE_POLES: Record<string, [string, string]> = {
  brake_aggression: ["Gentle braking", "Aggressive braking"],
  corner_entry_speed: ["Cautious entry", "Fast entry"],
  corner_exit_efficiency: ["Low exit speed", "High exit speed"],
  throttle_application: ["Gradual throttle", "Aggressive throttle"],
  tyre_management: ["Hard on tyres", "Easy on tyres"],
  quali_vs_race: ["Race-focused", "Quali-focused"],
  overtake_aggression: ["Patient overtaker", "Aggressive overtaker"],
  consistency: ["Variable", "Consistent"],
  avg_corner_time_delta: ["Slow through corners", "Fast through corners"],
  gear_usage_style: ["Conservative gears", "Aggressive gears"],
  brake_point_rel_mean: ["Early braker", "Late braker"],
  brake_point_rel_std: ["Variable braking", "Consistent braking"],
  corner_entry_speed_rel: ["Cautious entry", "Fast entry"],
  corner_apex_speed_rel: ["Low apex speed", "High apex speed"],
  corner_exit_speed_rel: ["Low exit speed", "High exit speed"],
  throttle_delay_after_apex: ["Early throttle", "Late throttle"],
  trail_braking_score: ["Low trail braking", "High trail braking"],
  slow_corner_speed: ["Slow in tight turns", "Fast in tight turns"],
  medium_corner_speed: ["Slow in medium turns", "Fast in medium turns"],
  fast_corner_speed: ["Slow in fast turns", "Fast in fast turns"],
  avg_tyre_deg_rate: ["Hard on tyres", "Easy on tyres"],
  quali_race_pace_delta: ["Race-focused", "Quali-focused"],
  wet_performance_delta: ["Weaker in wet", "Stronger in wet"],
  consistency_score: ["Variable", "Consistent"],
};

function getAxisPoles(axis: "pc1" | "pc2", pcaInfo: PcaInfo | null): { low: string; high: string } | null {
  if (!pcaInfo) return null;
  const features = axis === "pc1" ? pcaInfo.pc1_features : pcaInfo.pc2_features;
  if (!features.length) return null;
  const topFeature = features[0];
  const poles = FEATURE_POLES[topFeature];
  if (!poles) return null;
  return { low: poles[0], high: poles[1] };
}

const FEATURE_DISPLAY: Record<string, string> = {
  brake_aggression: "Brake Aggression",
  corner_entry_speed: "Corner Entry Speed",
  corner_exit_efficiency: "Exit Efficiency",
  throttle_application: "Throttle Application",
  tyre_management: "Tyre Management",
  quali_vs_race: "Quali vs Race",
  overtake_aggression: "Overtake Aggression",
  consistency: "Consistency",
  avg_corner_time_delta: "Corner Time Delta",
  gear_usage_style: "Gear Usage",
  brake_point_rel_mean: "Late Braking",
  brake_point_rel_std: "Braking Consistency",
  corner_entry_speed_rel: "Entry Speed",
  corner_apex_speed_rel: "Apex Speed",
  corner_exit_speed_rel: "Exit Speed",
  throttle_delay_after_apex: "Throttle Application",
  trail_braking_score: "Trail Braking",
  slow_corner_speed: "Slow Corners",
  medium_corner_speed: "Medium Corners",
  fast_corner_speed: "Fast Corners",
  avg_tyre_deg_rate: "Tyre Management",
  quali_race_pace_delta: "Quali vs Race",
  consistency_score: "Consistency",
  wet_performance_delta: "Wet Performance",
  overtake_aggression_raw: "Aggression",
};

function formatFeatureName(f: string): string {
  return FEATURE_DISPLAY[f] || f.replace(/_/g, " ");
}

interface Props {
  drivers: ClusterDriver[];
  colorBy?: "team" | "cluster";
  pcaInfo?: PcaInfo | null;
  onDriverClick?: (driver: ClusterDriver) => void;
}

export default function ClusterScatterPlot({
  drivers,
  colorBy = "team",
  pcaInfo,
  onDriverClick,
}: Props) {
  const [mode, setMode] = useState<"pca" | "tsne">("pca");

  // Filter out drivers with no coordinates (insufficient data)
  const validDrivers = drivers.filter(
    (d) => d.pca_x != null && d.pca_y != null
  );

  const data = validDrivers.map((d) => ({
    ...d,
    x: mode === "pca" ? d.pca_x : d.tsne_x,
    y: mode === "pca" ? d.pca_y : d.tsne_y,
  }));

  // Group by cluster for legend
  const clusters = new Map<number, typeof data>();
  for (const d of data) {
    if (!clusters.has(d.cluster_id)) clusters.set(d.cluster_id, []);
    clusters.get(d.cluster_id)!.push(d);
  }

  const xPoles = mode === "pca" ? getAxisPoles("pc1", pcaInfo ?? null) : null;
  const yPoles = mode === "pca" ? getAxisPoles("pc2", pcaInfo ?? null) : null;

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <span className="text-sm text-muted">Projection:</span>
        <button
          onClick={() => setMode("pca")}
          className={`px-3 py-1 text-sm rounded-lg transition-colors ${
            mode === "pca"
              ? "bg-accent text-white"
              : "bg-card-hover text-muted hover:text-foreground"
          }`}
        >
          PCA
        </button>
        <button
          onClick={() => setMode("tsne")}
          className={`px-3 py-1 text-sm rounded-lg transition-colors ${
            mode === "tsne"
              ? "bg-accent text-white"
              : "bg-card-hover text-muted hover:text-foreground"
          }`}
        >
          t-SNE
        </button>
        <span className="text-xs text-muted/60 ml-1">
          {mode === "pca"
            ? "Axes show what separates drivers — position tells you why"
            : "Optimized for clusters — nearby drivers have similar styles"}
        </span>
      </div>

      {/* Pole labels for PCA mode */}
      {mode === "pca" && xPoles && (
        <div className="flex justify-between text-xs text-muted mb-1 px-12">
          <span>← {xPoles.low}</span>
          <span>{xPoles.high} →</span>
        </div>
      )}

      <div className="relative">
        {/* Y-axis pole labels */}
        {mode === "pca" && yPoles && (
          <>
            <div className="absolute left-0 top-2 text-xs text-muted writing-mode-vertical" style={{ writingMode: "vertical-rl", transform: "rotate(180deg)" }}>
              ← {yPoles.low}
            </div>
            <div className="absolute left-0 bottom-10 text-xs text-muted writing-mode-vertical" style={{ writingMode: "vertical-rl", transform: "rotate(180deg)" }}>
              {yPoles.high} →
            </div>
          </>
        )}

      <ResponsiveContainer width="100%" height={500}>
        <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
          <XAxis
            type="number"
            dataKey="x"
            tick={{ fill: "#888899", fontSize: 12 }}
            axisLine={{ stroke: "#2a2a3a" }}
            tickLine={false}
          />
          <YAxis
            type="number"
            dataKey="y"
            tick={{ fill: "#888899", fontSize: 12 }}
            axisLine={{ stroke: "#2a2a3a" }}
            tickLine={false}
          />
          <Tooltip
            content={({ payload }) => {
              if (!payload?.length) return null;
              const d = payload[0].payload as (typeof data)[0];
              return (
                <div className="bg-card border border-border rounded-lg p-3 shadow-lg">
                  <div className="font-bold">{d.code}</div>
                  <div className="text-sm text-muted">
                    {d.first_name} {d.last_name}
                  </div>
                  <div className="text-sm text-muted">{d.team}</div>
                  <div className="text-xs mt-1 text-accent">
                    {d.cluster_label}
                  </div>
                </div>
              );
            }}
          />
          <Scatter data={data} onClick={(d) => onDriverClick?.(d as unknown as ClusterDriver)}>
            {data.map((d, i) => (
              <Cell
                key={i}
                fill={
                  colorBy === "team"
                    ? getTeamColor(d.team)
                    : CLUSTER_COLORS[d.cluster_id % CLUSTER_COLORS.length]
                }
                stroke="#0f0f13"
                strokeWidth={1}
                r={7}
                cursor="pointer"
              />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
      </div>

      {/* Cluster legend */}
      <div className="flex flex-wrap gap-4 mt-4">
        {Array.from(clusters.entries()).map(([cid, members]) => (
          <div key={cid} className="flex items-center gap-2 text-sm">
            <div
              className="w-3 h-3 rounded-full"
              style={{
                backgroundColor:
                  CLUSTER_COLORS[cid % CLUSTER_COLORS.length],
              }}
            />
            <span className="text-muted">
              {members[0].cluster_label} ({members.length})
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
