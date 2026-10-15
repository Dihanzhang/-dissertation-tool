"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect } from "react";
import FeedbackForm from "./feedback-form";

export default function LandingPage() {
  useEffect(() => {
    if (window.location.hash.includes("access_token=")) {
      window.location.replace(`/account${window.location.hash}`);
    }
  }, []);

  return (
    <main className="min-h-screen bg-white text-slate-900">
      <section className="mx-auto max-w-4xl px-6 pb-8 pt-12 text-center">
        <p className="mb-3 text-sm font-semibold uppercase tracking-[0.18em] text-blue-700">APA 7 Review Tool</p>
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">A careful review before you submit.</h1>
        <p className="mx-auto mt-4 max-w-2xl leading-7 text-slate-600">
          If you’re writing an essay, research paper or dissertation, check APA 7 alignment, citations, references and writing rules through deterministic, rule-based checks, then decide what to change.
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
            Need help? Contact <a className="underline" href="mailto:dihan.zhang@outlook.com">dihan.zhang@outlook.com</a>
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
          {["APA 7 and reference-list checks", "Citation–reference matching", "Annotated DOCX download", "Deterministic, rule-based findings", "Unlimited personal rechecks for 30 days", "Prior results remain visible after expiry"].map((item) => <li key={item}>✓ {item}</li>)}
        </ul>
        <p className="mt-8 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">This tool supports your own writing. It does not guarantee APA compliance or grades, and it does not replace your supervisor or university requirements.</p>
      </section>

      <section id="feedback" className="bg-slate-900 py-16 text-white">
        <div className="mx-auto max-w-xl px-6">
          <h2 className="text-2xl font-bold">Share your feedback</h2>
          <p className="mt-2 text-slate-300">Your feedback helps improve the tool. Name and contact details are optional.</p>
          <div className="mt-6"><FeedbackForm /></div>
        </div>
      </section>
    </main>
  );
}
