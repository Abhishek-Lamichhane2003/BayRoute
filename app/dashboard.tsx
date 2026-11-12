"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { loadDashboard, requestPrediction } from "./api";
import { TransitMap } from "./transit-map";
import type { DashboardPayload, Prediction } from "./types";

function formatDelay(seconds: number) {
  const minutes = Math.abs(seconds) / 60;
  if (seconds < -30) return `${minutes.toFixed(1)}m early`;
  if (seconds <= 30) return "On time";
  return `+${minutes.toFixed(1)}m`;
}

function formatStatus(value: string) {
  return value.replaceAll("_", " ");
}

export function Dashboard() {
  const [data, setData] = useState<DashboardPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedRoute, setSelectedRoute] = useState("22");
  const [selectedStop, setSelectedStop] = useState("DIRIDON");
  const [currentDelay, setCurrentDelay] = useState(180);
  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [predicting, setPredicting] = useState(false);

  useEffect(() => {
    loadDashboard().then(setData).catch(() => setError("Network snapshot unavailable."));
  }, []);

  const route = useMemo(
    () => data?.routes.find((item) => item.id === selectedRoute),
    [data, selectedRoute],
  );

  async function submitPrediction(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPredicting(true);
    try {
      const response = await requestPrediction({
        route_id: selectedRoute,
        stop_id: selectedStop,
        prediction_time: new Date().toISOString(),
        current_delay_seconds: currentDelay,
        previous_stop_delay_seconds: Math.max(0, currentDelay - 45),
        headway_minutes: selectedRoute === "522" ? 12 : 15,
      });
      setPrediction(response);
    } finally {
      setPredicting(false);
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="BayRoute home">
          <span className="brand-mark" aria-hidden="true"><i /><i /><i /></span>
          <span>BayRoute</span>
        </a>
        <nav aria-label="Dashboard sections">
          <a href="#network">Network</a>
          <a href="#reliability">Reliability</a>
          <a href="#predict">Predict</a>
        </nav>
        <div className="live-pill">
          <span aria-hidden="true" /> {data?.overview.data_mode === "live" ? "Live feed" : "Demo feed"}
        </div>
      </header>

      <section className="hero" id="top">
        <div>
          <p className="eyebrow">South Bay transit intelligence</p>
          <h1>Know the delay<br />before the platform does.</h1>
          <p className="hero-copy">
            BayRoute turns raw transit updates into route-level reliability and practical
            arrival forecasts for riders and operations teams.
          </p>
        </div>
        <div className="hero-meta">
          <span>Last network pulse</span>
          <strong>{data ? new Date(data.overview.last_updated).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "Loading"}</strong>
          <small>San José, California</small>
        </div>
      </section>

      {error ? <div className="error-banner" role="alert">{error}</div> : null}

      <section className="metric-grid" aria-label="Network summary">
        <article>
          <span>Routes monitored</span>
          <strong>{data?.overview.active_routes ?? "—"}</strong>
          <small>{data?.overview.tracked_vehicles ?? "—"} vehicles in snapshot</small>
        </article>
        <article>
          <span>On-time arrivals</span>
          <strong>{data ? `${data.overview.on_time_percent}%` : "—"}</strong>
          <small>Within five minutes</small>
        </article>
        <article>
          <span>Average delay</span>
          <strong>{data ? formatDelay(data.overview.average_delay_seconds) : "—"}</strong>
          <small>Across monitored routes</small>
        </article>
        <article className="metric-highlight">
          <span>Model MAE</span>
          <strong>{data ? `${Math.round(data.metrics.mae_seconds)}s` : "—"}</strong>
          <small>{data ? `${data.metrics.improvement_percent}% better than baseline` : "Temporal holdout"}</small>
        </article>
      </section>

      <section className="network-grid" id="network">
        <article className="map-panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Live network</p>
              <h2>Vehicles across San José</h2>
            </div>
            <span className="timestamp">Updated from latest snapshot</span>
          </div>
          {data ? <TransitMap vehicles={data.vehicles} /> : <div className="map-loading">Loading vehicle positions…</div>}
          <div className="route-legend" aria-label="Route legend">
            {data?.routes.map((item) => (
              <span key={item.id}><i style={{ background: item.color }} />{item.short_name}</span>
            ))}
          </div>
        </article>

        <aside className="pulse-panel">
          <div className="section-heading compact">
            <div>
              <p className="eyebrow">Operations pulse</p>
              <h2>What needs attention</h2>
            </div>
          </div>
          <div className="alert-list">
            {data?.overview.alerts.map((alert) => (
              <article key={alert.title}>
                <span className={`alert-dot ${alert.severity}`} aria-hidden="true" />
                <div><strong>{alert.title}</strong><p>{alert.detail}</p></div>
              </article>
            )) ?? <p>Reading network conditions…</p>}
          </div>
          <div className="vehicle-list">
            <span className="list-label">Latest vehicles</span>
            {data?.vehicles.slice(0, 4).map((vehicle) => (
              <div key={vehicle.vehicle_id}>
                <b style={{ borderColor: vehicle.route_color }}>{vehicle.route_name}</b>
                <span>{vehicle.stop_name}</span>
                <strong>{formatDelay(vehicle.delay_seconds)}</strong>
              </div>
            ))}
          </div>
        </aside>
      </section>

      <section className="reliability-section" id="reliability">
        <div className="section-heading">
          <div>
            <p className="eyebrow">28-day view</p>
            <h2>Reliability by route</h2>
          </div>
          <p className="section-note">Score = share of arrivals within five minutes of schedule.</p>
        </div>
        <div className="reliability-list">
          {data?.reliability.map((item, index) => (
            <article key={item.route_id}>
              <span className="rank">0{index + 1}</span>
              <div className="route-name">
                <i style={{ background: item.color }} />
                <div><strong>Route {item.route_name}</strong><small>{item.samples.toLocaleString()} observations</small></div>
              </div>
              <div className="score-track" aria-label={`${item.reliability_score}% reliable`}>
                <i style={{ width: `${item.reliability_score}%`, background: item.color }} />
              </div>
              <strong className="score">{item.reliability_score}%</strong>
              <span className="delay">{formatDelay(item.average_delay_seconds)}</span>
            </article>
          )) ?? <p>Calculating reliability…</p>}
        </div>
      </section>

      <section className="predict-section" id="predict">
        <div className="predict-copy">
          <p className="eyebrow">Delay lab</p>
          <h2>Test the forecast.</h2>
          <p>
            Choose a route and stop, then adjust the vehicle’s current delay. The model uses
            recent operations, temporal patterns, and route context to estimate arrival delay.
          </p>
          <div className="model-note">
            <span>Model</span><strong>{data?.metrics.model_version ?? "bayroute-hgbt-v1"}</strong>
            <span>Holdout</span><strong>Chronological 80 / 20</strong>
          </div>
        </div>
        <form className="predict-card" onSubmit={submitPrediction}>
          <div className="form-row">
            <label>Route
              <select value={selectedRoute} onChange={(event) => setSelectedRoute(event.target.value)}>
                {data?.routes.map((item) => <option key={item.id} value={item.id}>{item.short_name} · {item.long_name}</option>)}
              </select>
            </label>
            <label>Stop
              <select value={selectedStop} onChange={(event) => setSelectedStop(event.target.value)}>
                {data?.stops.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
              </select>
            </label>
          </div>
          <label className="range-label">
            <span>Current delay <strong>{Math.round(currentDelay / 60)} min</strong></span>
            <input type="range" min="0" max="900" step="30" value={currentDelay} onChange={(event) => setCurrentDelay(Number(event.target.value))} />
          </label>
          <button type="submit" disabled={predicting || !data}>
            {predicting ? "Forecasting…" : "Run delay forecast"}<span aria-hidden="true">↗</span>
          </button>
          <div className={`prediction-result ${prediction ? "visible" : ""}`} aria-live="polite">
            {prediction ? (
              <>
                <div><span>Predicted arrival delay</span><strong>{formatDelay(prediction.predicted_delay_seconds)}</strong></div>
                <div><span>90% error band</span><strong>{Math.round(prediction.interval_low_seconds / 60)} to {Math.round(prediction.interval_high_seconds / 60)} min</strong></div>
                <span className={`status-chip ${prediction.status}`}>{formatStatus(prediction.status)}</span>
              </>
            ) : (
              <p>Select the current conditions to generate a forecast for route {route?.short_name ?? "22"}.</p>
            )}
          </div>
        </form>
      </section>

      <footer>
        <div className="brand"><span className="brand-mark" aria-hidden="true"><i /><i /><i /></span><span>BayRoute</span></div>
        <p>Built for transparent, measurable transit reliability.</p>
        <a href="https://511.org/open-data/transit" target="_blank" rel="noreferrer">Data documentation ↗</a>
      </footer>
    </main>
  );
}

