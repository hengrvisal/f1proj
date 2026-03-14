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
} from "recharts";
import { ClusterDriver } from "@/lib/api";
import { getTeamColor, CLUSTER_COLORS } from "@/lib/teams";

interface Props {
  drivers: ClusterDriver[];
  colorBy?: "team" | "cluster";
  onDriverClick?: (driver: ClusterDriver) => void;
}

export default function ClusterScatterPlot({
  drivers,
  colorBy = "team",
  onDriverClick,
}: Props) {
  const [mode, setMode] = useState<"pca" | "tsne">("pca");

  const data = drivers.map((d) => ({
    ...d,
    x: mode === "pca" ? d.pca_x : d.tsne_x,
    y: mode === "pca" ? d.pca_y : d.tsne_y,
  }));

  // Group by cluster for hull rendering
  const clusters = new Map<number, typeof data>();
  for (const d of data) {
    if (!clusters.has(d.cluster_id)) clusters.set(d.cluster_id, []);
    clusters.get(d.cluster_id)!.push(d);
  }

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
        <span className="ml-4 text-sm text-muted">Color:</span>
        {/* Color toggle handled by parent via colorBy prop */}
      </div>

      <ResponsiveContainer width="100%" height={500}>
        <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
          <XAxis
            type="number"
            dataKey="x"
            name={mode === "pca" ? "PC1" : "t-SNE 1"}
            tick={{ fill: "#888899", fontSize: 12 }}
            axisLine={{ stroke: "#2a2a3a" }}
          />
          <YAxis
            type="number"
            dataKey="y"
            name={mode === "pca" ? "PC2" : "t-SNE 2"}
            tick={{ fill: "#888899", fontSize: 12 }}
            axisLine={{ stroke: "#2a2a3a" }}
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
