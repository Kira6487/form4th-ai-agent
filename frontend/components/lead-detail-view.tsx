"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import { getLead, updateLead } from "../lib/workspace";
import type { Lead } from "../types/workspace";
import { useWorkspace } from "./workspace-provider";

const statusOptions: Lead["status"][] = ["new", "qualified", "contacted", "converted", "lost"];

export function LeadDetailView({ companyId, leadId }: { companyId: string; leadId: string }) {
  const { organization } = useWorkspace();
  const [lead, setLead] = useState<Lead | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!organization) return;
    getLead(organization.id, companyId, leadId).then(setLead).catch((caught) => setError(caught instanceof Error ? caught.message : "Unable to load lead.")).finally(() => setLoading(false));
  }, [companyId, leadId, organization]);
  if (!organization || loading) return <section className="content-section"><div className="page-state">Loading lead...</div></section>;
  if (!lead) return <section className="content-section"><p className="form-error" role="alert">{error || "Lead not found."}</p></section>;
  const organizationId = organization.id;
  const currentLeadId = lead.id;
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setSaving(true); setError(null);
    const form = new FormData(event.currentTarget);
    try { setLead(await updateLead(organizationId, companyId, currentLeadId, { status: form.get("status") as Lead["status"], name: String(form.get("name") || "") || null, email: String(form.get("email") || "") || null, phone: String(form.get("phone") || "") || null, interest: String(form.get("interest") || "") || null, consent_to_contact: form.get("consent") === "on" })); } catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to save lead."); } finally { setSaving(false); }
  }
  return <section className="content-section narrow-section">
    <Link className="back-link" href={`/dashboard/companies/${companyId}/leads`}>← Leads</Link>
    <div className="content-header"><div><div className="eyebrow">Lead detail</div><h1>{lead.name || "Unnamed lead"}</h1><p className="content-subtitle">{lead.source === "dashboard_test" ? "Dashboard test" : lead.source} · detected {new Date(lead.detected_at).toLocaleString()}</p></div><span className={`source-status source-${lead.status}`}>{lead.status}</span></div>
    {error && <p className="form-error" role="alert">{error}</p>}
    <form className="company-form lead-detail-form" onSubmit={save}><div className="form-grid"><label>Name<input name="name" defaultValue={lead.name || ""} /></label><label>Email<input name="email" type="email" defaultValue={lead.email || ""} /></label><label>Phone<input name="phone" defaultValue={lead.phone || ""} /></label><label>Status<select name="status" defaultValue={lead.status}>{statusOptions.map((value) => <option key={value}>{value}</option>)}</select></label></div><label>Interest<textarea name="interest" rows={4} defaultValue={lead.interest || ""} /></label><label className="checkbox-label"><input name="consent" type="checkbox" defaultChecked={lead.consent_to_contact} /> Consent to contact</label><div className="detail-actions"><button className="primary-button" disabled={saving}>{saving ? "Saving..." : "Save lead"}</button><Link className="secondary-button" href={`/dashboard/companies/${companyId}/agent?conversation=${lead.conversation_id}`}>View conversation</Link></div></form>
    <div className="lead-facts"><div><strong>Intent</strong><span>{lead.intent.replaceAll("_", " ")}</span></div><div><strong>Confidence</strong><span>{Math.round(lead.confidence * 100)}%</span></div><div><strong>Qualified</strong><span>{lead.qualified_at ? new Date(lead.qualified_at).toLocaleString() : "Not yet"}</span></div></div>
  </section>;
}
