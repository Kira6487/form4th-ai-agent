"use client";

import Link from "next/link";
import { ReactNode } from "react";

import { useWorkspace } from "./workspace-provider";

const futureModules = ["AI Agent", "Conversations", "Leads", "Analytics", "Integrations"];

export function DashboardShell({ children }: { children: ReactNode }) {
  const { organizations, organization, selectOrganization, signOut } = useWorkspace();
  return <div className="app-layout"><aside className="sidebar"><div className="sidebar-brand"><span className="brand-mark">F</span><span>FORM4TH</span></div><div className="workspace-switcher"><label htmlFor="workspace">Workspace</label><select id="workspace" value={organization?.id ?? ""} onChange={(event) => selectOrganization(event.target.value)}>{organizations.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select></div><nav className="side-nav"><Link className="nav-active" href="/dashboard">Overview</Link><Link href="/dashboard/companies">Companies</Link><Link href="/dashboard/knowledge">Knowledge</Link>{futureModules.map((module) => <span className="nav-disabled" key={module}>{module}<small>Coming soon</small></span>)}</nav><div className="sidebar-footer"><Link href="/dashboard/settings">Settings</Link><button type="button" onClick={() => void signOut()}>Sign out</button></div></aside><main className="app-content">{children}</main></div>;
}
