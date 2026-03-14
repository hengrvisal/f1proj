import Link from "next/link";

export default function Home() {
  return (
    <div className="max-w-4xl mx-auto py-12">
      <h1 className="text-4xl font-bold mb-2">
        <span className="text-accent">F1</span> AI Platform
      </h1>
      <p className="text-muted text-lg mb-10">
        Machine learning insights from 2023–2024 Formula 1 telemetry data
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Link
          href="/dna"
          className="p-6 bg-card rounded-xl border border-border hover:border-accent/50 transition-colors group"
        >
          <div className="text-2xl mb-2">🧬</div>
          <h2 className="text-xl font-semibold mb-1 group-hover:text-accent transition-colors">
            Driver DNA
          </h2>
          <p className="text-muted text-sm">
            Cluster analysis of driving styles using telemetry-derived features.
            See which drivers are most similar.
          </p>
        </Link>

        <Link
          href="/telemetry"
          className="p-6 bg-card rounded-xl border border-border hover:border-accent/50 transition-colors group"
        >
          <div className="text-2xl mb-2">📊</div>
          <h2 className="text-xl font-semibold mb-1 group-hover:text-accent transition-colors">
            Telemetry Explorer
          </h2>
          <p className="text-muted text-sm">
            Visualize speed, throttle, brake, and gear traces. Compare drivers
            lap by lap.
          </p>
        </Link>

        <Link
          href="/tyres"
          className="p-6 bg-card rounded-xl border border-border hover:border-accent/50 transition-colors group"
        >
          <div className="text-2xl mb-2">🔘</div>
          <h2 className="text-xl font-semibold mb-1 group-hover:text-accent transition-colors">
            Tyre Degradation
          </h2>
          <p className="text-muted text-sm">
            Fitted degradation curves, stint timelines, and compound
            comparisons.
          </p>
        </Link>

        <Link
          href="/races"
          className="p-6 bg-card rounded-xl border border-border hover:border-accent/50 transition-colors group"
        >
          <div className="text-2xl mb-2">🏁</div>
          <h2 className="text-xl font-semibold mb-1 group-hover:text-accent transition-colors">
            Races
          </h2>
          <p className="text-muted text-sm">
            Browse the 2023–2024 season calendar and explore available session
            data.
          </p>
        </Link>
      </div>
    </div>
  );
}
