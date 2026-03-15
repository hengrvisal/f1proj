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
};

function formatFeatureName(f: string): string {
  return FEATURE_DISPLAY[f] || f.replace(/_/g, " ");
}

function formatAxisLabel(axis: "pc1" | "pc2", pcaInfo: PcaInfo | null): string {
  if (!pcaInfo) return axis === "pc1" ? "PC1" : "PC2";
  const variance = axis === "pc1" ? pcaInfo.pc1_variance : pcaInfo.pc2_variance;
  const features = axis === "pc1" ? pcaInfo.pc1_features : pcaInfo.pc2_features;
  const featureStr = features.map(formatFeatureName).join(", ");
  return `${axis.toUpperCase()} (${variance}% — ${featureStr})`;
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

  const xLabel =
    mode === "pca" ? formatAxisLabel("pc1", pcaInfo ?? null) : "t-SNE 1";
  const yLabel =
    mode === "pca" ? formatAxisLabel("pc2", pcaInfo ?? null) : "t-SNE 2";

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
      </div>

      <ResponsiveContainer width="100%" height={500}>
        <ScatterChart margin={{ top: 20, right: 20, bottom: 40, left: 20 }}>
          <XAxis
            type="number"
            dataKey="x"
            name={xLabel}
            tick={{ fill: "#888899", fontSize: 12 }}
            axisLine={{ stroke: "#2a2a3a" }}
          >
            <Label
              value={xLabel}
              position="bottom"
              offset={15}
              style={{ fill: "#888899", fontSize: 12 }}
            />
          </XAxis>
          <YAxis
            type="number"
            dataKey="y"
            name={yLabel}
            tick={{ fill: "#888899", fontSize: 12 }}
            axisLine={{ stroke: "#2a2a3a" }}
          >
            <Label
              value={yLabel}
              angle={-90}
              position="left"
              offset={0}
              style={{ fill: "#888899", fontSize: 12 }}
            />
          </YAxis>
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
