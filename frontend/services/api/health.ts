import { apiFetch } from "./client";
import type { AIHealthResponse, BackendHealthResponse, DatabaseHealthResponse } from "../../types/health";

export function getBackendHealth(): Promise<BackendHealthResponse> {
  return apiFetch<BackendHealthResponse>("/health");
}

export function getDatabaseHealth(): Promise<DatabaseHealthResponse> {
  return apiFetch<DatabaseHealthResponse>("/api/v1/health/db");
}

export function getAIHealth(): Promise<AIHealthResponse> {
  return apiFetch<AIHealthResponse>("/api/v1/health/ai");
}
