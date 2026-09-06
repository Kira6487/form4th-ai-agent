"use client";

import { FormEvent, useState } from "react";
import type { CompanyInput } from "../types/workspace";

type Props = { initial?: Partial<CompanyInput>; submitLabel: string; onSubmit: (input: CompanyInput) => Promise<void> };

export function CompanyForm({ initial, submitLabel, onSubmit }: Props) {
  const [form, setForm] = useState<CompanyInput>({ name: initial?.name ?? "", legal_name: initial?.legal_name ?? null, website: initial?.website ?? null, description: initial?.description ?? null, industry: initial?.industry ?? null, country: initial?.country ?? null, timezone: initial?.timezone ?? null });
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  function update(field: keyof CompanyInput, value: string) { setForm((current) => ({ ...current, [field]: value || null })); }
  async function submit(event: FormEvent) { event.preventDefault(); setError(null); setIsSaving(true); try { await onSubmit(form); } catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to save company."); } finally { setIsSaving(false); } }
  return <form className="company-form" onSubmit={submit}><label>Company name *<input value={form.name} onChange={(event) => update("name", event.target.value)} minLength={2} required /></label><label>Legal name<input value={form.legal_name ?? ""} onChange={(event) => update("legal_name", event.target.value)} /></label><label>Website<input type="url" placeholder="https://example.com" value={form.website ?? ""} onChange={(event) => update("website", event.target.value)} /></label><div className="form-grid"><label>Industry<input value={form.industry ?? ""} onChange={(event) => update("industry", event.target.value)} /></label><label>Country<input value={form.country ?? ""} onChange={(event) => update("country", event.target.value)} /></label><label>Timezone<input placeholder="America/Lima" value={form.timezone ?? ""} onChange={(event) => update("timezone", event.target.value)} /></label></div><label>Description<textarea rows={5} value={form.description ?? ""} onChange={(event) => update("description", event.target.value)} /></label>{error && <p className="form-error" role="alert">{error}</p>}<button className="primary-button" type="submit" disabled={isSaving}>{isSaving ? "Saving…" : submitLabel}</button></form>;
}
