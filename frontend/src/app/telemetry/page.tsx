"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import SpeedTrace from "@/components/SpeedTrace";
import ThrottleBrakeTrace from "@/components/ThrottleBrakeTrace";
import GearTrace from "@/components/GearTrace";
import TrackMap from "@/components/TrackMap";
import { getTeamColor } from "@/lib/teams";

const SESSION_LABELS: Record<string, string> = {
  R: "Race",
  Q: "Qualifying",
  S: "Sprint",
  SQ: "Sprint Qualifying",
  FP1: "Practice 1",
  FP2: "Practice 2",
  FP3: "Practice 3",
};

export default function TelemetryPage() {
  const [season, setSeason] = useState(2024);
  const [raceId, setRaceId] = useState<number | null>(null);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [driverA, setDriverA] = useState<number | null>(null);
  const [driverB, setDriverB] = useState<number | null>(null);
  const [trackColorBy, setTrackColorBy] = useState<"speed" | "throttle" | "gear">("speed");

  const { data: races } = useQuery({
    queryKey: ["races", season],
    queryFn: () => api.races(season),
  });

  // Fetch drivers with telemetry for the selected session
  const { data: telemetryDrivers } = useQuery({
    queryKey: ["telemetry-drivers", sessionId],
    queryFn: () => api.telemetryDrivers(sessionId!),
    enabled: !!sessionId,
  });

  const selectedRace = races?.find((r) => r.id === raceId);

  const hasValidSelection = !!sessionId && !!driverA && !!driverB && driverA !== driverB;

  const { data: comparison, isLoading } = useQuery({
    queryKey: ["telemetry-compare", sessionId, driverA, driverB],
    queryFn: () => api.telemetryCompare(sessionId!, driverA!, driverB!),
    enabled: hasValidSelection,
  });

  const { data: corners } = useQuery({
    queryKey: ["corners", selectedRace?.circuit_id],
    queryFn: () => api.circuitCorners(selectedRace!.circuit_id),
    enabled: !!selectedRace,
  });

  const driverAInfo = telemetryDrivers?.find((d) => d.id === driverA);
  const driverBInfo = telemetryDrivers?.find((d) => d.id === driverB);
  const colorA = "#E10600";
  const colorB = "#00D2BE";

  const hasTraces = comparison?.driver_a?.trace?.length && comparison?.driver_b?.trace?.length;

  const traces = hasTraces
    ? [
        { label: driverAInfo?.code ?? "A", color: colorA, data: comparison!.driver_a.trace },
        { label: driverBInfo?.code ?? "B", color: colorB, data: comparison!.driver_b.trace },
      ]
    : [];

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Telemetry Explorer</h1>
        <p className="text-muted mt-1">Compare speed, throttle, brake, and gear traces between drivers</p>
      </div>

      {/* Selectors */}
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={season}
          onChange={(e) => { setSeason(Number(e.target.value)); setRaceId(null); setSessionId(null); setDriverA(null); setDriverB(null); }}
          className="bg-card border border-border rounded-lg px-3 py-2 text-sm"
        >
          <option value={2024}>2024</option>
          <option value={2023}>2023</option>
        </select>

        <select
          value={raceId ?? ""}
          onChange={(e) => { setRaceId(Number(e.target.value) || null); setSessionId(null); setDriverA(null); setDriverB(null); }}
          className="bg-card border border-border rounded-lg px-3 py-2 text-sm"
        >
          <option value="">Select Race</option>
          {races?.map((r) => (
            <option key={r.id} value={r.id}>
              R{r.round} - {r.name}
            </option>
          ))}
        </select>

        {selectedRace && (
          <select
            value={sessionId ?? ""}
            onChange={(e) => { setSessionId(Number(e.target.value) || null); setDriverA(null); setDriverB(null); }}
            className="bg-card border border-border rounded-lg px-3 py-2 text-sm"
          >
            <option value="">Select Session</option>
            {selectedRace.sessions.map((s) => (
              <option key={s.id} value={s.id}>
                {SESSION_LABELS[s.type] ?? s.type}
              </option>
            ))}
          </select>
        )}

        {sessionId && (
          <>
            <select
              value={driverA ?? ""}
              onChange={(e) => setDriverA(Number(e.target.value) || null)}
              className="bg-card border border-border rounded-lg px-3 py-2 text-sm"
            >
              <option value="">Driver A</option>
              {telemetryDrivers?.map((d) => (
                <option key={d.id} value={d.id}>{d.code} - {d.first_name} {d.last_name}</option>
              ))}
            </select>

            <span className="text-muted font-bold">vs</span>

            <select
              value={driverB ?? ""}
              onChange={(e) => setDriverB(Number(e.target.value) || null)}
              className="bg-card border border-border rounded-lg px-3 py-2 text-sm"
            >
              <option value="">Driver B</option>
              {telemetryDrivers?.filter((d) => d.id !== driverA).map((d) => (
                <option key={d.id} value={d.id}>{d.code} - {d.first_name} {d.last_name}</option>
              ))}
            </select>
          </>
        )}
      </div>

      {!sessionId && (
        <div className="bg-card rounded-xl border border-border p-12 text-center">
          <p className="text-muted">Select a race and session above to compare driver telemetry</p>
        </div>
      )}

      {sessionId && !hasValidSelection && !isLoading && telemetryDrivers && telemetryDrivers.length > 0 && (
        <div className="bg-card rounded-xl border border-border p-12 text-center">
          <p className="text-muted">Select two drivers above to compare their telemetry</p>
        </div>
      )}

      {sessionId && telemetryDrivers && telemetryDrivers.length === 0 && (
        <div className="bg-card rounded-xl border border-border p-12 text-center">
          <p className="text-muted">No telemetry data available for this session</p>
        </div>
      )}

      {isLoading && (
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="bg-card rounded-xl border border-border p-4">
              <div className="animate-pulse bg-border rounded h-4 w-24 mb-3" />
              <div className="animate-pulse bg-border rounded-lg h-48" />
            </div>
          ))}
        </div>
      )}

      {comparison?.error && (
        <div className="text-amber-400 py-8 text-center">{comparison.error}</div>
      )}

      {hasTraces && (
        <div className="space-y-4">
          <div className="flex items-center gap-6 text-sm">
            <span>
              <span className="inline-block w-3 h-3 rounded-full mr-1" style={{ backgroundColor: colorA }} />
              {driverAInfo?.code} (Lap {comparison!.driver_a.lap})
            </span>
            <span>
              <span className="inline-block w-3 h-3 rounded-full mr-1" style={{ backgroundColor: colorB }} />
              {driverBInfo?.code} (Lap {comparison!.driver_b.lap})
            </span>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-[1fr_400px] gap-4">
            <div className="space-y-4">
              <div className="bg-card rounded-xl border border-border p-4">
                <h3 className="text-sm font-medium text-muted mb-2">Speed</h3>
                <SpeedTrace traces={traces} corners={corners?.corners} syncId="telemetry" />
              </div>
              <div className="bg-card rounded-xl border border-border p-4">
                <h3 className="text-sm font-medium text-muted mb-2">Throttle & Brake</h3>
                <ThrottleBrakeTrace traces={traces} syncId="telemetry" />
              </div>
              <div className="bg-card rounded-xl border border-border p-4">
                <h3 className="text-sm font-medium text-muted mb-2">Gear</h3>
                <GearTrace traces={traces} syncId="telemetry" />
              </div>
            </div>

            <div className="bg-card rounded-xl border border-border p-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-medium text-muted">Track Map</h3>
                <select
                  value={trackColorBy}
                  onChange={(e) => setTrackColorBy(e.target.value as "speed" | "throttle" | "gear")}
                  className="bg-background border border-border rounded px-2 py-1 text-xs"
                >
                  <option value="speed">Speed</option>
                  <option value="throttle">Throttle</option>
                  <option value="gear">Gear</option>
                </select>
              </div>
              <TrackMap
                samples={comparison!.driver_a.trace}
                colorBy={trackColorBy}
                width={360}
                height={360}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
