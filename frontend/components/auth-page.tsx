import Link from "next/link";

import { AuthForm } from "./auth-form";

const content = {
  login: { title: "Welcome back", subtitle: "Sign in to your FORM4TH workspace." },
  register: { title: "Create your account", subtitle: "Start building your workspace foundation." },
  forgot: { title: "Reset your password", subtitle: "We’ll send a secure recovery link if the account exists." },
} as const;

export function AuthPage({ mode }: { mode: keyof typeof content }) {
  const copy = content[mode];
  return <main className="auth-shell"><section className="auth-card"><div className="brand-mark">F</div><div className="eyebrow">FORM4TH AI Agent</div><h1>{copy.title}</h1><p className="auth-subtitle">{copy.subtitle}</p><AuthForm mode={mode} /><nav className="auth-links">{mode !== "login" && <Link href="/login">Sign in</Link>}{mode !== "register" && <Link href="/register">Create account</Link>}{mode !== "forgot" && <Link href="/forgot-password">Forgot password?</Link>}</nav></section></main>;
}
