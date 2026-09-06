"use client";

import Link from "next/link";

import { useWorkspace } from "../../components/workspace-provider";

export default function DashboardPage() {
  const { organization } = useWorkspace();
  return <section className="content-section"><div className="content-header"><div><div className="eyebrow">Overview</div><h1>{organization?.name ?? "Workspace"}</h1><p className="content-subtitle">Your secure FORM4TH workspace is ready for its first company.</p></div></div><div className="overview-grid"><article className="overview-card"><span className="card-kicker">Workspace status</span><strong>Active</strong><p>Authentication and organization membership are enforced by the backend.</p></article><article className="overview-card"><span className="card-kicker">Next step</span><strong>Add a company</strong><p>Create the first company profile without starting ingestion or AI automation yet.</p><Link className="text-link" href="/dashboard/companies/new">Create company →</Link></article></div></section>;
}
