export type Organization = {
  id: string;
  name: string;
  slug: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export type Company = {
  id: string;
  organization_id: string;
  name: string;
  legal_name: string | null;
  website: string | null;
  description: string | null;
  industry: string | null;
  country: string | null;
  timezone: string | null;
  status: "active" | "inactive" | "archived";
  created_at: string;
  updated_at: string;
};

export type CompanyInput = Omit<Company, "id" | "organization_id" | "status" | "created_at" | "updated_at">;
export type CompanyUpdate = Partial<CompanyInput> & { status?: Company["status"] };

export type KnowledgeSource = {
  id: string; organization_id: string; company_id: string;
  type: "website" | "manual" | "pdf"; name: string; description: string | null; source_url: string | null; storage_path: string | null;
  status: "pending" | "processing" | "ready" | "failed" | "disabled"; last_error: string | null;
  last_indexed_at: string | null; created_by: string | null; created_at: string; updated_at: string;
  documents_count: number; chunks_count: number;
  embedded_chunks_count: number; pending_embeddings_count: number; failed_embeddings_count: number;
};
export type KnowledgeDocument = { id: string; source_id: string; ingestion_run_id: string | null; title: string; content: string; content_type: string; language: string | null; source_url: string | null; content_hash: string; metadata: Record<string, unknown>; is_active: boolean; created_at: string; updated_at: string };
export type KnowledgeChunk = { id: string; source_id: string; document_id: string; ingestion_run_id: string | null; chunk_index: number; content: string; content_hash: string; approx_token_count: number | null; metadata: Record<string, unknown>; is_active: boolean; embedding_model: string | null; embedding_dimensions: number | null; embedded_at: string | null; embedding_status: "pending" | "processing" | "ready" | "failed"; embedding_error: string | null; created_at: string; updated_at: string };
export type KnowledgeSearchResult = { chunk_id: string; document_id: string; source_id: string; title: string; content: string; similarity: number; source_url: string | null; metadata: Record<string, unknown> };
export type AIAgent = { id: string; organization_id: string; company_id: string; name: string; role: string; description: string | null; objective: string; tone: string; language: string; system_instructions: string; model: string; status: "draft" | "active" | "disabled"; temperature: number | null; max_output_tokens: number | null; created_at: string; updated_at: string };
export type Conversation = { id: string; organization_id: string; company_id: string; agent_id: string; created_by: string | null; channel: string; status: "active" | "closed"; started_at: string; last_message_at: string | null; created_at: string; updated_at: string };
export type ChatSource = { title: string; url: string | null; chunk_id: string; source_id: string; document_id: string };
export type ChatMessage = { id: string; conversation_id: string; role: "user" | "assistant" | "system" | "tool"; content: string; retrieved_chunk_ids: string[] | null; sources: ChatSource[] | null; provider: string | null; model: string | null; latency_ms: number | null; input_tokens: number | null; output_tokens: number | null; status: "completed" | "failed"; created_at: string };
export type Lead = { id: string; organization_id: string; company_id: string; agent_id: string | null; conversation_id: string; name: string | null; email: string | null; phone: string | null; interest: string | null; intent: "general_inquiry" | "purchase_interest" | "request_quote" | "request_demo" | "contact_request" | "appointment_interest" | "other_commercial"; confidence: number; status: "new" | "qualified" | "contacted" | "converted" | "lost"; source: "dashboard_test" | "widget" | "whatsapp" | "email" | "api"; consent_to_contact: boolean; detected_at: string; qualified_at: string | null; last_user_message_id: string | null; metadata: Record<string, unknown> | null; created_at: string; updated_at: string };
export type KnowledgePage<T> = { items: T[]; page: number; page_size: number; total: number };
