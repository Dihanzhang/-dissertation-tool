"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || "";
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "";

function tokenFromHash() {
  return new URLSearchParams(window.location.hash.slice(1)).get("access_token") || "";
}

export default function BetaPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [sending, setSending] = useState(false);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    const token = tokenFromHash() || localStorage.getItem("submission-pass-token") || sessionStorage.getItem("submission-pass-token") || "";
    if (!token) return;
    localStorage.setItem("submission-pass-token", token);
    sessionStorage.setItem("submission-pass-token", token);
    localStorage.removeItem("beta-redemption-pending");
    async function redeemInvitation() {
      try {
        const response = await fetch(`${API_BASE}/api/beta/redeem`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!response.ok) {
          setNotice("This email does not have an active beta invitation. Please use the email that received the invitation or contact support.");
          return;
        }
        setNotice("Your 30-day beta Submission Pass is active. Opening your review…");
        router.replace("/review");
      } catch {
        setNotice("We could not confirm beta access. Please try again or contact support.");
      }
    }
    void redeemInvitation();
  }, [router]);

  async function sendSignIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
      setNotice("Email sign-in is being configured. Please try again shortly.");
      return;
    }
    setSending(true);
    setNotice("Sending your private beta sign-in link…");
    localStorage.setItem("beta-redemption-pending", "true");
    try {
      const response = await fetch(`${SUPABASE_URL}/auth/v1/otp`, {
        method: "POST",
        headers: {
          apikey: SUPABASE_ANON_KEY,
          Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email,
          create_user: true,
          email_redirect_to: `${window.location.origin}/beta`,
        }),
      });
      setNotice(response.ok ? "Check your email for your private beta sign-in link." : "We could not send the sign-in link. Please try again.");
      if (!response.ok) localStorage.removeItem("beta-redemption-pending");
    } catch {
      localStorage.removeItem("beta-redemption-pending");
      setNotice("We could not send the sign-in link. Please check your connection and try again.");
    } finally {
      setSending(false);
    }
  }

  return (
    <main className="mx-auto min-h-screen max-w-xl px-6 py-16">
      <Link href="/" className="text-sm font-semibold text-blue-700">← Dissertation Review</Link>
      <h1 className="mt-8 text-3xl font-bold">Private beta access</h1>
      <p className="mt-3 text-slate-600">This beta is for invited members only. Sign in with the exact email address that received your invitation.</p>
      <form className="mt-8 space-y-4 rounded-xl bg-slate-50 p-6 text-slate-900" onSubmit={sendSignIn}>
        <label className="block text-sm font-semibold" htmlFor="beta-email">Invited email address</label>
        <input id="beta-email" required type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.edu" className="w-full rounded-md border p-3" />
        <button disabled={sending} className="button-primary rounded-md px-5 py-3 font-semibold disabled:opacity-60">
          {sending ? "Sending…" : "Email me a beta sign-in link"}
        </button>
      </form>
      {notice && <p role="status" className="mt-4 text-slate-700">{notice}</p>}
      <p className="mt-10 text-sm text-slate-600">Need help? <a className="underline" href="mailto:dihan.zhang@outlook.com">dihan.zhang@outlook.com</a></p>
    </main>
  );
}
