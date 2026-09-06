"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useWorkspace } from "../../../components/workspace-provider";
import { getCompanies } from "../../../lib/workspace";
import type { Company } from "../../../types/workspace";

export default function CompaniesPage() {
  const { organization } = useWorkspace();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!organization) return;
    let active = true;
    const timeoutId = window.setTimeout(() => {
      setIsLoading(true);
      setError(null);
      getCompanies(organization.id)
        .then((result) => { if (active) setCompanies(result); })
        .catch((caught) => { if (active) setError(caught instanceof Error ? caught.message : "Unable to load companies."); })
        .finally(() => { if (active) setIsLoading(false); });
    }, 0);
    return () => { active = false; window.clearTimeout(timeoutId); };
  }, [organization]);
  return <section className="content-section"><div className="content-header"><div><div className="eyebrow">Workspace</div><h1>Companies</h1><p className="content-subtitle">Manage the businesses connected to this organization.</p></div><Link className="primary-button inline-button" href="/dashboard/companies/new">+ New company</Link></div>{isLoading && <div className="page-state">Loading companies…</div>}{error && <p className="form-error" role="alert">{error}</p>}{!isLoading && !error && companies.length === 0 && <div className="empty-state"><strong>No companies yet.</strong><p>Create your first company to begin.</p><Link className="text-link" href="/dashboard/companies/new">Create your first company →</Link></div>}{!isLoading && companies.length > 0 && <div className="company-list">{companies.map((company) => <Link className="company-row" href={`/dashboard/companies/${company.id}`} key={company.id}><div><strong>{company.name}</strong><span>{company.industry || "Industry not set"}</span></div><div><span>{company.website || "No website"}</span><small>{company.status}</small></div></Link>)}</div>}</section>;
}
