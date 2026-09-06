"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { getCompanies } from "../lib/workspace";
import { getKnowledgeSources } from "../lib/workspace";
import type { Company, KnowledgeSource } from "../types/workspace";
import { useWorkspace } from "./workspace-provider";

function formatDate(value: string | null) { return value ? new Date(value).toLocaleDateString() : "Not indexed"; }

export function KnowledgeView({ companyId }: { companyId?: string }) {
  const { organization } = useWorkspace();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [selectedCompany, setSelectedCompany] = useState(companyId ?? "");
  const [sources, setSources] = useState<KnowledgeSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { if (!organization || companyId) return; getCompanies(organization.id).then((items) => { setCompanies(items); setSelectedCompany(items[0]?.id ?? ""); }).catch(() => setError("Unable to load companies.")); }, [organization, companyId]);
  useEffect(() => { let active = true; const timer = window.setTimeout(() => { if (!organization || !selectedCompany) { setLoading(false); return; } setLoading(true); getKnowledgeSources(organization.id, selectedCompany).then((items) => { if (active) setSources(items); }).catch((caught) => { if (active) setError(caught instanceof Error ? caught.message : "Unable to load knowledge sources."); }).finally(() => { if (active) setLoading(false); }); }, 0); return () => { active = false; window.clearTimeout(timer); }; }, [organization, selectedCompany]);
  const totals = useMemo(() => sources.reduce((sum, source) => ({ documents: sum.documents + source.documents_count, chunks: sum.chunks + source.chunks_count, embedded: sum.embedded + source.embedded_chunks_count }), { documents: 0, chunks: 0, embedded: 0 }), [sources]);
  const path = selectedCompany ? `/dashboard/companies/${selectedCompany}/knowledge` : "/dashboard/knowledge";
  if (!organization) return <section className="content-section"><div className="page-state">Loading workspace…</div></section>;
  return <section className="content-section"><div className="content-header"><div><div className="eyebrow">Knowledge base</div><h1>Knowledge</h1><p className="content-subtitle">Turn company websites, PDFs and notes into clean, searchable-ready text.</p></div>{selectedCompany && <Link className="primary-button inline-button" href={`${path}/new`}>+ Add source</Link>}</div>{!companyId && companies.length > 1 && <label className="company-picker">Company<select value={selectedCompany} onChange={(event) => setSelectedCompany(event.target.value)}>{companies.map((company) => <option key={company.id} value={company.id}>{company.name}</option>)}</select></label>}{selectedCompany && <div className="knowledge-stats"><div><strong>{sources.length}</strong><span>Sources</span></div><div><strong>{totals.documents}</strong><span>Documents</span></div><div><strong>{totals.chunks}</strong><span>Chunks</span></div><div><strong>{totals.embedded}</strong><span>Embedded</span></div></div>}{error && <p className="form-error" role="alert">{error}</p>}{loading && <div className="page-state">Loading knowledge…</div>}{!loading && !error && !selectedCompany && <div className="empty-state"><strong>Create a company first.</strong><p>Knowledge sources belong to a company workspace.</p><Link className="text-link" href="/dashboard/companies/new">Create company →</Link></div>}{!loading && !error && selectedCompany && sources.length === 0 && <div className="empty-state"><strong>No knowledge sources yet.</strong><p>Add a website, PDF or manual note to start building this company&apos;s knowledge base.</p><Link className="text-link" href={`${path}/new`}>Add the first source →</Link></div>}{!loading && sources.length > 0 && <div className="source-list">{sources.map((source) => <Link className="source-card" href={`${path}/${source.id}`} key={source.id}><div className="source-card-top"><div><span className="source-type">{source.type}</span><h2>{source.name}</h2></div><span className={`source-status source-${source.status}`}>{source.status}</span></div><p>{source.source_url || (source.type === "pdf" ? "Private PDF" : "Manual text")}</p><div className="source-meta"><span>{source.documents_count} documents</span><span>{source.chunks_count} chunks</span><span>{source.embedded_chunks_count}/{source.chunks_count} embedded</span><span>Updated {formatDate(source.last_indexed_at)}</span></div>{source.last_error && <small className="form-error">{source.last_error}</small>}</Link>)}</div>}</section>;
}
