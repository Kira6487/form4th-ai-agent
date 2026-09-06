"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { CompanyForm } from "./company-form";
import { useWorkspace } from "./workspace-provider";
import { getCompany, updateCompany } from "../lib/workspace";
import type { Company, CompanyInput } from "../types/workspace";

export function CompanyDetail({ companyId }: { companyId: string }) {
  const { organization } = useWorkspace();
  const [company, setCompany] = useState<Company | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!organization) return;
    let active = true;
    getCompany(organization.id, companyId).then((result) => { if (active) setCompany(result); }).catch((caught) => { if (active) setError(caught instanceof Error ? caught.message : "Unable to load company."); });
    return () => { active = false; };
  }, [companyId, organization]);
  if (error) return <section className="content-section"><p className="form-error" role="alert">{error}</p></section>;
  if (!company || !organization) return <section className="content-section"><div className="page-state">Loading company…</div></section>;
  const initial: CompanyInput = { name: company.name, legal_name: company.legal_name, website: company.website, description: company.description, industry: company.industry, country: company.country, timezone: company.timezone };
  return <section className="content-section narrow-section"><Link className="back-link" href="/dashboard/companies">← Companies</Link><div className="content-header"><div><div className="eyebrow">Company overview</div><h1>{company.name}</h1><p className="content-subtitle">Status: {company.status}</p></div></div><CompanyForm initial={initial} submitLabel="Save changes" onSubmit={async (input) => { const updated = await updateCompany(organization.id, company.id, input); setCompany(updated); }} /><div className="coming-soon-panel"><strong>Future modules</strong><p>Knowledge, AI Agent and Integrations will be available in later phases.</p></div></section>;
}
