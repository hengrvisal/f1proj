"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import RadarChart from "@/components/RadarChart";

const FEATURE_LABELS: Record<string, string> = {
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
  overtake_aggression: "Aggression",
  consistency_score: "Consistency",
  wet_performance_delta: "Wet Performance",
};

export default function ComparePage() {
  const [season, setSeason] = useState(2024);
  const [driverA, setDriverA] = useState<number | null>(null);
  const [driverB, setDriverB] = useState<number | null>(null);

  const { data: drivers } = useQuery({
    queryKey: ["drivers", season],
    queryFn: () => api.drivers(season),
  });

  const { data: comparison } = useQuery({
    queryKey: ["dna-compare", driverA, driverB, season],
    queryFn: () => api.dnaCompare(driverA!, driverB!, season),
    enabled: !!driverA && !!driverB && driverA !== driverB,
  });

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Driver Comparison</h1>
        <p className="text-muted mt-1">Head-to-head DNA feature comparison</p>
      </div>

      <div className="flex items-center gap-4">
        <select
          value={season}
          onChange={(e) => setSeason(Number(e.target.value))}
          className="bg-card border border-border rounded-lg px-3 py-2 text-sm"
        >
          <option value={2024}>2024</option>
          <option value={2023}>2023</option>
        </select>

        <select
          value={driverA ?? ""}
          onChange={(e) => setDriverA(Number(e.target.value) || null)}
          className="bg-card border border-border rounded-lg px-3 py-2 text-sm flex-1"
        >
          <option value="">Select Driver A</option>
          {drivers?.map((d) => (
            <option key={d.id} value={d.id}>
              {d.code} - {d.first_name} {d.last_name}
            </option>
          ))}
        </select>

        <span className="text-muted font-bold">vs</span>

        <select
          value={driverB ?? ""}
          onChange={(e) => setDriverB(Number(e.target.value) || null)}
          className="bg-card border border-border rounded-lg px-3 py-2 text-sm flex-1"
        >
          <option value="">Select Driver B</option>
          {drivers?.map((d) => (
            <option key={d.id} value={d.id}>
              {d.code} - {d.first_name} {d.last_name}
            </option>
          ))}
        </select>
      </div>

      {(!driverA || !driverB || driverA === driverB) && (
        <div className="bg-card rounded-xl border border-border p-12 text-center">
          <p className="text-muted">Select two drivers above to compare their DNA profiles</p>
        </div>
      )}

      {comparison && comparison.drivers.length === 2 && (
        <>
          {comparison.similarity !== null && (
            <div className="text-center py-4">
              <span className="text-muted text-sm">Similarity Score: </span>
              <span className="text-2xl font-bold text-accent">
                {(comparison.similarity * 100).toFixed(1)}%
              </span>
            </div>
          )}

          <div className="bg-card rounded-xl border border-border p-6">
            <h2 className="text-lg font-semibold mb-4">Radar Comparison</h2>
            <RadarChart
              drivers={comparison.drivers.map((d) => ({
                code: d.code,
                features: d.features,
              }))}
            />
          </div>

          <div className="bg-card rounded-xl border border-border p-6">
            <h2 className="text-lg font-semibold mb-4">Feature Delta</h2>
            <div className="space-y-2">
              {Object.entries(FEATURE_LABELS).map(([key, label]) => {
                const a = comparison.drivers[0].features[key] ?? 0;
                const b = comparison.drivers[1].features[key] ?? 0;
                const delta = a - b;
                const maxAbs = Math.max(Math.abs(a), Math.abs(b), 0.01);
                const pctA = (a / maxAbs) * 50;
                const pctB = (b / maxAbs) * 50;

                return (
                  <div key={key} className="flex items-center gap-4">
                    <div className="w-36 text-sm text-muted text-right">
                      {label}
                    </div>
                    <div className="flex-1 flex items-center gap-2">
                      <div className="w-16 text-right text-sm font-mono">
                        {a.toFixed(2)}
                      </div>
                      <div className="flex-1 h-4 bg-background rounded-full relative overflow-hidden">
                        <div
                          className="absolute top-0 h-full rounded-full opacity-60"
                          style={{
                            left: `${50 - Math.max(0, -pctA)}%`,
                            width: `${Math.abs(pctA)}%`,
                            backgroundColor: "#E10600",
                          }}
                        />
                        <div
                          className="absolute top-0 h-full rounded-full opacity-60"
                          style={{
                            left: `${50 - Math.max(0, -pctB)}%`,
                            width: `${Math.abs(pctB)}%`,
                            backgroundColor: "#00D2BE",
                          }}
                        />
                        <div className="absolute left-1/2 top-0 w-px h-full bg-border" />
                      </div>
                      <div className="w-16 text-sm font-mono">
                        {b.toFixed(2)}
                      </div>
                    </div>
                    <div
                      className={`w-16 text-sm font-mono text-right ${
                        delta > 0 ? "text-green-400" : delta < 0 ? "text-red-400" : "text-muted"
                      }`}
                    >
                      {delta > 0 ? "+" : ""}
                      {delta.toFixed(2)}
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="flex justify-center gap-8 mt-4 text-sm text-muted">
              <span>
                <span className="inline-block w-3 h-3 rounded-full bg-[#E10600] mr-1" />
                {comparison.drivers[0].code}
              </span>
              <span>
                <span className="inline-block w-3 h-3 rounded-full bg-[#00D2BE] mr-1" />
                {comparison.drivers[1].code}
              </span>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
