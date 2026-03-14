const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchApi<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
  return res.json();
}

// Types
export interface Driver {
  id: number;
  code: string;
  first_name: string;
  last_name: string;
  nationality: string;
  permanent_number: number | null;
  team_name: string | null;
  cluster_id: number | null;
  cluster_label: string | null;
}

export interface PcaInfo {
  pc1_variance: number;
  pc2_variance: number;
  pc1_features: string[];
  pc2_features: string[];
}

export interface ClusterDriver {
  driver_id: number;
  code: string;
  first_name: string;
  last_name: string;
  team: string;
  cluster_id: number;
  cluster_label: string;
  pca_x: number;
  pca_y: number;
  tsne_x: number;
  tsne_y: number;
  features: Record<string, number>;
}

export interface ClustersResponse {
  drivers: ClusterDriver[];
  pca_info: PcaInfo | null;
}

export interface SimilarityMatrix {
  drivers: string[];
  matrix: Record<string, Record<string, number>>;
}

export interface DriverComparison {
  drivers: { driver_id: number; code: string; features: Record<string, number> }[];
  similarity: number | null;
}

export interface DriverDnaProfile {
  features: Record<string, number>;
  cluster_id: number;
  cluster_label: string;
  pca_x: number;
  pca_y: number;
  tsne_x: number;
  tsne_y: number;
  most_similar: { id: number; code: string; similarity: number }[];
  least_similar: { id: number; code: string; similarity: number }[];
}

export interface TelemetrySample {
  distance_m: number;
  speed: number;
  throttle: number;
  brake: boolean;
  gear: number;
  rpm: number | null;
  drs: number | null;
  x: number | null;
  y: number | null;
}

export interface DegCurve {
  driver_id: number;
  code: string;
  stint_number: number;
  compound: string;
  model_type: string;
  coefficients: number[];
  r_squared: number;
  deg_rate_ms_per_lap: number;
  predicted_cliff_lap: number | null;
  num_laps: number;
  actual_laps: { lap: number; time_ms: number; tyre_life: number }[];
}

export interface StrategyDriver {
  driver_id: number;
  code: string;
  stints: {
    stint_number: number;
    compound: string;
    start_lap: number;
    end_lap: number;
    tyre_age_at_start: number | null;
    deg_rate_ms_per_lap: number | null;
    model_type: string | null;
  }[];
}

export interface Race {
  id: number;
  round: number;
  name: string;
  date: string | null;
  circuit: string;
  circuit_id: number;
  country: string;
  sessions: { id: number; type: string; date: string | null }[];
}

export interface Corner {
  corner_number: number;
  entry_distance_m: number;
  apex_distance_m: number;
  exit_distance_m: number;
  entry_speed_median: number;
  apex_speed_median: number;
  exit_speed_median: number;
  corner_type: string;
}

export interface DriverAIAnalysis {
  confidence: number;
  confidenceVerdict: string;
  style: string;
  strengths: string;
  areas: string;
  verdict: string;
}

// API functions
export const api = {
  drivers: (season?: number) =>
    fetchApi<Driver[]>(`/api/drivers${season ? `?season=${season}` : ""}`),

  dnaClusters: (season: number) =>
    fetchApi<ClustersResponse>(`/api/dna/clusters?season=${season}`),

  dnaSimilarity: (season: number) =>
    fetchApi<SimilarityMatrix>(`/api/dna/similarity?season=${season}`),

  dnaCompare: (driverA: number, driverB: number, season: number) =>
    fetchApi<DriverComparison>(
      `/api/dna/compare?driver_a=${driverA}&driver_b=${driverB}&season=${season}`
    ),

  dnaDriver: (id: number, season: number) =>
    fetchApi<DriverDnaProfile>(`/api/dna/driver/${id}?season=${season}`),

  telemetryDrivers: (sessionId: number) =>
    fetchApi<{ id: number; code: string; first_name: string; last_name: string }[]>(
      `/api/telemetry/drivers?session_id=${sessionId}`
    ),

  telemetryLap: (sessionId: number, driverId: number, lap: number) =>
    fetchApi<{ samples: TelemetrySample[] }>(
      `/api/telemetry/lap?session_id=${sessionId}&driver_id=${driverId}&lap=${lap}`
    ),

  telemetryCompare: (sessionId: number, driverA: number, driverB: number) =>
    fetchApi<{
      driver_a: { driver_id: number; lap: number; trace: TelemetrySample[] };
      driver_b: { driver_id: number; lap: number; trace: TelemetrySample[] };
      error?: string;
    }>(`/api/telemetry/compare?session_id=${sessionId}&driver_a=${driverA}&driver_b=${driverB}`),

  tyreDegCurves: (sessionId: number, driverId?: number) =>
    fetchApi<DegCurve[]>(
      `/api/tyres/deg-curves?session_id=${sessionId}${driverId ? `&driver_id=${driverId}` : ""}`
    ),

  tyreStrategy: (sessionId: number) =>
    fetchApi<StrategyDriver[]>(`/api/tyres/strategy-summary?session_id=${sessionId}`),

  circuitCorners: (circuitId: number) =>
    fetchApi<{ corners: Corner[] }>(`/api/circuits/${circuitId}/corners`),

  races: (season: number) => fetchApi<Race[]>(`/api/races?season=${season}`),

  aiAnalyseDriver: async (driverId: number, season: number): Promise<DriverAIAnalysis> => {
    const res = await fetch(`${API_BASE}/api/ai/analyse-driver?driver_id=${driverId}&season=${season}`, {
      method: "POST",
    });
    if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
    return res.json();
  },
};
