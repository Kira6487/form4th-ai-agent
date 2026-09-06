"use client";

import { useWorkspace } from "../../../components/workspace-provider";

export default function SettingsPage() {
  const { organization } = useWorkspace();
  return <section className="content-section narrow-section"><div className="eyebrow">Settings</div><h1>Workspace settings</h1><div className="settings-card"><span>Organization</span><strong>{organization?.name}</strong><span>Your role</span><strong>Member access is managed by the backend.</strong></div></section>;
}
