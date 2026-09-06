"use client";

import Link from "next/link";
import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";

import { createAgent, createConversation, getAgents, streamChatMessage, updateAgent } from "../lib/workspace";
import type { AIAgent, ChatMessage, ChatSource } from "../types/workspace";
import { useWorkspace } from "./workspace-provider";

type Draft = Omit<AIAgent, "id" | "organization_id" | "company_id" | "created_at" | "updated_at">;
const emptyDraft: Draft = { name: "", role: "", description: null, objective: "", tone: "Professional and friendly", language: "Spanish", system_instructions: "", model: "", status: "draft", temperature: 0.2, max_output_tokens: null };

export function AgentView({ companyId }: { companyId: string }) {
  const { organization } = useWorkspace();
  const [agent, setAgent] = useState<AIAgent | null>(null);
  const [draft, setDraft] = useState<Draft>(emptyDraft);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [sending, setSending] = useState(false);
  const [leadStatus, setLeadStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!organization) return;
    getAgents(organization.id, companyId)
      .then((items) => { const first = items[0] ?? null; setAgent(first); setDraft(first ? { ...first } : emptyDraft); })
      .catch((caught) => setError(caught instanceof Error ? caught.message : "Unable to load agents."))
      .finally(() => setLoading(false));
  }, [organization, companyId]);
  useEffect(() => { scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" }); }, [messages, sending]);
  function setField<K extends keyof Draft>(field: K, value: Draft[K]) { setDraft((current) => ({ ...current, [field]: value })); }
  async function save(event: FormEvent) { event.preventDefault(); if (!organization) return; setSaving(true); setError(null); try { const result = agent ? await updateAgent(organization.id, companyId, agent.id, draft) : await createAgent(organization.id, companyId, draft); setAgent(result); setDraft({ ...result }); } catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to save agent."); } finally { setSaving(false); } }
  async function send() {
    if (!organization || !agent || !input.trim() || sending || agent.status === "disabled") return;
    const text = input.trim(); setInput(""); setSending(true); setError(null);
    try {
      const id = conversationId ?? (await createConversation(organization.id, companyId, agent.id)).id;
      setConversationId(id);
      setMessages((current) => [...current, { id: `local-${Date.now()}`, conversation_id: id, role: "user", content: text, retrieved_chunk_ids: null, sources: null, provider: null, model: null, latency_ms: null, input_tokens: null, output_tokens: null, status: "completed", created_at: new Date().toISOString() }]);
      const assistantId = `stream-${Date.now()}`;
      setMessages((current) => [...current, { id: assistantId, conversation_id: id, role: "assistant", content: "", retrieved_chunk_ids: null, sources: null, provider: "gemini", model: null, latency_ms: null, input_tokens: null, output_tokens: null, status: "completed", created_at: new Date().toISOString() }]);
      await streamChatMessage(organization.id, companyId, id, text, (part) => setMessages((current) => current.map((message) => message.id === assistantId ? { ...message, content: message.content + part } : message)), (sources, model, lead) => { setLeadStatus(lead?.status ?? null); setMessages((current) => current.map((message) => message.id === assistantId ? { ...message, sources, retrieved_chunk_ids: sources.map((source) => source.chunk_id), model } : message)); });
    } catch (caught) { setInput(text); setError(caught instanceof Error ? caught.message : "Unable to send message."); } finally { setSending(false); }
  }
  function handleKey(event: KeyboardEvent<HTMLTextAreaElement>) { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); void send(); } }
  if (!organization) return <section className="content-section"><div className="page-state">Loading workspace…</div></section>;
  if (loading) return <section className="content-section"><div className="page-state">Loading agent…</div></section>;
  return (
    <section className="content-section">
      <Link className="back-link" href={`/dashboard/companies/${companyId}`}>← Company</Link>
      <div className="content-header"><div><div className="eyebrow">AI Agent</div><h1>{agent?.name || "Configure an agent"}</h1><p className="content-subtitle">Configure a private business agent and test its grounded answers before later publication.</p></div>{agent && <span className={`source-status source-${agent.status === "active" ? "ready" : agent.status}`}>{agent.status}</span>}</div>
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="agent-layout">
        <form className="company-form agent-form" onSubmit={(event) => void save(event)}>
          <h2>Agent configuration</h2>
          <label>Name *<input required minLength={2} value={draft.name} onChange={(event) => setField("name", event.target.value)} /></label>
          <label>Role *<input required minLength={2} value={draft.role} onChange={(event) => setField("role", event.target.value)} /></label>
          <label>Objective *<textarea required minLength={2} rows={3} value={draft.objective} onChange={(event) => setField("objective", event.target.value)} /></label>
          <div className="form-grid"><label>Tone<input value={draft.tone} onChange={(event) => setField("tone", event.target.value)} /></label><label>Language<input value={draft.language} onChange={(event) => setField("language", event.target.value)} /></label><label>Model<input value={draft.model} onChange={(event) => setField("model", event.target.value)} /></label></div>
          <label>Instructions *<textarea required minLength={1} rows={7} value={draft.system_instructions} onChange={(event) => setField("system_instructions", event.target.value)} placeholder="Rules specific to this agent…" /></label>
          <div className="form-grid"><label>Status<select value={draft.status} onChange={(event) => setField("status", event.target.value as Draft["status"])}><option value="draft">Draft</option><option value="active">Active</option><option value="disabled">Disabled</option></select></label><label>Temperature<input type="number" min="0" max="1" step="0.05" value={draft.temperature ?? 0.2} onChange={(event) => setField("temperature", Number(event.target.value))} /></label></div>
          <button className="primary-button" disabled={saving}>{saving ? "Saving…" : "Save agent"}</button>
        </form>
        <div className="chat-panel">
          <div className="chat-panel-heading"><div><h2>Test your agent</h2><p className="content-subtitle">Answers use this company&apos;s authorized knowledge and show their sources.</p></div><div>{conversationId && <small>Conversation active</small>}{leadStatus && <small className="lead-signal">Lead detected · {leadStatus}</small>}</div></div>
          <div className="chat-messages" ref={scrollRef}>
            {messages.length === 0 && <div className="chat-empty">Ask a question to test the configured agent.</div>}
            {messages.map((message) => <article className={`chat-message chat-${message.role}`} key={message.id}><div className="chat-message-meta"><strong>{message.role === "user" ? "You" : agent?.name ?? "Agent"}</strong><time>{new Date(message.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</time></div><p>{message.content}</p>{message.sources?.length ? <div className="source-chips"><span>Sources</span>{message.sources.map((source: ChatSource) => <span className="source-chip" key={source.chunk_id}>{source.title}</span>)}</div> : null}</article>)}
            {sending && <div className="chat-typing">Agent is thinking…</div>}
          </div>
          <div className="chat-composer"><textarea value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={handleKey} placeholder={agent ? "Ask something…" : "Save an agent first"} disabled={!agent || sending || agent.status === "disabled"} rows={3} /><div><small>Enter to send · Shift+Enter for a new line</small><button className="primary-button" disabled={!agent || sending || !input.trim() || agent.status === "disabled"} onClick={() => void send()}>Send</button></div></div>
        </div>
      </div>
    </section>
  );
}
