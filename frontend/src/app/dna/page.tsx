"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, ClusterDriver } from "@/lib/api";
import ClusterScatterPlot from "@/components/ClusterScatterPlot";
import SimilarityHeatmap from "@/components/SimilarityHeatmap";
import RadarChart from "@/components/RadarChart";
import { CLUSTER_COLORS } from "@/lib/teams";
import AIAnalysisPanel from "@/components/AIAnalysisPanel";

export default function DnaPage() {
  const [season, setSeason] = useState(2024);
  const [selectedDriver, setSelectedDriver] = useState<ClusterDriver | null>(null);
  const [colorBy, setColorBy] = useState<"team" | "cluster">("team");

  const { data: clustersData, isLoading } = useQuery({
    queryKey: ["dna-clusters", season],
    queryFn: () => api.dnaClusters(season),
  });

  const clusters = clustersData?.drivers;
  const pcaInfo = clustersData?.pca_info;

  const { data: similarity } = useQuery({
    queryKey: ["dna-similarity", season],
    queryFn: () => api.dnaSimilarity(season),
  });

  const { data: driverProfile } = useQuery({
    queryKey: ["dna-driver", selectedDriver?.driver_id, season],
    queryFn: () => api.dnaDriver(selectedDriver!.driver_id, season),
    enabled: !!selectedDriver,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-muted">Loading Driver DNA data...</div>
      </div>
    );
  }

  // Group clusters for cards (exclude "Insufficient Data" drivers)
  const clusterGroups = new Map<number, ClusterDriver[]>();
  for (const d of clusters ?? []) {
    if (d.cluster_id < 0) continue;
    if (!clusterGroups.has(d.cluster_id)) clusterGroups.set(d.cluster_id, []);
    clusterGroups.get(d.cluster_id)!.push(d);
  }

  // Insufficient data drivers
  const insufficientDrivers = (clusters ?? []).filter((d) => d.cluster_id < 0);

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Driver DNA</h1>
          <p className="text-muted mt-1">
            Driving style clustering from telemetry features
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={season}
            onChange={(e) => setSeason(Number(e.target.value))}
            className="bg-card border border-border rounded-lg px-3 py-2 text-sm"
          >
            <option value={2024}>2024</option>
            <option value={2023}>2023</option>
          </select>
          <button
            onClick={() => setColorBy(colorBy === "team" ? "cluster" : "team")}
            className="px-3 py-2 text-sm bg-card border border-border rounded-lg hover:bg-card-hover transition-colors"
          >
            Color: {colorBy === "team" ? "Team" : "Cluster"}
          </button>
        </div>
      </div>

      {/* Scatter Plot */}
      <div className="bg-card rounded-xl border border-border p-6">
        <h2 className="text-lg font-semibold mb-4">Driver Clustering</h2>
        {clusters && (
          <ClusterScatterPlot
            drivers={clusters}
            colorBy={colorBy}
            pcaInfo={pcaInfo}
            onDriverClick={setSelectedDriver}
          />
        )}
      </div>

      {/* Selected Driver Profile */}
      {selectedDriver && driverProfile && (
        <div className="bg-card rounded-xl border border-border p-6">
          <h2 className="text-lg font-semibold mb-4">
            {selectedDriver.first_name} {selectedDriver.last_name}
            <span className="ml-2 text-sm text-muted">
              ({selectedDriver.team})
            </span>
            <span
              className="ml-2 text-xs px-2 py-0.5 rounded-full"
              style={{
                backgroundColor:
                  CLUSTER_COLORS[
                    selectedDriver.cluster_id >= 0
                      ? selectedDriver.cluster_id % CLUSTER_COLORS.length
                      : 0
                  ] + "22",
                color:
                  CLUSTER_COLORS[
                    selectedDriver.cluster_id >= 0
                      ? selectedDriver.cluster_id % CLUSTER_COLORS.length
                      : 0
                  ],
              }}
            >
              {selectedDriver.cluster_label}
            </span>
          </h2>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div>
              <h3 className="text-sm font-medium text-muted mb-3">
                Feature Profile
              </h3>
              <RadarChart
                drivers={[
                  {
                    code: selectedDriver.code,
                    team: selectedDriver.team,
                    features: driverProfile.features,
                  },
                ]}
              />
            </div>
            <div>
              <h3 className="text-sm font-medium text-muted mb-3">
                Most Similar Drivers
              </h3>
              <div className="space-y-2">
                {driverProfile.most_similar.map((d) => (
                  <div
                    key={d.id}
                    className="flex items-center justify-between px-4 py-2 bg-background rounded-lg"
                  >
                    <span className="font-medium">{d.code}</span>
                    <span className="text-sm text-muted">
                      {(d.similarity * 100).toFixed(1)}%
                    </span>
                  </div>
                ))}
              </div>

              <h3 className="text-sm font-medium text-muted mt-6 mb-3">
                Least Similar Drivers
              </h3>
              <div className="space-y-2">
                {driverProfile.least_similar.map((d) => (
                  <div
                    key={d.id}
                    className="flex items-center justify-between px-4 py-2 bg-background rounded-lg"
                  >
                    <span className="font-medium">{d.code}</span>
                    <span className="text-sm text-muted">
                      {(d.similarity * 100).toFixed(1)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <AIAnalysisPanel driverId={selectedDriver.driver_id} season={season} />
        </div>
      )}

      {/* Cluster Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from(clusterGroups.entries()).map(([cid, members]) => (
          <div
            key={cid}
            className="bg-card rounded-xl border border-border p-5"
          >
            <div className="flex items-center gap-2 mb-3">
              <div
                className="w-3 h-3 rounded-full"
                style={{
                  backgroundColor:
                    CLUSTER_COLORS[cid % CLUSTER_COLORS.length],
                }}
              />
              <h3 className="font-semibold">{members[0].cluster_label}</h3>
              <span className="text-sm text-muted">({members.length})</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {members.map((d) => (
                <button
                  key={d.driver_id}
                  onClick={() => setSelectedDriver(d)}
                  className="px-2 py-1 text-sm bg-background rounded-md hover:bg-card-hover transition-colors"
                >
                  {d.code}
                </button>
              ))}
            </div>
          </div>
        ))}

        {/* Insufficient Data card */}
        {insufficientDrivers.length > 0 && (
          <div className="bg-card rounded-xl border border-border p-5 opacity-60">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-3 h-3 rounded-full bg-gray-500" />
              <h3 className="font-semibold">Insufficient Data</h3>
              <span className="text-sm text-muted">
                ({insufficientDrivers.length})
              </span>
            </div>
            <div className="flex flex-wrap gap-2">
              {insufficientDrivers.map((d) => (
                <span
                  key={d.driver_id}
                  className="px-2 py-1 text-sm bg-background rounded-md text-muted"
                >
                  {d.code}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Similarity Heatmap */}
      {similarity && (
        <div className="bg-card rounded-xl border border-border p-6">
          <h2 className="text-lg font-semibold mb-4">Similarity Matrix</h2>
          <SimilarityHeatmap data={similarity} />
        </div>
      )}
    </div>
  );
}
