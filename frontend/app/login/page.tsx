"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useState, type FormEvent } from "react";

import { LogoMark } from "@/components/logo";
import { api, asApiError } from "@/lib/api";
import type { LoginResponse } from "@/lib/types";

const DEMO_ACCOUNTS = [
  { email: "member@northwind.test", label: "Member" },
  { email: "reviewer@northwind.test", label: "Reviewer" },
  { email: "member@globex.test", label: "Other tenant" },
];
const DEMO_PASSWORD = "demo-password";

function SignInForm() {
  const next = useSearchParams().get("next");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api<LoginResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      // Only follow same-site paths so ?next= can't redirect off the app. A full load (not
      // router.replace) discards routes Next.js keeps alive in the background, which would
      // otherwise come back holding the signed-out state.
      window.location.assign(next?.startsWith("/") && !next.startsWith("//") ? next : "/vendors");
    } catch (err) {
      setError(asApiError(err).message);
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} noValidate>
      {error && (
        <p role="alert" className="alert alert-error">
          {error}
        </p>
      )}
      <div className="field">
        <label htmlFor="email">Email</label>
        <input
          id="email"
          className="input"
          type="email"
          autoComplete="username"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
      </div>
      <div className="field">
        <label htmlFor="password">Password</label>
        <input
          id="password"
          className="input"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </div>
      <button type="submit" className="btn btn-primary" disabled={busy}>
        {busy ? "Signing in…" : "Sign in"}
      </button>
      <div className="demo-accounts">
        <p>Demo accounts use the password {DEMO_PASSWORD}.</p>
        <div>
          {DEMO_ACCOUNTS.map((account) => (
            <button
              key={account.email}
              type="button"
              className="btn"
              onClick={() => {
                setEmail(account.email);
                setPassword(DEMO_PASSWORD);
              }}
            >
              Fill in {account.label.toLowerCase()}
            </button>
          ))}
        </div>
      </div>
    </form>
  );
}

export default function SignInPage() {
  return (
    <main className="signin">
      <div className="signin-card panel">
        <LogoMark size={36} />
        <div>
          <h1>Sign in to Vendor Intake</h1>
          <p className="panel-meta">Collect vendor paperwork and get it approved.</p>
        </div>
        <Suspense>
          <SignInForm />
        </Suspense>
      </div>
    </main>
  );
}
