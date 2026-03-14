"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { getTeamColor, CLUSTER_COLORS } from "@/lib/teams";
import Link from "next/link";

export default function DriversPage() {
  const [season, setSeason] = useState(2024);

  const { data: drivers, isLoading } = useQuery({
    queryKey: ["drivers", season],
    queryFn: () => api.drivers(season),
  });

  if (isLoading) {
    return <div className="text-muted py-8 text-center">Loading drivers...</div>;
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Drivers</h1>
        <select
          value={season}
          onChange={(e) => setSeason(Number(e.target.value))}
          className="bg-card border border-border rounded-lg px-3 py-2 text-sm"
        >
          <option value={2024}>2024</option>
          <option value={2023}>2023</option>
        </select>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {drivers?.map((d) => {
          const teamColor = d.team_name ? getTeamColor(d.team_name) : "#888899";
          return (
            <Link
              key={d.id}
              href={`/dna?driver=${d.id}`}
              className="bg-card rounded-xl border border-border p-4 hover:border-accent/30 transition-colors group"
              style={{ borderLeftColor: teamColor, borderLeftWidth: 3 }}
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-2xl font-bold font-mono text-muted">
                    {d.permanent_number ?? "—"}
                  </div>
                  <div className="font-semibold text-lg group-hover:text-accent transition-colors">
                    {d.code}
                  </div>
                  <div className="text-sm text-muted">
                    {d.first_name} {d.last_name}
                  </div>
                </div>
              </div>

              <div className="mt-3 text-xs text-muted">{d.team_name}</div>

              {d.cluster_label && (
                <div
                  className="mt-2 inline-block px-2 py-0.5 text-xs rounded-full"
                  style={{
                    backgroundColor:
                      CLUSTER_COLORS[(d.cluster_id ?? 0) % CLUSTER_COLORS.length] + "22",
                    color:
                      CLUSTER_COLORS[(d.cluster_id ?? 0) % CLUSTER_COLORS.length],
                  }}
                >
                  {d.cluster_label}
                </div>
              )}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
