"use client";

import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Line,
  ComposedChart,
  Cell,
} from "recharts";
import { DegCurve } from "@/lib/api";
import { COMPOUND_COLORS } from "@/lib/teams";

interface Props {
  curves: DegCurve[];
  selectedDriver?: string;
}

export default function DegCurveChart({ curves, selectedDriver }: Props) {
  const filtered = selectedDriver
    ? curves.filter((c) => c.code === selectedDriver)
    : curves;

  if (!filtered.length) {
    return <div className="text-muted text-sm py-8 text-center">No degradation data available</div>;
  }

  // For each stint, build actual + fitted points
  return (
    <div className="space-y-4">
      {filtered.map((curve) => {
        const compoundColor = COMPOUND_COLORS[curve.compound?.toUpperCase()] ?? "#888899";

        // Generate fitted line points
        const fittedPoints: { tyre_life: number; fitted_ms: number }[] = [];
        if (curve.actual_laps.length > 0 && curve.coefficients.length > 0) {
          const minLife = Math.min(...curve.actual_laps.map((l) => l.tyre_life ?? 1));
          const maxLife = Math.max(...curve.actual_laps.map((l) => l.tyre_life ?? 1));
          for (let x = minLife; x <= maxLife; x++) {
            let y: number;
            if (curve.model_type === "quadratic" && curve.coefficients.length === 3) {
              y = curve.coefficients[0] * x * x + curve.coefficients[1] * x + curve.coefficients[2];
            } else {
              y = curve.coefficients[0] * x + (curve.coefficients[1] ?? 0);
            }
            fittedPoints.push({ tyre_life: x, fitted_ms: y });
          }
        }

        // Use baseline-relative (delta from first lap)
        const baseline = curve.actual_laps[0]?.time_ms ?? 0;
        const scatterData = curve.actual_laps.map((l) => ({
          tyre_life: l.tyre_life ?? l.lap - curve.actual_laps[0].lap + 1,
          delta_ms: l.time_ms - baseline,
        }));

        const allData = scatterData.map((s) => {
          const fitted = fittedPoints.find((f) => f.tyre_life === s.tyre_life);
          return { ...s, fitted_ms: fitted?.fitted_ms };
        });

        // Add fitted-only points
        for (const fp of fittedPoints) {
          if (!allData.find((d) => d.tyre_life === fp.tyre_life)) {
            allData.push({ tyre_life: fp.tyre_life, delta_ms: undefined as unknown as number, fitted_ms: fp.fitted_ms });
          }
        }
        allData.sort((a, b) => a.tyre_life - b.tyre_life);

        return (
          <div key={`${curve.code}-${curve.stint_number}`} className="bg-background rounded-lg p-4">
            <div className="flex items-center gap-3 mb-3">
              <span className="font-bold">{curve.code}</span>
              <span className="text-sm">Stint {curve.stint_number}</span>
              <span
                className="px-2 py-0.5 text-xs rounded-full font-medium"
                style={{ backgroundColor: compoundColor + "33", color: compoundColor }}
              >
                {curve.compound}
              </span>
              <span className="text-xs text-muted">
                R² = {curve.r_squared?.toFixed(3)} | Deg = {curve.deg_rate_ms_per_lap?.toFixed(1)} ms/lap
                {curve.predicted_cliff_lap && ` | Cliff ≈ Lap ${curve.predicted_cliff_lap}`}
              </span>
            </div>

            <ResponsiveContainer width="100%" height={200}>
              <ComposedChart data={allData} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
                <XAxis
                  dataKey="tyre_life"
                  tick={{ fill: "#888899", fontSize: 11 }}
                  axisLine={{ stroke: "#2a2a3a" }}
                  label={{ value: "Tyre Life (laps)", position: "bottom", fill: "#888899", fontSize: 11 }}
                />
                <YAxis
                  tick={{ fill: "#888899", fontSize: 11 }}
                  axisLine={{ stroke: "#2a2a3a" }}
                  label={{ value: "Δ ms", angle: -90, position: "insideLeft", fill: "#888899", fontSize: 11 }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#1a1a24",
                    border: "1px solid #2a2a3a",
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                />
                <Scatter dataKey="delta_ms" name="Actual" fill={compoundColor} r={4} />
                <Line
                  dataKey="fitted_ms"
                  name="Fitted"
                  stroke={compoundColor}
                  strokeWidth={2}
                  dot={false}
                  strokeDasharray="6 3"
                  isAnimationActive={false}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        );
      })}
    </div>
  );
}
