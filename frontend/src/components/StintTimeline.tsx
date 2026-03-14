"use client";

import { StrategyDriver } from "@/lib/api";
import { COMPOUND_COLORS } from "@/lib/teams";

interface Props {
  strategies: StrategyDriver[];
}

export default function StintTimeline({ strategies }: Props) {
  if (!strategies.length) return null;

  const maxLap = Math.max(
    ...strategies.flatMap((s) => s.stints.map((st) => st.end_lap ?? 0))
  );

  return (
    <div className="space-y-2">
      {strategies.map((driver) => (
        <div key={driver.driver_id} className="flex items-center gap-3">
          <div className="w-12 text-sm font-bold text-right">{driver.code}</div>
          <div className="flex-1 h-7 relative bg-background rounded-md overflow-hidden">
            {driver.stints.map((stint) => {
              const start = stint.start_lap ?? 0;
              const end = stint.end_lap ?? start;
              const left = (start / maxLap) * 100;
              const width = ((end - start) / maxLap) * 100;
              const color = COMPOUND_COLORS[stint.compound?.toUpperCase()] ?? "#888899";

              return (
                <div
                  key={stint.stint_number}
                  className="absolute top-0.5 bottom-0.5 rounded-sm flex items-center justify-center text-[10px] font-medium"
                  style={{
                    left: `${left}%`,
                    width: `${Math.max(width, 1)}%`,
                    backgroundColor: color + "44",
                    borderLeft: `2px solid ${color}`,
                    color: color,
                  }}
                  title={`${stint.compound} | Laps ${start}-${end}${
                    stint.deg_rate_ms_per_lap
                      ? ` | Deg: ${stint.deg_rate_ms_per_lap.toFixed(1)} ms/lap`
                      : ""
                  }`}
                >
                  {width > 5 && stint.compound?.charAt(0)}
                </div>
              );
            })}
          </div>
        </div>
      ))}

      {/* Legend */}
      <div className="flex gap-4 mt-3 ml-16 text-xs text-muted">
        {Object.entries(COMPOUND_COLORS).map(([name, color]) => (
          <div key={name} className="flex items-center gap-1">
            <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: color }} />
            {name}
          </div>
        ))}
      </div>
    </div>
  );
}
