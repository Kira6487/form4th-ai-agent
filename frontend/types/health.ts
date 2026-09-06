export type ServiceState = "loading" | "connected" | "online" | "error";

export type HealthStatus = {
  state: ServiceState;
  message: string;
};

export type DatabaseHealthResponse = {
  status: string;
  database: string;
};

export type BackendHealthResponse = {
  status: string;
  service: string;
};

export type AIHealthResponse = {
  status: string;
  provider: string;
  model: string;
};
