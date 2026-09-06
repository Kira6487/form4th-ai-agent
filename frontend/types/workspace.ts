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
};
export type KnowledgeDocument = { id: string; source_id: string; ingestion_run_id: string | null; title: string; content: string; content_type: string; language: string | null; source_url: string | null; content_hash: string; metadata: Record<string, unknown>; is_active: boolean; created_at: string; updated_at: string };
export type KnowledgeChunk = { id: string; source_id: string; document_id: string; ingestion_run_id: string | null; chunk_index: number; content: string; content_hash: string; approx_token_count: number | null; metadata: Record<string, unknown>; is_active: boolean; created_at: string; updated_at: string };
export type KnowledgePage<T> = { items: T[]; page: number; page_size: number; total: number };
