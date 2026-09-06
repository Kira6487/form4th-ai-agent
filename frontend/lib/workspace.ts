import { apiFetch } from "../services/api/client";
import type { Company, CompanyInput, CompanyUpdate, KnowledgeChunk, KnowledgeDocument, KnowledgePage, KnowledgeSearchResult, KnowledgeSource, Organization } from "../types/workspace";

export function getOrganizations(): Promise<Organization[]> {
  return apiFetch<Organization[]>("/api/v1/organizations");
}

export function createOrganization(name: string): Promise<Organization> {
  return apiFetch<Organization>("/api/v1/organizations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
}

export function getCompanies(organizationId: string): Promise<Company[]> {
  return apiFetch<Company[]>(`/api/v1/organizations/${organizationId}/companies`);
}

export function getCompany(organizationId: string, companyId: string): Promise<Company> {
  return apiFetch<Company>(`/api/v1/organizations/${organizationId}/companies/${companyId}`);
}

export function createCompany(organizationId: string, input: CompanyInput): Promise<Company> {
  return apiFetch<Company>(`/api/v1/organizations/${organizationId}/companies`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export function updateCompany(organizationId: string, companyId: string, input: CompanyUpdate): Promise<Company> {
  return apiFetch<Company>(`/api/v1/organizations/${organizationId}/companies/${companyId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

const knowledgePath = (organizationId: string, companyId: string) => `/api/v1/organizations/${organizationId}/companies/${companyId}/knowledge`;
export const getKnowledgeSources = (o: string, c: string) => apiFetch<KnowledgeSource[]>(`${knowledgePath(o, c)}/sources`);
export const getKnowledgeSource = (o: string, c: string, s: string) => apiFetch<KnowledgeSource>(`${knowledgePath(o, c)}/sources/${s}`);
export const createManualSource = (o: string, c: string, input: { name: string; title: string; content: string; description?: string }) => apiFetch<KnowledgeSource>(`${knowledgePath(o, c)}/sources/manual`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input) });
export const createWebsiteSource = (o: string, c: string, input: { name: string; source_url: string; description?: string }) => apiFetch<KnowledgeSource>(`${knowledgePath(o, c)}/sources/website`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input) });
export function createPdfSource(o: string, c: string, name: string, file: File, description?: string) { const form = new FormData(); form.append("name", name); if (description) form.append("description", description); form.append("file", file); return apiFetch<KnowledgeSource>(`${knowledgePath(o, c)}/sources/pdf`, { method: "POST", body: form }); }
export const reindexKnowledgeSource = (o: string, c: string, s: string) => apiFetch<KnowledgeSource>(`${knowledgePath(o, c)}/sources/${s}/reindex`, { method: "POST" });
export const disableKnowledgeSource = (o: string, c: string, s: string) => apiFetch<KnowledgeSource>(`${knowledgePath(o, c)}/sources/${s}/disable`, { method: "POST" });
export const getKnowledgeDocuments = (o: string, c: string, s: string) => apiFetch<KnowledgePage<KnowledgeDocument>>(`${knowledgePath(o, c)}/sources/${s}/documents`);
export const getKnowledgeChunks = (o: string, c: string, d: string) => apiFetch<KnowledgePage<KnowledgeChunk>>(`${knowledgePath(o, c)}/documents/${d}/chunks`);
export const getKnowledgeStatus = (o: string, c: string, s: string) => apiFetch<{ source: KnowledgeSource }>(`${knowledgePath(o, c)}/sources/${s}/status`);
export const indexKnowledgeEmbeddings = (o: string, c: string, sourceId?: string, limit?: number) => apiFetch<{ total: number; processed: number; embedded: number; pending: number; failed: number }>(`${knowledgePath(o, c)}/embeddings/index`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ source_id: sourceId, limit }) });
export const reindexKnowledgeEmbeddings = (o: string, c: string, s: string, force = false) => apiFetch<{ total: number; processed: number; embedded: number; pending: number; failed: number }>(`${knowledgePath(o, c)}/sources/${s}/embeddings/reindex`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ force }) });
export const searchKnowledge = (o: string, c: string, query: string, top_k = 5) => apiFetch<{ query: string; results: KnowledgeSearchResult[] }>(`${knowledgePath(o, c)}/search`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query, top_k }) });
