"use client";

import { useRef, useState } from "react";
import { api, DriverAIAnalysis } from "@/lib/api";

interface Props {
  driverId: number;
  season: number;
}

export default function AIAnalysisPanel({ driverId, season }: Props) {
  const cache = useRef<Map<string, DriverAIAnalysis>>(new Map());
  const [state, setState] = useState<"idle" | "loading" | "result" | "error">("idle");
  const [analysis, setAnalysis] = useState<DriverAIAnalysis | null>(null);
  const [error, setError] = useState("");

  const cacheKey = `${driverId}-${season}`;

  async function handleAnalyse() {
    const cached = cache.current.get(cacheKey);
    if (cached) {
      setAnalysis(cached);
      setState("result");
      return;
    }

    setState("loading");
    setError("");
    try {
      const result = await api.aiAnalyseDriver(driverId, season);
      cache.current.set(cacheKey, result);
      setAnalysis(result);
      setState("result");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed");
      setState("error");
    }
  }

  if (state === "idle") {
    return (
      <button
        onClick={handleAnalyse}
        className="mt-4 px-5 py-2.5 bg-accent hover:bg-accent-hover text-white font-medium rounded-lg transition-colors text-sm"
      >
        Analyse Driver
      </button>
    );
  }

  if (state === "loading") {
    return (
      <div className="mt-4 bg-card rounded-xl border border-border p-6 space-y-4 animate-pulse">
        <div className="h-8 w-32 bg-border rounded" />
        <div className="space-y-3">
          <div className="h-4 w-3/4 bg-border rounded" />
          <div className="h-4 w-1/2 bg-border rounded" />
          <div className="h-4 w-2/3 bg-border rounded" />
          <div className="h-4 w-5/6 bg-border rounded" />
        </div>
      </div>
    );
  }

  if (state === "error") {
    return (
      <div className="mt-4 space-y-2">
        <div className="text-red-400 text-sm">{error}</div>
        <button
          onClick={handleAnalyse}
          className="px-4 py-2 bg-card border border-border rounded-lg text-sm hover:bg-card-hover transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!analysis) return null;

  const verdictColor =
    analysis.confidence >= 80
      ? "text-green-400"
      : analysis.confidence >= 60
        ? "text-yellow-400"
        : "text-orange-400";

  return (
    <div className="mt-4 bg-card rounded-xl border border-border p-6">
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-lg font-semibold">AI Analysis</h3>
        <button
          onClick={() => setState("idle")}
          className="text-xs text-muted hover:text-foreground transition-colors"
        >
          Dismiss
        </button>
      </div>

      {/* Confidence header */}
      <div className="flex items-center gap-4 mb-6">
        <div className={`text-4xl font-bold ${verdictColor}`}>
          {analysis.confidence}
        </div>
        <div>
          <span
            className={`text-sm font-medium px-2.5 py-1 rounded-full ${
              analysis.confidence >= 80
                ? "bg-green-400/15 text-green-400"
                : analysis.confidence >= 60
                  ? "bg-yellow-400/15 text-yellow-400"
                  : "bg-orange-400/15 text-orange-400"
            }`}
          >
            {analysis.confidenceVerdict}
          </span>
        </div>
      </div>

      {/* Analysis sections */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Section title="Driving Style" content={analysis.style} />
        <Section title="Strengths" content={analysis.strengths} />
        <Section title="Areas to Watch" content={analysis.areas} />
        <Section title="Analyst Verdict" content={analysis.verdict} />
      </div>
    </div>
  );
}

function Section({ title, content }: { title: string; content: string }) {
  return (
    <div className="bg-background rounded-lg p-4">
      <h4 className="text-xs font-medium text-muted uppercase tracking-wider mb-2">
        {title}
      </h4>
      <p className="text-sm leading-relaxed">{content}</p>
    </div>
  );
}
