"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { CompanyForm } from "../../../../components/company-form";
import { useWorkspace } from "../../../../components/workspace-provider";
import { createCompany } from "../../../../lib/workspace";

export default function NewCompanyPage() {
  const router = useRouter();
  const { organization } = useWorkspace();
  return <section className="content-section narrow-section"><Link className="back-link" href="/dashboard/companies">← Companies</Link><div className="eyebrow">New company</div><h1>Create company</h1><p className="content-subtitle">Store basic company information. Website content processing belongs to the next phase.</p>{organization && <CompanyForm submitLabel="Create company" onSubmit={async (input) => { const company = await createCompany(organization.id, input); router.push(`/dashboard/companies/${company.id}`); }} />}</section>;
}
