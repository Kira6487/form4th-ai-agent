"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { getSupabaseBrowserClient } from "../lib/supabase/client";

type AuthMode = "login" | "register" | "forgot";

export function AuthForm({ mode }: { mode: AuthMode }) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const isRegister = mode === "register";
  const isForgot = mode === "forgot";

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    if (isRegister && password !== confirmation) {
      setError("Passwords do not match.");
      return;
    }
    setIsLoading(true);
    try {
      const supabase = getSupabaseBrowserClient();
      if (isForgot) {
        const { error: resetError } = await supabase.auth.resetPasswordForEmail(email, { redirectTo: `${window.location.origin}/login` });
        if (resetError) throw resetError;
        setMessage("If the account exists, a recovery email has been sent.");
      } else if (isRegister) {
        const { data, error: signUpError } = await supabase.auth.signUp({ email, password });
        if (signUpError) throw signUpError;
        if (data.session) router.push("/onboarding");
        else setMessage("Check your email to confirm your account before signing in.");
      } else {
        const { error: signInError } = await supabase.auth.signInWithPassword({ email, password });
        if (signInError) throw signInError;
        router.push("/dashboard");
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to complete the request.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <form className="auth-form" onSubmit={submit}>
      <label htmlFor="email">Email</label>
      <input id="email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
      {!isForgot && <><label htmlFor="password">Password</label><input id="password" type="password" autoComplete={isRegister ? "new-password" : "current-password"} minLength={8} value={password} onChange={(event) => setPassword(event.target.value)} required /></>}
      {isRegister && <><label htmlFor="confirmation">Confirm password</label><input id="confirmation" type="password" autoComplete="new-password" minLength={8} value={confirmation} onChange={(event) => setConfirmation(event.target.value)} required /></>}
      {error && <p className="form-error" role="alert">{error}</p>}
      {message && <p className="form-success" role="status">{message}</p>}
      <button className="primary-button" type="submit" disabled={isLoading}>{isLoading ? "Please wait…" : isForgot ? "Send recovery email" : isRegister ? "Create account" : "Sign in"}</button>
    </form>
  );
}
