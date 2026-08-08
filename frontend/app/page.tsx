"use client";

import Image from "next/image";
import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function LandingPage() {
  const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");

  useEffect(() => {
    if (window.location.hash.includes("access_token=")) {
      window.location.replace(`/account${window.location.hash}`);
    }
  }, []);

  async function sendFeedback(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus("sending");
    const form = new FormData(event.currentTarget);
    try {
      const response = await fetch(`${API_BASE}/api/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(Object.fromEntries(form)),
      });
      if (!response.ok) throw new Error("Could not send feedback");
      event.currentTarget.reset();
      setStatus("sent");
    } catch {
      setStatus("error");
    }
  }

  return (
    <main className="min-h-screen bg-white text-slate-900">
      <section className="mx-auto max-w-4xl px-6 pb-8 pt-12 text-center">
        <p className="mb-3 text-sm font-semibold uppercase tracking-[0.18em] text-blue-700">APA 7 dissertation review</p>
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">A careful final review before you submit.</h1>
        <p className="mx-auto mt-4 max-w-2xl leading-7 text-slate-600">
          Check APA 7 alignment, citations and references, then review clarity while you remain in control of every change.
        </p>
        <div className="mt-6 flex flex-col justify-center gap-3 sm:flex-row">
          <Link href="/account" className="button-primary rounded-lg px-6 py-3 font-semibold">Get Submission Pass — AU$14.95</Link>
          <a href="#how-it-works" className="button-secondary rounded-lg px-6 py-3 font-semibold">How it works</a>
        </div>
        <p className="mt-3 text-sm text-slate-500">One payment · 30 days of unlimited personal rechecks</p>
      </section>

      {/* Kept to a single compact strip so the sample below stays visible without scrolling. */}
      <section id="how-it-works" className="border-y border-slate-200 bg-slate-50 py-4">
        <div className="mx-auto flex max-w-4xl flex-col gap-x-6 gap-y-2 px-6 text-sm sm:flex-row sm:items-center sm:justify-between">
          <ol className="flex flex-col gap-x-6 gap-y-1 sm:flex-row">
            {["Sign in with your email", "Buy one Submission Pass", "Recheck as you revise"].map((item, index) => (
              <li key={item} className="flex items-center gap-2 text-slate-700">
                <span className="font-semibold text-blue-700">0{index + 1}</span>
                <span className="font-medium">{item}</span>
              </li>
            ))}
          </ol>
          <p className="text-slate-600">
            Need help? <a className="underline" href="mailto:dihan.zhang@outlook.com">dihan.zhang@outlook.com</a>
          </p>
        </div>
      </section>

      <section className="mx-auto max-w-5xl px-6 pb-14 pt-8">
        <div className="grid gap-8 md:grid-cols-[0.9fr_1.3fr] md:items-center">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-blue-700">What you get back</p>
            <h2 className="mt-2 text-2xl font-bold">Comments beside the highlighted text</h2>
            <p className="mt-3 leading-7 text-slate-600">
              You download your own Word document, unchanged in format, with colour-coded highlights and a
              comment beside each sentence or phrase that needs attention.
            </p>
            <p className="mt-4 leading-7 text-slate-600">
              Every comment names the APA rule, how serious it is, and what to do — so you decide what to change.
            </p>
          </div>
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-slate-50 shadow-sm">
            <Image
              src="/review-output-sample.png"
              alt="A reviewed Word document with highlighted text and APA review comments in the margin"
              width={1143}
              height={813}
              unoptimized
              priority
              className="h-auto w-full"
            />
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-4xl px-6 pb-16">
        <h2 className="text-2xl font-bold">What your pass includes</h2>
        <ul className="mt-6 grid gap-3 text-slate-700 sm:grid-cols-2">
          {["APA 7 and reference-list checks", "Citation–reference matching", "Annotated DOCX download", "AI-assisted clarity review", "Unlimited personal rechecks for 30 days", "Prior results remain visible after expiry"].map((item) => <li key={item}>✓ {item}</li>)}
        </ul>
        <p className="mt-8 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">This tool supports your own writing. It does not guarantee APA compliance or grades, and it does not replace your supervisor or university requirements.</p>
      </section>

      <section id="feedback" className="bg-slate-900 py-16 text-white">
        <div className="mx-auto max-w-xl px-6">
          <h2 className="text-2xl font-bold">Share your experience</h2>
          <p className="mt-2 text-slate-300">Your feedback helps improve the tool. Name and contact details are optional.</p>
          <form className="mt-6 space-y-4" onSubmit={sendFeedback}>
            {/* bg-white is required: a browser in dark mode gives unstyled fields a
                dark background, which made these invisible against this section. */}
            <input name="name" aria-label="Name" placeholder="Name (optional)" className="w-full rounded-md border border-slate-300 bg-white p-3 text-slate-900 placeholder:text-slate-500" />
            <input name="contact" aria-label="Contact" placeholder="Email or contact (optional)" className="w-full rounded-md border border-slate-300 bg-white p-3 text-slate-900 placeholder:text-slate-500" />
            <input name="website" tabIndex={-1} autoComplete="off" className="hidden" aria-hidden="true" />
            <textarea name="message" required minLength={10} maxLength={2000} aria-label="Feedback message" placeholder="Tell me what worked, what did not, or what you need." className="min-h-32 w-full rounded-md border border-slate-300 bg-white p-3 text-slate-900 placeholder:text-slate-500" />
            <button disabled={status === "sending"} className="button-interaction rounded-md bg-white px-5 py-3 font-semibold text-slate-900 hover:bg-slate-100 disabled:opacity-60">{status === "sending" ? "Sending…" : "Send feedback"}</button>
            {status === "sent" && <p role="status" className="text-emerald-300">Thank you — your message has been received.</p>}
            {status === "error" && <p role="alert" className="text-rose-300">Your message could not be sent. Please try again or email dihan.zhang@outlook.com.</p>}
          </form>
        </div>
      </section>
    </main>
  );
}
