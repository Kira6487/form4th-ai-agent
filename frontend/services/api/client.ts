import { getSupabaseBrowserClient } from "../../lib/supabase/client";

const apiBaseUrl = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let accessToken: string | undefined;
  try {
    const { data } = await getSupabaseBrowserClient().auth.getSession();
    accessToken = data.session?.access_token;
  } catch {
    // Public foundation endpoints remain usable without Supabase configuration.
  }

  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...init?.headers,
    },
    cache: "no-store",
  });

  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // Keep the generic status message when the API does not return JSON.
    }
    throw new Error(detail);
  }

  return (await response.json()) as T;
}
