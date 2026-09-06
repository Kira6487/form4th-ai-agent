import { apiFetch } from "../services/api/client";
import { getSupabaseBrowserClient } from "./supabase/client";
import type { AIAgent, ChatMessage, ChatSource, Company, CompanyInput, CompanyUpdate, Conversation, KnowledgeChunk, KnowledgeDocument, KnowledgePage, KnowledgeSearchResult, KnowledgeSource, Organization } from "../types/workspace";

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
const agentPath = (o: string, c: string) => `/api/v1/organizations/${o}/companies/${c}/agents`;
export const getAgents = (o: string, c: string) => apiFetch<AIAgent[]>(agentPath(o, c));
export const createAgent = (o: string, c: string, input: Omit<AIAgent, "id" | "organization_id" | "company_id" | "created_at" | "updated_at">) => apiFetch<AIAgent>(agentPath(o, c), { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input) });
export const updateAgent = (o: string, c: string, a: string, input: Partial<Omit<AIAgent, "id" | "organization_id" | "company_id" | "created_at" | "updated_at">>) => apiFetch<AIAgent>(`${agentPath(o, c)}/${a}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input) });
const conversationPath = (o: string, c: string, a: string) => `${agentPath(o, c)}/${a}/conversations`;
export const createConversation = (o: string, c: string, a: string) => apiFetch<Conversation>(conversationPath(o, c, a), { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ channel: "dashboard" }) });
export const getConversationMessages = (o: string, c: string, conversationId: string) => apiFetch<ChatMessage[]>(`/api/v1/organizations/${o}/companies/${c}/conversations/${conversationId}/messages`);
export const sendChatMessage = (o: string, c: string, conversationId: string, message: string) => apiFetch<{ conversation_id: string; message_id: string; answer: string; sources: ChatSource[]; model: string | null }>(`/api/v1/organizations/${o}/companies/${c}/conversations/${conversationId}/messages`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message }) });
export async function streamChatMessage(o: string, c: string, conversationId: string, message: string, onText: (text: string) => void, onDone: (sources: ChatSource[], model: string | null) => void): Promise<void> {
  const { data } = await getSupabaseBrowserClient().auth.getSession();
  const response = await fetch(`${(process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "")}/api/v1/organizations/${o}/companies/${c}/conversations/${conversationId}/messages/stream`, { method: "POST", headers: { Accept: "text/event-stream", "Content-Type": "application/json", ...(data.session?.access_token ? { Authorization: `Bearer ${data.session.access_token}` } : {}) }, body: JSON.stringify({ message }), cache: "no-store" });
  if (!response.ok || !response.body) throw new Error(`Request failed (${response.status})`);
  const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = "";
  while (true) { const { value, done } = await reader.read(); buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done }); const events = buffer.split("\n\n"); buffer = events.pop() ?? ""; for (const event of events) { const lines = event.split("\n"); const type = lines.find((line) => line.startsWith("event: "))?.slice(7) ?? ""; const raw = lines.find((line) => line.startsWith("data: "))?.slice(6); if (!raw) continue; const body = JSON.parse(raw) as { text?: string; sources?: ChatSource[]; model?: string | null; detail?: string }; if (type === "text" && body.text) onText(body.text); else if (type === "done") onDone(body.sources ?? [], body.model ?? null); else if (type === "error") throw new Error(body.detail ?? "Streaming failed"); } if (done) break; }
}
