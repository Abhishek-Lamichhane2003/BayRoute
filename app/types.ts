export type Route = {
  id: string;
  short_name: string;
  long_name: string;
  color: string;
};

export type Stop = {
  id: string;
  code: string | null;
  name: string;
  latitude: number;
  longitude: number;
};

export type LiveVehicle = {
  vehicle_id: string;
  route_id: string;
  route_name: string;
  route_color: string;
  stop_id: string;
  stop_name: string;
  latitude: number;
  longitude: number;
  delay_seconds: number;
  captured_at: string;
};

export type ReliabilityPoint = {
  route_id: string;
  route_name: string;
  color: string;
  samples: number;
  average_delay_seconds: number;
  on_time_percent: number;
  reliability_score: number;
};

export type ModelMetrics = {
  trained_records: number;
  test_records: number;
  mae_seconds: number;
  baseline_mae_seconds: number;
  improvement_percent: number;
  within_two_minutes_percent: number;
  residual_p90_seconds: number;
  trained_at: string;
  model_version: string;
};

export type Overview = {
  active_routes: number;
  tracked_vehicles: number;
  average_delay_seconds: number;
  on_time_percent: number;
  data_mode: "demo" | "live";
  last_updated: string;
  alerts: Array<{ severity: string; title: string; detail: string }>;
};

export type DashboardPayload = {
  overview: Overview;
  routes: Route[];
  stops: Stop[];
  vehicles: LiveVehicle[];
  reliability: ReliabilityPoint[];
  metrics: ModelMetrics;
};

export type Prediction = {
  predicted_delay_seconds: number;
  predicted_delay_minutes: number;
  status: string;
  interval_low_seconds: number;
  interval_high_seconds: number;
  model_version: string;
};

