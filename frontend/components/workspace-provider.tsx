"use client";

import { createContext, ReactNode, useContext, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { getOrganizations } from "../lib/workspace";
import { getSupabaseBrowserClient } from "../lib/supabase/client";
import type { Organization } from "../types/workspace";

type WorkspaceValue = {
  organizations: Organization[];
  organization: Organization | null;
  selectOrganization: (id: string) => void;
  signOut: () => Promise<void>;
};

const WorkspaceContext = createContext<WorkspaceValue | undefined>(undefined);

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const supabase = getSupabaseBrowserClient();
        const { data } = await supabase.auth.getSession();
        if (!data.session) { router.replace("/login"); return; }
        const result = await getOrganizations();
        if (!active) return;
        setOrganizations(result);
        if (result.length === 0) router.replace("/onboarding");
        else setSelectedId(localStorage.getItem("form4th.organization") ?? result[0].id);
      } catch (caught) {
        if (active) setError(caught instanceof Error ? caught.message : "Unable to load workspace.");
      } finally {
        if (active) setIsLoading(false);
      }
    }
    void load();
    return () => { active = false; };
  }, [router]);

  const organization = useMemo(() => organizations.find((item) => item.id === selectedId) ?? organizations[0] ?? null, [organizations, selectedId]);
  function selectOrganization(id: string) { setSelectedId(id); localStorage.setItem("form4th.organization", id); }
  async function signOut() { await getSupabaseBrowserClient().auth.signOut(); router.replace("/login"); }

  if (isLoading) return <main className="page-state"><p>Loading workspace…</p></main>;
  if (error) return <main className="page-state"><p className="form-error">{error}</p></main>;

  return <WorkspaceContext.Provider value={{ organizations, organization, selectOrganization, signOut }}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace(): WorkspaceValue {
  const context = useContext(WorkspaceContext);
  if (!context) throw new Error("useWorkspace must be used inside WorkspaceProvider");
  return context;
}
