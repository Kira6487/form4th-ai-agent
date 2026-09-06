"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { createManualSource, createPdfSource, createWebsiteSource } from "../lib/workspace";
import { useWorkspace } from "./workspace-provider";

type Kind = "website" | "pdf" | "manual";

export function KnowledgeForm({ companyId }: { companyId: string }) {
  const { organization } = useWorkspace();
  const router = useRouter();
  const [kind, setKind] = useState<Kind>("website");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [url, setUrl] = useState("");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!organization) return;
    setBusy(true);
    setError(null);
    try {
      if (kind === "website") await createWebsiteSource(organization.id, companyId, { name, source_url: url, description });
      else if (kind === "manual") await createManualSource(organization.id, companyId, { name, title, content, description });
      else {
        if (!file) throw new Error("Choose a PDF file.");
        await createPdfSource(organization.id, companyId, name, file, description);
      }
      router.push(`/dashboard/companies/${companyId}/knowledge`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to create source.");
    } finally {
      setBusy(false);
    }
  }

  return <section className="content-section narrow-section">
    <Link className="back-link" href={`/dashboard/companies/${companyId}/knowledge`}>← Knowledge</Link>
    <div className="eyebrow">Add source</div><h1>Add knowledge source</h1>
    <p className="content-subtitle">Choose a source and we&apos;ll normalize it into documents and chunks.</p>
    <div className="source-tabs">{(["website", "pdf", "manual"] as Kind[]).map((item) => <button className={kind === item ? "source-tab active" : "source-tab"} type="button" onClick={() => setKind(item)} key={item}>{item === "manual" ? "Manual text" : item.toUpperCase()}</button>)}</div>
    <form className="company-form knowledge-form" onSubmit={(event) => void submit(event)}>
      <label>Source name<input required minLength={2} value={name} onChange={(event) => setName(event.target.value)} placeholder="Company website" /></label>
      <label>Description (optional)<input value={description} onChange={(event) => setDescription(event.target.value)} placeholder="What this source contains" /></label>
      {kind === "website" && <><label>URL<input required type="url" value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://company.com" /></label><p className="form-hint">Only crawl websites you are authorized to process.</p></>}
      {kind === "pdf" && <><label>PDF file<input required type="file" accept="application/pdf,.pdf" onChange={(event) => setFile(event.target.files?.[0] ?? null)} /></label><p className="form-hint">Maximum 20 MB. OCR is not supported in Phase 3.</p></>}
      {kind === "manual" && <><label>Title<input required value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Product overview" /></label><label>Content<textarea required rows={12} value={content} onChange={(event) => setContent(event.target.value)} placeholder="Write the source content here…" /></label></>}
      {error && <p className="form-error" role="alert">{error}</p>}<button className="primary-button" disabled={busy} type="submit">{busy ? "Processing…" : "Create source"}</button>
    </form>
  </section>;
}
