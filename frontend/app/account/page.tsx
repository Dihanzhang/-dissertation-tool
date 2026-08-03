"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || "";
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "";

type Access = { can_submit: boolean; status: string; expires_at: string | null };

export default function AccountPage() {
  const [email, setEmail] = useState("");
  const [token, setToken] = useState("");
  const [notice, setNotice] = useState("");
  const [access, setAccess] = useState<Access | null>(null);

  useEffect(() => {
    const accessToken = new URLSearchParams(window.location.hash.slice(1)).get("access_token") || "";
    setToken(accessToken);
    if (accessToken) sessionStorage.setItem("submission-pass-token", accessToken);
    if (accessToken) void loadAccess(accessToken);
  }, []);

  async function loadAccess(activeToken = token) {
    const response = await fetch(`${API_BASE}/api/account/entitlement`, { headers: { Authorization: `Bearer ${activeToken}` } });
    if (response.ok) setAccess(await response.json());
  }

  async function sendSignIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!SUPABASE_URL || !SUPABASE_ANON_KEY) { setNotice("Email sign-in is being configured. Please try again shortly."); return; }
    const response = await fetch(`${SUPABASE_URL}/auth/v1/otp`, {
      method: "POST",
      headers: { apikey: SUPABASE_ANON_KEY, Authorization: `Bearer ${SUPABASE_ANON_KEY}`, "Content-Type": "application/json" },
      body: JSON.stringify({ email, create_user: true, email_redirect_to: `${window.location.origin}/account` }),
    });
    setNotice(response.ok ? "Check your email for your secure sign-in link." : "We could not send the sign-in link. Please try again.");
  }

  async function buyPass() {
    const response = await fetch(`${API_BASE}/api/billing/checkout-session`, { method: "POST", headers: { Authorization: `Bearer ${token}` } });
    if (!response.ok) { setNotice("Please sign in first, then try again."); return; }
    window.location.assign((await response.json()).checkout_url);
  }

  return <main className="mx-auto min-h-screen max-w-xl px-6 py-16">
    <Link href="/" className="text-sm font-semibold text-blue-700">← Dissertation Review</Link>
    <h1 className="mt-8 text-3xl font-bold">Your Submission Pass</h1>
    {!token ? <form className="mt-8 space-y-4 rounded-xl bg-slate-50 p-6" onSubmit={sendSignIn}>
      <p>Enter your email and we’ll send a secure sign-in link.</p>
      <input required type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" className="w-full rounded-md border p-3" />
      <button className="rounded-md bg-blue-700 px-5 py-3 font-semibold text-white">Email me a sign-in link</button>
    </form> : <section className="mt-8 rounded-xl bg-slate-50 p-6">
      {access?.can_submit ? <><p className="font-semibold text-emerald-700">Your Submission Pass is active.</p><p className="mt-2 text-slate-600">Expires {new Date(access.expires_at!).toLocaleDateString()}.</p><Link href="/review" className="mt-5 inline-block rounded-md bg-blue-700 px-5 py-3 font-semibold text-white">Start a review</Link></> : <><p className="font-semibold">No active Submission Pass</p><p className="mt-2 text-slate-600">AU$14.95 for 30 days of unlimited personal rechecks.</p><button onClick={buyPass} className="mt-5 rounded-md bg-blue-700 px-5 py-3 font-semibold text-white">Buy Submission Pass</button></>}
    </section>}
    {notice && <p role="status" className="mt-4 text-slate-700">{notice}</p>}
    <p className="mt-10 text-sm text-slate-600">Need help with your pass? <a className="underline" href="mailto:dihan.zhang@outlook.com">dihan.zhang@outlook.com</a></p>
  </main>;
}
