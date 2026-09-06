"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { createOrganization } from "../../lib/workspace";

export default function OnboardingPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSaving(true);
    try {
      await createOrganization(name);
      router.replace("/dashboard");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to create workspace.");
    } finally {
      setIsSaving(false);
    }
  }
  return <main className="auth-shell"><section className="auth-card"><div className="brand-mark">F</div><div className="eyebrow">Workspace setup</div><h1>Create your workspace</h1><p className="auth-subtitle">Your organization is the secure boundary for companies and future AI modules.</p><form className="auth-form" onSubmit={submit}><label htmlFor="organization-name">Organization name</label><input id="organization-name" value={name} onChange={(event) => setName(event.target.value)} minLength={2} required />{error && <p className="form-error" role="alert">{error}</p>}<button className="primary-button" type="submit" disabled={isSaving}>{isSaving ? "Creating…" : "Create workspace"}</button></form></section></main>;
}
