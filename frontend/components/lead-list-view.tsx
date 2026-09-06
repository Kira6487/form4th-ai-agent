"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { getLeads } from "../lib/workspace";
import type { Lead } from "../types/workspace";
import { useWorkspace } from "./workspace-provider";

const statuses = ["", "new", "qualified", "contacted"];

export function LeadListView({ companyId }: { companyId: string }) {
  const { organization } = useWorkspace();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const pageSize = 25;

  useEffect(() => {
    if (!organization) return;
    getLeads(organization.id, companyId, { status: status || undefined, page, page_size: pageSize })
      .then((result) => { setLeads(result.items); setTotal(result.total); })
      .catch((caught) => setError(caught instanceof Error ? caught.message : "Unable to load leads."))
      .finally(() => setLoading(false));
  }, [companyId, organization, page, status]);

  if (!organization || loading) return <section className="content-section"><div className="page-state">Loading leads...</div></section>;
  if (error) return <section className="content-section"><p className="form-error" role="alert">{error}</p></section>;
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  return <section className="content-section">
    <Link className="back-link" href={`/dashboard/companies/${companyId}`}>← Company</Link>
    <div className="content-header"><div><div className="eyebrow">Commercial pipeline</div><h1>Leads</h1><p className="content-subtitle">Commercial interest detected by the private AI Agent.</p></div><span className="source-status source-ready">{total} total</span></div>
    <div className="lead-filters" role="group" aria-label="Lead status filters">{statuses.map((value) => <button className={status === value ? "source-tab active" : "source-tab"} key={value || "all"} type="button" onClick={() => { setStatus(value); setPage(1); }}>{value ? value : "All"}</button>)}</div>
    {leads.length === 0 ? <div className="empty-card"><h2>No leads yet.</h2><p>When the AI Agent detects commercial interest, leads will appear here.</p></div> : <div className="lead-table-wrap"><table className="lead-table"><thead><tr><th>Name</th><th>Intent</th><th>Contact</th><th>Status</th><th>Source</th><th>Created</th></tr></thead><tbody>{leads.map((lead) => <tr key={lead.id}><td><Link href={`/dashboard/companies/${companyId}/leads/${lead.id}`}>{lead.name || "Unnamed lead"}</Link></td><td>{lead.intent.replaceAll("_", " ")}</td><td>{lead.email || lead.phone || "Not provided"}</td><td><span className={`source-status source-${lead.status}`}>{lead.status}</span></td><td>{lead.source === "dashboard_test" ? "Dashboard test" : lead.source}</td><td>{new Date(lead.created_at).toLocaleDateString()}</td></tr>)}</tbody></table></div>}
    {pageCount > 1 && <div className="pagination"><button className="secondary-button" type="button" disabled={page === 1} onClick={() => setPage((current) => current - 1)}>Previous</button><span>Page {page} of {pageCount}</span><button className="secondary-button" type="button" disabled={page >= pageCount} onClick={() => setPage((current) => current + 1)}>Next</button></div>}
  </section>;
}
