"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import DegCurveChart from "@/components/DegCurveChart";
import StintTimeline from "@/components/StintTimeline";

export default function TyresPage() {
  const [season, setSeason] = useState(2024);
  const [raceId, setRaceId] = useState<number | null>(null);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [selectedDriver, setSelectedDriver] = useState<string | undefined>(undefined);

  const { data: races } = useQuery({
    queryKey: ["races", season],
    queryFn: () => api.races(season),
  });

  const selectedRace = races?.find((r) => r.id === raceId);

  const { data: strategies } = useQuery({
    queryKey: ["tyre-strategy", sessionId],
    queryFn: () => api.tyreStrategy(sessionId!),
    enabled: !!sessionId,
  });

  const { data: degCurves, isLoading } = useQuery({
    queryKey: ["tyre-deg", sessionId],
    queryFn: () => api.tyreDegCurves(sessionId!),
    enabled: !!sessionId,
  });

  const driverCodes = Array.from(
    new Set(degCurves?.map((c) => c.code) ?? [])
  ).sort();

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <h1 className="text-3xl font-bold">Tyre Degradation</h1>

      <div className="flex flex-wrap items-center gap-3">
        <select
          value={season}
          onChange={(e) => { setSeason(Number(e.target.value)); setRaceId(null); setSessionId(null); }}
          className="bg-card border border-border rounded-lg px-3 py-2 text-sm"
        >
          <option value={2024}>2024</option>
          <option value={2023}>2023</option>
        </select>

        <select
          value={raceId ?? ""}
          onChange={(e) => {
            const rid = Number(e.target.value) || null;
            setRaceId(rid);
            // Auto-select race session
            const race = races?.find((r) => r.id === rid);
            const raceSession = race?.sessions.find((s) => s.type === "R");
            setSessionId(raceSession?.id ?? null);
          }}
          className="bg-card border border-border rounded-lg px-3 py-2 text-sm"
        >
          <option value="">Select Race</option>
          {races?.map((r) => (
            <option key={r.id} value={r.id}>
              R{r.round} - {r.name}
            </option>
          ))}
        </select>

        {driverCodes.length > 0 && (
          <select
            value={selectedDriver ?? ""}
            onChange={(e) => setSelectedDriver(e.target.value || undefined)}
            className="bg-card border border-border rounded-lg px-3 py-2 text-sm"
          >
            <option value="">All Drivers</option>
            {driverCodes.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        )}
      </div>

      {isLoading && <div className="text-muted py-8 text-center">Loading tyre data...</div>}

      {/* Stint Timeline */}
      {strategies && strategies.length > 0 && (
        <div className="bg-card rounded-xl border border-border p-6">
          <h2 className="text-lg font-semibold mb-4">Strategy Overview</h2>
          <StintTimeline strategies={strategies} />
        </div>
      )}

      {/* Deg Curves */}
      {degCurves && degCurves.length > 0 && (
        <div className="bg-card rounded-xl border border-border p-6">
          <h2 className="text-lg font-semibold mb-4">Degradation Curves</h2>
          <DegCurveChart curves={degCurves} selectedDriver={selectedDriver} />
        </div>
      )}

      {/* Summary Stats */}
      {degCurves && degCurves.length > 0 && (
        <div className="bg-card rounded-xl border border-border p-6">
          <h2 className="text-lg font-semibold mb-4">Compound Comparison</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {["SOFT", "MEDIUM", "HARD"].map((compound) => {
              const compoundCurves = degCurves.filter(
                (c) => c.compound?.toUpperCase() === compound
              );
              if (!compoundCurves.length) return null;

              const avgDeg =
                compoundCurves.reduce((s, c) => s + (c.deg_rate_ms_per_lap ?? 0), 0) /
                compoundCurves.length;
              const avgR2 =
                compoundCurves.reduce((s, c) => s + (c.r_squared ?? 0), 0) /
                compoundCurves.length;

              const compoundColors: Record<string, string> = {
                SOFT: "#FF3333",
                MEDIUM: "#FFDD00",
                HARD: "#EEEEEE",
              };

              return (
                <div
                  key={compound}
                  className="bg-background rounded-lg p-4 border-l-4"
                  style={{ borderColor: compoundColors[compound] }}
                >
                  <h3 className="font-semibold mb-2" style={{ color: compoundColors[compound] }}>
                    {compound}
                  </h3>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted">Stints</span>
                      <span>{compoundCurves.length}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted">Avg Deg Rate</span>
                      <span>{avgDeg.toFixed(1)} ms/lap</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted">Avg R²</span>
                      <span>{avgR2.toFixed(3)}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
