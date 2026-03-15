"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, ClusterDriver } from "@/lib/api";
import ClusterScatterPlot from "@/components/ClusterScatterPlot";
import SimilarityHeatmap from "@/components/SimilarityHeatmap";
import RadarChart from "@/components/RadarChart";
import { CLUSTER_COLORS } from "@/lib/teams";
import AIAnalysisPanel from "@/components/AIAnalysisPanel";
import SeasonTrajectory from "@/components/SeasonTrajectory";

// Maps cluster labels (from backend) to their defining trait
const CLUSTER_TRAITS: Record<string, string> = {
  "Late Braker": "late braking into corners",
  "Early Braker": "early, conservative braking",
  "Brave Entry": "high corner entry speed",
  "Cautious Entry": "careful, controlled corner entry",
  "Strong Exit": "fast corner exit acceleration",
  "Weak Exit": "slower corner exit speed",
  "Late Throttle": "delayed throttle application",
  "Early Throttle": "quick throttle out of corners",
  "Tyre Whisperer": "excellent tyre preservation",
  "Hard on Tyres": "aggressive tyre usage",
  "Race Specialist": "race pace consistency",
  "Quali Specialist": "one-lap qualifying speed",
  "Aggressive Racer": "aggressive overtaking moves",
  "Position Holder": "patient, defensive racing",
  "Metronomic": "lap-to-lap consistency",
  "Erratic": "high lap time variation",
  "Slow through Corners": "low overall cornering speed",
  "Corner Speed Demon": "high cornering speed",
  "Aggressive Gearing": "aggressive gear shifts",
  "Conservative Gearing": "smooth, conservative gearing",
};

function getClusterTooltip(label: string): string {
  const trait = CLUSTER_TRAITS[label];
  const traitPhrase = trait ? ` (${trait})` : "";
  return `We average all trait values${traitPhrase} across the group to find the centroid, then measure each driver's distance from it. The % uses a Gaussian curve scaled to the overall grid spread — so 95% in one cluster means the same closeness as 95% in another.`;
}

const FEATURE_LABELS: Record<string, string> = {
  brake_aggression: "Brake Aggression",
  corner_entry_speed: "Entry Speed",
  corner_exit_efficiency: "Exit Efficiency",
  throttle_application: "Throttle Application",
  tyre_management: "Tyre Management",
  quali_vs_race: "Quali vs Race",
  overtake_aggression: "Aggression",
  consistency: "Consistency",
  avg_corner_time_delta: "Corner Speed",
  gear_usage_style: "Gear Usage",
  brake_point_rel_mean: "Late Braking",
  brake_point_rel_std: "Brake Consistency",
  corner_entry_speed_rel: "Entry Speed",
  corner_apex_speed_rel: "Apex Speed",
  corner_exit_speed_rel: "Exit Speed",
  throttle_delay_after_apex: "Throttle Delay",
  trail_braking_score: "Trail Braking",
  slow_corner_speed: "Slow Corners",
  medium_corner_speed: "Medium Corners",
  fast_corner_speed: "Fast Corners",
  avg_tyre_deg_rate: "Tyre Management",
  quali_race_pace_delta: "Quali vs Race",
  consistency_score: "Consistency",
  wet_performance_delta: "Wet Performance",
};

function formatFeature(key: string): string {
  return FEATURE_LABELS[key] || key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Rank drivers within a cluster by how close they are to the cluster centroid.
 *  Uses an absolute scale: fit = e^(-dist²/2σ²) where σ is the global spread
 *  across ALL drivers, so percentages are comparable across clusters. */
function rankDriversByCentroid(
  members: ClusterDriver[],
  allDrivers: ClusterDriver[]
): { driver: ClusterDriver; fit: number }[] {
  if (!members.length) return [];

  const featureKeys = Object.keys(members[0].features ?? {});
  if (!featureKeys.length) return members.map((d) => ({ driver: d, fit: 1 }));

  // Compute cluster centroid
  const centroid: Record<string, number> = {};
  for (const key of featureKeys) {
    centroid[key] = members.reduce((s, d) => s + (d.features?.[key] ?? 0), 0) / members.length;
  }

  // Compute global centroid (across all valid drivers) for σ
  const globalCentroid: Record<string, number> = {};
  for (const key of featureKeys) {
    globalCentroid[key] = allDrivers.reduce((s, d) => s + (d.features?.[key] ?? 0), 0) / allDrivers.length;
  }

  // σ = RMS distance of all drivers from the global centroid
  const sigma = Math.sqrt(
    allDrivers.reduce((s, d) => {
      const dist2 = featureKeys.reduce((ss, key) => ss + ((d.features?.[key] ?? 0) - globalCentroid[key]) ** 2, 0);
      return s + dist2;
    }, 0) / allDrivers.length
  ) || 1;

  // Gaussian fit for each member
  const ranked = members.map((d) => {
    const dist2 = featureKeys.reduce((s, key) => s + ((d.features?.[key] ?? 0) - centroid[key]) ** 2, 0);
    const fit = Math.exp(-dist2 / (2 * sigma * sigma));
    return { driver: d, fit };
  });

  return ranked.sort((a, b) => b.fit - a.fit);
}

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
      <div className="max-w-7xl mx-auto space-y-8">
        <div>
          <div className="animate-pulse bg-border rounded h-8 w-48 mb-2" />
          <div className="animate-pulse bg-border rounded h-4 w-72" />
        </div>
        <div className="bg-card rounded-xl border border-border p-6">
          <div className="animate-pulse bg-border rounded h-5 w-40 mb-4" />
          <div className="animate-pulse bg-border rounded-lg h-64" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="bg-card rounded-xl border border-border p-5 space-y-3">
              <div className="animate-pulse bg-border rounded h-4 w-32" />
              <div className="animate-pulse bg-border rounded h-8 w-full" />
            </div>
          ))}
        </div>
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
          <h1 className="text-4xl font-bold">Driver DNA</h1>
          <p className="text-foreground/70 text-lg mt-2">
            Every driver has a unique fingerprint — how they brake, carry speed through corners, and manage tyres.
          </p>
          <p className="text-foreground/50 mt-1">
            We extracted those traits from telemetry and grouped drivers with similar styles into clusters.
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
      {!selectedDriver && (
        <div className="bg-card rounded-xl border border-border p-8 text-center">
          <p className="text-muted">Click a driver on the scatter plot or in a cluster card below to view their profile</p>
        </div>
      )}

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
              <SeasonTrajectory
                driverCode={selectedDriver.code}
                season={season}
                allDrivers={(clusters ?? []).map(d => ({ code: d.code, team: d.team }))}
              />
            </div>
          </div>

          <AIAnalysisPanel driverId={selectedDriver.driver_id} season={season} />
        </div>
      )}

      {/* Cluster Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from(clusterGroups.entries()).map(([cid, members]) => {
          const validAll = (clusters ?? []).filter((d) => d.cluster_id >= 0);
          const ranked = rankDriversByCentroid(members, validAll);
          const clusterColor = CLUSTER_COLORS[cid % CLUSTER_COLORS.length];

          return (
            <div
              key={cid}
              className="bg-card rounded-xl border border-border p-5"
            >
              <div className="flex items-center gap-2 mb-1">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: clusterColor }}
                />
                <h3 className="font-semibold">{members[0].cluster_label}</h3>
                <span className="text-sm text-muted">({members.length})</span>
                <span className="ml-auto relative group/info">
                  <span className="w-4 h-4 rounded-full border border-muted/40 text-muted/60 text-[10px] flex items-center justify-center cursor-help hover:border-muted hover:text-muted transition-colors">
                    ?
                  </span>
                  <span className="absolute right-0 top-6 w-64 p-2.5 bg-card border border-border rounded-lg text-xs text-muted shadow-lg opacity-0 pointer-events-none group-hover/info:opacity-100 group-hover/info:pointer-events-auto transition-opacity z-10">
                    {getClusterTooltip(members[0].cluster_label)}
                  </span>
                </span>
              </div>
              <p className="text-xs text-muted mb-3">
                Defined by: {CLUSTER_TRAITS[members[0].cluster_label] ?? "unique driving traits"}
              </p>

              {/* Drivers ranked by closeness to cluster centroid */}
              <div className="space-y-1.5">
                {ranked.map(({ driver: d, fit }) => {
                  return (
                    <button
                      key={d.driver_id}
                      onClick={() => setSelectedDriver(d)}
                      className="w-full group"
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium w-10 text-left group-hover:text-accent transition-colors">
                          {d.code}
                        </span>
                        <div className="flex-1 h-2 bg-background rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all"
                            style={{
                              width: `${Math.max(fit * 100, 8)}%`,
                              backgroundColor: clusterColor,
                              opacity: 0.5 + fit * 0.5,
                            }}
                          />
                        </div>
                        <span className="text-xs text-muted w-10 text-right font-mono">
                          {(fit * 100).toFixed(0)}%
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}

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
