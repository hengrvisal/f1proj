"use client";

import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, SeasonMetricRow } from "@/lib/api";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceDot,
} from "recharts";

const METRICS = [
  { key: "consistency", label: "Consistency", color: "#22d3ee", rawKey: "consistency_raw", rawUnit: "CV" },
  { key: "entry_speed", label: "Entry Speed", color: "#f472b6", rawKey: "entry_speed_raw", rawUnit: "km/h" },
  { key: "throttle_application", label: "Throttle App.", color: "#a78bfa", rawKey: "throttle_application_raw", rawUnit: "m delay" },
  { key: "overtake_rate", label: "Overtake Rate", color: "#fb923c", rawKey: "overtake_rate_raw", rawUnit: "positions" },
  { key: "tyre_management", label: "Tyre Mgmt", color: "#4ade80", rawKey: "tyre_management_raw", rawUnit: "ms/lap deg" },
  { key: "quali_proxy", label: "Quali Proxy", color: "#facc15", rawKey: "quali_proxy_raw", rawUnit: "ms" },
] as const;

type MetricKey = (typeof METRICS)[number]["key"];

const METRIC_DESCRIPTIONS: Record<MetricKey, string> = {
  consistency: "High = lap times barely varied race to race \u00b7 Low = big swings between laps",
  entry_speed: "High = carried more speed into corners \u00b7 Low = braked earlier, scrubbed more speed",
  throttle_application: "High = got back on power earlier after apex \u00b7 Low = cautious, delayed throttle",
  overtake_rate: "High = consistently gained places from grid position \u00b7 Low = lost positions or started well and faded",
  tyre_management: "High = pace held up late in stints \u00b7 Low = significant degradation over a stint",
  quali_proxy: "High = started near the front \u00b7 Low = started near the back of the grid",
};

function scoreLabel(score: number): string {
  if (score >= 75) return "strong";
  if (score >= 50) return "average";
  if (score >= 25) return "below average";
  return "weak";
}

function getScoreBand(score: number) {
  if (score >= 80) return { label: "elite", color: "#4ade80", bg: "#4ade8020" };
  if (score >= 60) return { label: "strong", color: "#4ade80", bg: "#4ade8020" };
  if (score >= 40) return { label: "midfield", color: "#f59e0b", bg: "#f59e0b20" };
  if (score >= 20) return { label: "below average", color: "#ef4444", bg: "#ef444420" };
  return { label: "struggling", color: "#ef4444", bg: "#ef444420" };
}

const DELTA_STYLES = {
  ahead: { color: "#27500A", bg: "#EAF3DE", fill: "#27500A" },
  behind: { color: "#791F1F", bg: "#FCEBEB", fill: "#791F1F" },
} as const;

function DeltaPill({ delta, mode = "default" }: { delta: number; mode?: "default" | "trend" }) {
  const isAhead = delta > 0;
  const style = isAhead ? DELTA_STYLES.ahead : DELTA_STYLES.behind;
  const suffix = mode === "trend"
    ? (isAhead ? "better" : "worse")
    : (isAhead ? "ahead" : "behind");
  return (
    <span
      className="inline-flex items-center gap-1 font-mono font-medium rounded-lg whitespace-nowrap"
      style={{
        fontSize: 11,
        padding: "2px 8px",
        borderRadius: 8,
        color: style.color,
        backgroundColor: style.bg,
      }}
    >
      {isAhead ? (
        <svg width="8" height="6" viewBox="0 0 8 6"><polygon points="4,0 8,6 0,6" fill={style.fill} /></svg>
      ) : (
        <svg width="8" height="6" viewBox="0 0 8 6"><polygon points="4,6 8,0 0,0" fill={style.fill} /></svg>
      )}
      {isAhead ? "+" : ""}{delta.toFixed(1)} {suffix}
    </span>
  );
}

function GridRankPill({ rank, total }: { rank: number; total: number }) {
  return (
    <span
      className="font-medium whitespace-nowrap"
      style={{
        fontSize: 11,
        padding: "2px 8px",
        borderRadius: 8,
        background: "var(--color-background, #1a1a2e)",
        border: "0.5px solid var(--color-border, #2a2a3a)",
        color: "var(--color-muted, #888899)",
      }}
    >
      {ordinal(rank)} of {total}
    </span>
  );
}

function ProgressBar({ score }: { score: number }) {
  const band = getScoreBand(score);
  return (
    <div
      style={{
        margin: "0 0 14px",
        height: 4,
        borderRadius: 2,
        background: "var(--color-border, #2a2a3a)",
        position: "relative",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          position: "absolute",
          left: 0,
          top: 0,
          height: "100%",
          width: `${Math.min(Math.max(score, 0), 100)}%`,
          borderRadius: 2,
          background: band.color,
        }}
      />
    </div>
  );
}

function ordinal(n: number): string {
  const s = ["th", "st", "nd", "rd"];
  const v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
}

function formatRaw(key: MetricKey, val: number | null): string {
  if (val == null) return "\u2014";
  switch (key) {
    case "consistency":
      return `${((1 - val) * 100).toFixed(1)}%`;
    case "entry_speed":
      return `${val.toFixed(1)} km/h`;
    case "throttle_application":
      return `${val.toFixed(0)}m`;
    case "overtake_rate":
      if (val >= -0.5 && val <= 0.5) return "met expectation";
      return val > 0 ? `+${val.toFixed(1)} places better than avg` : `${Math.abs(val).toFixed(1)} places worse than avg`;
    case "tyre_management":
      return `${val.toFixed(1)} ms/lap`;
    case "quali_proxy":
      return `${(val / 1000).toFixed(3)}s`;
    default:
      return `${val}`;
  }
}

const RAW_LABEL: Record<MetricKey, string> = {
  consistency: "Lap time CV",
  entry_speed: "Avg entry speed",
  throttle_application: "Throttle delay",
  overtake_rate: "vs expected",
  tyre_management: "Deg rate",
  quali_proxy: "Best Q time",
};

function rollingAvg(
  values: (number | null)[],
  dnfFlags: boolean[],
  window = 3
): (number | null)[] {
  return values.map((_, i) => {
    const slice: number[] = [];
    for (let j = Math.max(0, i - window + 1); j <= i; j++) {
      if (values[j] != null && !dnfFlags[j]) slice.push(values[j]!);
    }
    return slice.length ? slice.reduce((a, b) => a + b, 0) / slice.length : null;
  });
}

/** Compute summary stats for a single driver's metric rows */
function computeDriverStats(driverRows: SeasonMetricRow[], metricKey: MetricKey) {
  const clean = driverRows.filter(
    (r) => r[metricKey as keyof SeasonMetricRow] != null && !r.had_dnf
  );
  const allValid = driverRows.filter(
    (r) => r[metricKey as keyof SeasonMetricRow] != null
  );
  if (!allValid.length) return null;

  const values = clean.map((r) => r[metricKey as keyof SeasonMetricRow] as number);
  const allValues = allValid.map((r) => r[metricKey as keyof SeasonMetricRow] as number);

  const first3 = values.slice(0, Math.min(3, values.length));
  const last3 = values.slice(-Math.min(3, values.length));
  const firstAvg = first3.length ? Math.round(first3.reduce((s, v) => s + v, 0) / first3.length * 10) / 10 : null;
  const lastAvg = last3.length ? Math.round(last3.reduce((s, v) => s + v, 0) / last3.length * 10) / 10 : null;
  const trend = firstAvg != null && lastAvg != null ? Math.round((lastAvg - firstAvg) * 10) / 10 : null;
  const peak = allValues.length ? Math.max(...allValues) : null;

  // Find the peak row for race name info
  const peakRow = peak != null ? allValid.find((r) => (r[metricKey as keyof SeasonMetricRow] as number) === peak) : null;

  return { firstAvg, lastAvg, trend, peak, peakRow };
}

interface Props {
  driverCode: string;
  season: number;
  allDrivers?: { code: string; team: string }[];
}

export default function SeasonTrajectory({ driverCode, season, allDrivers }: Props) {
  const [activeMetric, setActiveMetric] = useState<MetricKey>("consistency");

  const { data: rows, isLoading } = useQuery({
    queryKey: ["season-metrics", driverCode, season],
    queryFn: () => api.seasonMetrics(driverCode, season),
  });

  // Fetch all drivers' season metrics for rankings
  const { data: allMetrics } = useQuery({
    queryKey: ["all-season-metrics", season],
    queryFn: () => api.allSeasonMetrics(season),
    staleTime: 5 * 60 * 1000,
  });

  const metric = METRICS.find((m) => m.key === activeMetric)!;

  const chartData = useMemo(() => {
    if (!rows) return [];
    const values = rows.map(
      (r) => r[activeMetric as keyof SeasonMetricRow] as number | null
    );
    const dnfFlags = rows.map((r) => r.had_dnf);
    const avg = rollingAvg(values, dnfFlags);

    return rows.map((r, i) => ({
      round: r.race_round,
      name: r.race_name,
      value: values[i],
      avg: avg[i],
      raw: r[(metric.rawKey) as keyof SeasonMetricRow] as number | null,
      overtakePasses: r.overtake_passes,
      hadDnf: r.had_dnf,
      hadSc: r.had_safety_car,
    }));
  }, [rows, activeMetric, metric.rawKey]);

  // Summary stats — exclude DNF rounds so they don't distort trends
  const { best, worst, startAvg, endAvg, delta, trendLabel } = useMemo(() => {
    const clean = chartData.filter((d) => d.value != null && !d.hadDnf) as {
      round: number;
      name: string;
      value: number;
    }[];
    const allValid = chartData.filter((d) => d.value != null) as {
      round: number;
      name: string;
      value: number;
    }[];
    if (!allValid.length)
      return { best: null, worst: null, startAvg: null, endAvg: null, delta: null, trendLabel: null };

    const best = allValid.reduce((a, b) => (b.value > a.value ? b : a));
    const worst = allValid.reduce((a, b) => (b.value < a.value ? b : a));

    if (!clean.length)
      return { best, worst, startAvg: null, endAvg: null, delta: null, trendLabel: null };

    const first3 = clean.slice(0, Math.min(3, clean.length));
    const last3 = clean.slice(-Math.min(3, clean.length));
    const startAvg = Math.round(first3.reduce((s, d) => s + d.value, 0) / first3.length * 10) / 10;
    const endAvg = Math.round(last3.reduce((s, d) => s + d.value, 0) / last3.length * 10) / 10;
    const delta = Math.round((endAvg - startAvg) * 10) / 10;
    const trendLabel = delta > 3 ? "improving \u2191" : delta < -3 ? "declining \u2193" : "stable \u2192";

    return { best, worst, startAvg, endAvg, delta, trendLabel };
  }, [chartData]);

  // Grid rankings and teammate data
  const { gridRank, gridTotal, teammateStats, myStats } = useMemo(() => {
    if (!allMetrics) return { gridRank: null, gridTotal: null, teammateStats: null, myStats: null };

    // Group rows by driver
    const byDriver = new Map<string, SeasonMetricRow[]>();
    for (const row of allMetrics) {
      if (!byDriver.has(row.driver)) byDriver.set(row.driver, []);
      byDriver.get(row.driver)!.push(row);
    }

    // Compute summary stats per driver
    const driverSummaries: { code: string; firstAvg: number | null; lastAvg: number | null; trend: number | null; peak: number | null }[] = [];
    for (const [code, driverRows] of byDriver) {
      const stats = computeDriverStats(driverRows, activeMetric);
      if (stats) {
        driverSummaries.push({ code, ...stats });
      }
    }

    const myStats = driverSummaries.find((d) => d.code === driverCode) ?? null;

    // Compute rankings for each stat type
    const withFirst = driverSummaries.filter((d) => d.firstAvg != null);
    const withLast = driverSummaries.filter((d) => d.lastAvg != null);
    const withTrend = driverSummaries.filter((d) => d.trend != null);
    const withPeak = driverSummaries.filter((d) => d.peak != null);

    const sortedFirst = [...withFirst].sort((a, b) => (b.firstAvg ?? 0) - (a.firstAvg ?? 0));
    const sortedLast = [...withLast].sort((a, b) => (b.lastAvg ?? 0) - (a.lastAvg ?? 0));
    const sortedTrend = [...withTrend].sort((a, b) => (b.trend ?? 0) - (a.trend ?? 0));
    const sortedPeak = [...withPeak].sort((a, b) => (b.peak ?? 0) - (a.peak ?? 0));

    const gridTotal = driverSummaries.length;

    const firstRank = sortedFirst.findIndex((d) => d.code === driverCode) + 1 || null;
    const lastRank = sortedLast.findIndex((d) => d.code === driverCode) + 1 || null;
    const trendRank = sortedTrend.findIndex((d) => d.code === driverCode) + 1 || null;
    const peakRank = sortedPeak.findIndex((d) => d.code === driverCode) + 1 || null;

    // Teammate detection
    let teammateStats: { code: string; firstAvg: number | null; lastAvg: number | null; trend: number | null; peak: number | null } | null = null;
    if (allDrivers) {
      const myTeam = allDrivers.find((d) => d.code === driverCode)?.team;
      if (myTeam) {
        const teammateCodes = allDrivers
          .filter((d) => d.team === myTeam && d.code !== driverCode)
          .map((d) => d.code);
        if (teammateCodes.length > 0) {
          teammateStats = driverSummaries.find((d) => teammateCodes.includes(d.code)) ?? null;
        }
      }
    }

    return {
      gridRank: { first: firstRank, last: lastRank, trend: trendRank, peak: peakRank },
      gridTotal,
      teammateStats,
      myStats,
    };
  }, [allMetrics, activeMetric, driverCode, allDrivers]);

  if (isLoading) {
    return (
      <div className="space-y-3">
        <div className="animate-pulse bg-border rounded h-4 w-40" />
        <div className="animate-pulse bg-border rounded-lg h-48" />
      </div>
    );
  }

  if (!rows || rows.length === 0) {
    return (
      <div className="text-sm text-muted text-center py-8">
        No season trajectory data available
      </div>
    );
  }

  // Find the peak race name for the Peak chip
  const peakRaceName = best ? rows.find((r) => r.race_round === best.round)?.race_name : null;

  // Band transition for Trend chip
  const startBand = startAvg != null ? getScoreBand(startAvg) : null;
  const endBand = endAvg != null ? getScoreBand(endAvg) : null;
  const bandTransition =
    startBand && endBand
      ? startBand.label === endBand.label
        ? "stable"
        : `${startBand.label} \u2192 ${endBand.label}`
      : null;

  return (
    <div>
      <h3 className="text-sm font-medium text-muted mb-3">Season Trajectory</h3>

      {/* Metric tabs */}
      <div className="flex flex-wrap gap-1.5 mb-2">
        {METRICS.map((m) => (
          <button
            key={m.key}
            onClick={() => setActiveMetric(m.key)}
            className={`px-2.5 py-1 text-xs rounded-md transition-colors ${
              activeMetric === m.key
                ? "text-white font-medium"
                : "bg-background text-muted hover:text-foreground"
            }`}
            style={
              activeMetric === m.key
                ? { backgroundColor: m.color + "cc" }
                : undefined
            }
          >
            {m.label}
          </button>
        ))}
      </div>

      <p className="text-[11px] text-muted/60 mb-3">
        {METRIC_DESCRIPTIONS[activeMetric]}
      </p>

      {/* Chart with raw line + rolling avg */}
      <ResponsiveContainer width="100%" height={220}>
        <LineChart
          data={chartData}
          margin={{ top: 15, right: 10, bottom: 35, left: 0 }}
        >
          <XAxis
            dataKey="name"
            tick={(props: Record<string, unknown>) => {
              const x = Number(props.x ?? 0);
              const y = Number(props.y ?? 0);
              const payload = props.payload as { value: string; index: number } | undefined;
              const idx = payload?.index ?? 0;
              const d = chartData[idx];
              return (
                <g transform={`translate(${x},${y})`}>
                  <text
                    x={0}
                    y={0}
                    dy={4}
                    textAnchor="end"
                    fill="#888899"
                    fontSize={10}
                    transform="rotate(-90)"
                  >
                    {payload?.value ?? ""}
                  </text>
                  {d?.hadSc && (
                    <text x={0} y={30} textAnchor="middle" fill="#f59e0b" fontSize={7} fontWeight={600}>
                      SC
                    </text>
                  )}
                  {d?.hadDnf && (
                    <text x={0} y={d?.hadSc ? 38 : 30} textAnchor="middle" fill="#ef4444" fontSize={7} fontWeight={600}>
                      DNF
                    </text>
                  )}
                </g>
              );
            }}
            axisLine={{ stroke: "#2a2a3a" }}
            tickLine={false}
            height={60}
            interval={0}
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fill: "#888899", fontSize: 10 }}
            axisLine={{ stroke: "#2a2a3a" }}
            tickLine={false}
            width={30}
          />
          <Tooltip
            content={({ payload }) => {
              if (!payload?.length) return null;
              const d = payload[0]?.payload;
              if (!d || d.value == null) return null;
              const score = d.value as number;
              const verdict = scoreLabel(score);
              const verdictColor =
                score >= 75 ? "#4ade80" : score >= 50 ? "#facc15" : score >= 25 ? "#fb923c" : "#ef4444";
              return (
                <div className="bg-card border border-border rounded-lg p-2.5 shadow-lg text-xs">
                  <div className="font-medium">
                    R{d.round} — {d.name}
                    {d.hadDnf && <span className="ml-1.5 text-red-400">DNF</span>}
                    {d.hadSc && <span className="ml-1.5 text-amber-400">SC</span>}
                  </div>
                  <div className="mt-1" style={{ color: metric.color }}>
                    {metric.label}: {score.toFixed(0)}{" "}
                    <span style={{ color: verdictColor }}>({verdict})</span>
                  </div>
                  {activeMetric === "overtake_rate" && d.overtakePasses != null && (
                    <div className="mt-0.5 text-muted">
                      On-track passes: {d.overtakePasses}
                    </div>
                  )}
                  <div className={`mt-0.5 ${
                    activeMetric === "overtake_rate" && d.raw != null
                      ? d.raw > 0.5 ? "text-green-400" : d.raw < -0.5 ? "text-red-400" : "text-muted"
                      : "text-muted"
                  }`}>
                    {RAW_LABEL[activeMetric]}: {formatRaw(activeMetric, d.raw)}
                  </div>
                </div>
              );
            }}
          />
          {/* Raw per-race line */}
          <Line
            type="monotone"
            dataKey="value"
            stroke={metric.color}
            strokeWidth={1.5}
            strokeOpacity={0.4}
            dot={{ r: 2.5, fill: metric.color, strokeWidth: 0, fillOpacity: 0.5 }}
            connectNulls={false}
            activeDot={{ r: 5, strokeWidth: 0 }}
          />
          {/* 3-race rolling average */}
          <Line
            type="monotone"
            dataKey="avg"
            stroke={metric.color}
            strokeWidth={2.5}
            dot={false}
            connectNulls={false}
            activeDot={false}
          />
          {best && (
            <ReferenceDot
              x={best.name}
              y={best.value}
              r={5}
              fill={metric.color}
              stroke="#fff"
              strokeWidth={1.5}
              label={{
                value: "Best",
                position: "top",
                fill: metric.color,
                fontSize: 9,
                fontWeight: 600,
              }}
            />
          )}
          {worst && worst.round !== best?.round && (
            <ReferenceDot
              x={worst.name}
              y={worst.value}
              r={5}
              fill="#ef4444"
              stroke="#fff"
              strokeWidth={1.5}
              label={{
                value: "Low",
                position: "bottom",
                fill: "#ef4444",
                fontSize: 9,
                fontWeight: 600,
              }}
            />
          )}
        </LineChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="flex items-center gap-4 text-[10px] text-muted mt-1 mb-3">
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-5 h-px" style={{ backgroundColor: metric.color, opacity: 0.4 }} />
          Raw
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-5 h-0.5 rounded" style={{ backgroundColor: metric.color }} />
          3-race avg
        </span>
      </div>

      {/* Summary chips */}
      {startAvg != null && endAvg != null && delta != null && best && (
        <div className="grid grid-cols-2" style={{ gap: 16 }}>
          {/* First 3 Races chip */}
          <div className="bg-background rounded-lg" style={{ padding: "1.25rem 1.5rem" }}>
            <div className="flex items-center justify-between" style={{ marginBottom: 12 }}>
              <div className="text-[10px] text-muted uppercase tracking-wide font-medium">
                First 3 Races
              </div>
              {gridRank?.first && gridTotal && (
                <GridRankPill rank={gridRank.first} total={gridTotal} />
              )}
            </div>
            <div className="flex items-baseline gap-2" style={{ marginBottom: 14 }}>
              <span style={{ fontSize: 28, fontWeight: 500 }} className="font-mono leading-none">
                {startAvg.toFixed(1)}
              </span>
              <span
                style={{ fontSize: 13, fontWeight: 500, color: getScoreBand(startAvg).color }}
              >
                {getScoreBand(startAvg).label}
              </span>
            </div>
            <ProgressBar score={startAvg} />
            {teammateStats?.firstAvg != null && (() => {
              const d = Math.round((startAvg - teammateStats.firstAvg!) * 10) / 10;
              return (
                <div className="flex items-center justify-between" style={{ paddingTop: 14 }}>
                  <span style={{ fontSize: 12 }} className="text-muted">
                    Teammate {teammateStats.firstAvg!.toFixed(1)}
                  </span>
                  <DeltaPill delta={d} />
                </div>
              );
            })()}
          </div>

          {/* Last 3 Races chip */}
          <div className="bg-background rounded-lg" style={{ padding: "1.25rem 1.5rem" }}>
            <div className="flex items-center justify-between" style={{ marginBottom: 12 }}>
              <div className="text-[10px] text-muted uppercase tracking-wide font-medium">
                Last 3 Races
              </div>
              {gridRank?.last && gridTotal && (
                <GridRankPill rank={gridRank.last} total={gridTotal} />
              )}
            </div>
            <div className="flex items-baseline gap-2" style={{ marginBottom: 14 }}>
              <span style={{ fontSize: 28, fontWeight: 500 }} className="font-mono leading-none">
                {endAvg.toFixed(1)}
              </span>
              <span
                style={{ fontSize: 13, fontWeight: 500, color: getScoreBand(endAvg).color }}
              >
                {getScoreBand(endAvg).label}
              </span>
            </div>
            <ProgressBar score={endAvg} />
            {teammateStats?.lastAvg != null && (() => {
              const d = Math.round((endAvg - teammateStats.lastAvg!) * 10) / 10;
              return (
                <div className="flex items-center justify-between" style={{ paddingTop: 14 }}>
                  <span style={{ fontSize: 12 }} className="text-muted">
                    Teammate {teammateStats.lastAvg!.toFixed(1)}
                  </span>
                  <DeltaPill delta={d} />
                </div>
              );
            })()}
          </div>

          {/* Trend chip */}
          <div className="bg-background rounded-lg" style={{ padding: "1.25rem 1.5rem" }}>
            <div className="flex items-center justify-between" style={{ marginBottom: 12 }}>
              <div className="text-[10px] text-muted uppercase tracking-wide font-medium">
                Trend
              </div>
              {gridRank?.trend && gridTotal && (
                <GridRankPill rank={gridRank.trend} total={gridTotal} />
              )}
            </div>
            <div className="flex items-baseline gap-2" style={{ marginBottom: 14 }}>
              <span
                style={{ fontSize: 28, fontWeight: 500 }}
                className={`font-mono leading-none ${
                  delta > 3
                    ? "text-green-400"
                    : delta < -3
                      ? "text-red-400"
                      : "text-muted"
                }`}
              >
                {delta > 0 ? "+" : ""}
                {delta.toFixed(1)}
              </span>
              <span
                style={{
                  fontSize: 13,
                  fontWeight: 500,
                  color: endBand?.color ?? "#888899",
                }}
              >
                {bandTransition === "stable"
                  ? `${endBand?.label ?? ""} stable`
                  : bandTransition ?? trendLabel}
              </span>
            </div>
            <ProgressBar score={endAvg} />
            {teammateStats?.trend != null && (() => {
              const d = Math.round((delta - teammateStats.trend!) * 10) / 10;
              return (
                <div className="flex items-center justify-between" style={{ paddingTop: 14 }}>
                  <span style={{ fontSize: 12 }} className="text-muted">
                    Teammate {teammateStats.trend! > 0 ? "+" : ""}{teammateStats.trend!.toFixed(1)}
                  </span>
                  <DeltaPill delta={d} mode="trend" />
                </div>
              );
            })()}
          </div>

          {/* Peak chip */}
          <div className="bg-background rounded-lg" style={{ padding: "1.25rem 1.5rem" }}>
            <div className="flex items-center justify-between" style={{ marginBottom: 12 }}>
              <div className="text-[10px] text-muted uppercase tracking-wide font-medium">
                Peak
              </div>
              {gridRank?.peak && gridTotal && (
                <GridRankPill rank={gridRank.peak} total={gridTotal} />
              )}
            </div>
            <div className="flex items-baseline gap-2" style={{ marginBottom: 14 }}>
              <span style={{ fontSize: 28, fontWeight: 500 }} className="font-mono leading-none">
                {best.value.toFixed(1)}
              </span>
              <span
                style={{ fontSize: 13, fontWeight: 500, color: getScoreBand(best.value).color }}
              >
                {getScoreBand(best.value).label}
              </span>
            </div>
            <div style={{ fontSize: 12, margin: "4px 0 14px" }} className="text-muted">
              {peakRaceName ? `${peakRaceName} \u00b7 R${best.round}` : `R${best.round}`}
            </div>
            {teammateStats?.peak != null && (() => {
              const d = Math.round((best.value - teammateStats.peak!) * 10) / 10;
              return (
                <div className="flex items-center justify-between" style={{ paddingTop: 14 }}>
                  <span style={{ fontSize: 12 }} className="text-muted">
                    Teammate {teammateStats.peak!.toFixed(1)}
                  </span>
                  <DeltaPill delta={d} />
                </div>
              );
            })()}
          </div>
        </div>
      )}
    </div>
  );
}
