import type { DashboardPayload, Prediction } from "./types";

const apiBase = (process.env.NEXT_PUBLIC_BAYROUTE_API_URL ?? "").replace(/\/$/, "");

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, init);
  if (!response.ok) {
    throw new Error(`Request failed with ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function loadDashboard(): Promise<DashboardPayload> {
  if (!apiBase) {
    const response = await fetch("/demo.json");
    if (!response.ok) throw new Error("Demo data could not be loaded");
    return (await response.json()) as DashboardPayload;
  }

  try {
    const [overview, routes, stops, vehicles, reliability, metrics] = await Promise.all([
      fetchJson<DashboardPayload["overview"]>("/api/overview"),
      fetchJson<DashboardPayload["routes"]>("/api/routes"),
      fetchJson<DashboardPayload["stops"]>("/api/stops"),
      fetchJson<DashboardPayload["vehicles"]>("/api/live"),
      fetchJson<DashboardPayload["reliability"]>("/api/reliability"),
      fetchJson<DashboardPayload["metrics"]>("/api/model/metrics"),
    ]);
    return { overview, routes, stops, vehicles, reliability, metrics };
  } catch (error) {
    console.warn("API unavailable; using the bundled demo snapshot.", error);
    const response = await fetch("/demo.json");
    return (await response.json()) as DashboardPayload;
  }
}

export async function requestPrediction(input: {
  route_id: string;
  stop_id: string;
  prediction_time: string;
  current_delay_seconds: number;
  previous_stop_delay_seconds: number;
  headway_minutes: number;
}): Promise<Prediction> {
  if (apiBase) {
    return fetchJson<Prediction>("/api/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    });
  }

  const date = new Date(input.prediction_time);
  const hour = date.getHours();
  const peakPenalty = (hour >= 7 && hour < 10) || (hour >= 16 && hour < 19) ? 105 : 15;
  const routePenalty = input.route_id === "22" ? 70 : input.route_id === "66" ? 40 : 5;
  const predicted = Math.round(
    input.current_delay_seconds * 0.58 +
      input.previous_stop_delay_seconds * 0.22 +
      peakPenalty +
      routePenalty,
  );
  return {
    predicted_delay_seconds: predicted,
    predicted_delay_minutes: Math.round((predicted / 60) * 10) / 10,
    status: predicted <= 120 ? "on_time" : predicted <= 300 ? "minor_delay" : "major_delay",
    interval_low_seconds: predicted - 128,
    interval_high_seconds: predicted + 128,
    model_version: "bayroute-hgbt-v1-demo",
  };
}

