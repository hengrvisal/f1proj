"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import Link from "next/link";

const SESSION_LABELS: Record<string, string> = {
  R: "Race",
  Q: "Qualifying",
  S: "Sprint",
  SQ: "Sprint Qualifying",
  FP1: "Practice 1",
  FP2: "Practice 2",
  FP3: "Practice 3",
};

export default function RacesPage() {
  const [season, setSeason] = useState(2024);

  const { data: races, isLoading } = useQuery({
    queryKey: ["races", season],
    queryFn: () => api.races(season),
  });

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Season Calendar</h1>
          <p className="text-muted mt-1">2023–2024 season calendar with session links</p>
        </div>
        <select
          value={season}
          onChange={(e) => setSeason(Number(e.target.value))}
          className="bg-card border border-border rounded-lg px-3 py-2 text-sm"
        >
          <option value={2024}>2024</option>
          <option value={2023}>2023</option>
        </select>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="bg-card rounded-xl border border-border p-5 space-y-3">
              <div className="flex items-start gap-4">
                <div className="animate-pulse bg-border rounded h-8 w-10" />
                <div className="space-y-2 flex-1">
                  <div className="animate-pulse bg-border rounded h-5 w-48" />
                  <div className="animate-pulse bg-border rounded h-4 w-36" />
                  <div className="animate-pulse bg-border rounded h-3 w-24" />
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="space-y-3">
          {races?.map((race) => {
            const raceSession = race.sessions.find((s) => s.type === "R");
            return (
              <div
                key={race.id}
                className="bg-card rounded-xl border border-border p-5 hover:border-border/80 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-4">
                    <div className="text-2xl font-bold text-muted font-mono w-10 text-right">
                      {race.round}
                    </div>
                    <div>
                      <h2 className="text-lg font-semibold">{race.name}</h2>
                      <div className="text-sm text-muted">
                        {race.circuit} — {race.country}
                      </div>
                      {race.date && (
                        <div className="text-xs text-muted mt-1">{race.date}</div>
                      )}
                    </div>
                  </div>

                  <div className="flex gap-2">
                    {race.sessions.map((s) => (
                      <Link
                        key={s.id}
                        href={`/telemetry?session=${s.id}`}
                        className="px-2 py-1 text-xs bg-background rounded-md hover:bg-card-hover transition-colors"
                        title={SESSION_LABELS[s.type] ?? s.type}
                      >
                        {SESSION_LABELS[s.type] ?? s.type}
                      </Link>
                    ))}
                  </div>
                </div>

                <div className="flex gap-3 mt-3">
                  {raceSession && (
                    <>
                      <Link
                        href={`/telemetry?session=${raceSession.id}`}
                        className="text-xs text-accent hover:underline"
                      >
                        Telemetry
                      </Link>
                      <Link
                        href={`/tyres?session=${raceSession.id}`}
                        className="text-xs text-accent hover:underline"
                      >
                        Tyre Analysis
                      </Link>
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
