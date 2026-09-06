"use client";

import { useCallback, useEffect, useState } from "react";

import { getAIHealth, getBackendHealth, getDatabaseHealth } from "../services/api/health";
import type { HealthStatus } from "../types/health";

type StatusKey = "frontend" | "backend" | "database" | "gemini";
type StatusMap = Record<StatusKey, HealthStatus>;

const initialStatuses: StatusMap = {
  frontend: { state: "online", message: "The Next.js application is running." },
  backend: { state: "loading", message: "Checking the FastAPI service…" },
  database: { state: "loading", message: "Checking the configured PostgreSQL connection…" },
  gemini: { state: "loading", message: "Running a minimal Gemini smoke check…" },
};

const labels: Record<StatusKey, string> = {
  frontend: "Frontend",
  backend: "Backend API",
  database: "Database",
  gemini: "Gemini",
};

function statusLabel(state: HealthStatus["state"]): string {
  if (state === "loading") return "Checking";
  if (state === "error") return "Unavailable";
  return state === "online" ? "Online" : "Connected";
}

export function StatusDashboard() {
  const [statuses, setStatuses] = useState<StatusMap>(initialStatuses);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const refresh = useCallback(async () => {
    setIsRefreshing(true);
    setStatuses((current) => ({
      ...current,
      backend: { state: "loading", message: "Checking the FastAPI service…" },
      database: { state: "loading", message: "Checking the configured PostgreSQL connection…" },
      gemini: { state: "loading", message: "Running a minimal Gemini smoke check…" },
    }));

    const [backendResult, databaseResult, geminiResult] = await Promise.allSettled([
      getBackendHealth(),
      getDatabaseHealth(),
      getAIHealth(),
    ]);
    setStatuses((current) => ({
      ...current,
      backend: backendResult.status === "fulfilled"
        ? { state: "online", message: "FastAPI is responding to health requests." }
        : { state: "error", message: backendResult.reason instanceof Error ? backendResult.reason.message : "Backend is unavailable." },
      database: databaseResult.status === "fulfilled"
        ? { state: "connected", message: "PostgreSQL responded successfully to SELECT 1." }
        : { state: "error", message: databaseResult.reason instanceof Error ? databaseResult.reason.message : "Database is unavailable." },
      gemini: geminiResult.status === "fulfilled"
        ? { state: "connected", message: `Gemini is responding with ${geminiResult.value.model}.` }
        : { state: "error", message: geminiResult.reason instanceof Error ? geminiResult.reason.message : "Gemini is unavailable." },
    }));
    setIsRefreshing(false);
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">F</div>
          <div><div className="brand-name">FORM4TH</div><div className="brand-subtitle">AI Agent infrastructure</div></div>
        </div>
        <div className="environment">Foundation · Development</div>
      </header>
      <main className="main">
        <div className="eyebrow">System overview</div>
        <h1>AI Infrastructure Status</h1>
        <p className="intro">A single view of the services that power the FORM4TH platform. Dependencies are checked from the backend at load time.</p>
        <div className="toolbar">
          <span className="toolbar-label">Last check runs on page load or on demand.</span>
          <button className="refresh" type="button" onClick={() => void refresh()} disabled={isRefreshing}>
            {isRefreshing ? "Checking…" : "Refresh status"}
          </button>
        </div>
        <section className="status-grid" aria-label="Infrastructure service status">
          {(Object.keys(labels) as StatusKey[]).map((key) => {
            const service = statuses[key];
            return <article className="status-card" key={key}>
              <div className="status-card-header"><h2>{labels[key]}</h2><span className={`status-pill status-${service.state}`}>{statusLabel(service.state)}</span></div>
              <p>{service.message}</p>
            </article>;
          })}
        </section>
        <p className="footnote">Gemini checks are manual/on-load only to avoid unnecessary provider calls.</p>
      </main>
    </div>
  );
}
