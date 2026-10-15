"use client";

import { FormEvent, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function FeedbackForm({ context = "" }: { context?: string }) {
  const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");

  async function sendFeedback(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const values = Object.fromEntries(new FormData(formElement));
    const message = String(values.message).trim();
    setStatus("sending");
    try {
      const response = await fetch(`${API_BASE}/api/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...values, message: context ? `${message}\n\n${context}` : message }),
      });
      if (!response.ok) throw new Error("Could not send feedback");
      formElement.reset();
      setStatus("sent");
    } catch {
      setStatus("error");
    }
  }

  return (
    <form className="space-y-4 rounded-lg border border-slate-200 bg-white p-4 text-left text-slate-900" onSubmit={sendFeedback}>
      <p className="text-sm text-slate-600">Tell us what worked, what was confusing, or which finding needs checking. Name and contact details are optional.</p>
      {context && <p className="text-xs text-slate-500">The review version and counts will be included with your feedback.</p>}
      <input name="name" aria-label="Name" placeholder="Name (optional)" maxLength={120} className="w-full rounded-md border border-slate-300 bg-white p-3 text-slate-900 placeholder:text-slate-500" />
      <input name="contact" aria-label="Contact" placeholder="Email or contact (optional)" maxLength={254} className="w-full rounded-md border border-slate-300 bg-white p-3 text-slate-900 placeholder:text-slate-500" />
      <input name="website" tabIndex={-1} autoComplete="off" className="hidden" aria-hidden="true" />
      <textarea name="message" required minLength={10} maxLength={2000 - (context ? context.length + 2 : 0)} aria-label="Feedback message" placeholder="Share your feedback here." className="min-h-32 w-full rounded-md border border-slate-300 bg-white p-3 text-slate-900 placeholder:text-slate-500" />
      <button disabled={status === "sending"} className="button-primary rounded-md px-5 py-3 font-semibold disabled:opacity-60">{status === "sending" ? "Sending…" : "Share your feedback"}</button>
      {status === "sent" && <p role="status" className="text-sm text-emerald-700">Thank you — your message has been received.</p>}
      {status === "error" && <p role="alert" className="text-sm text-red-700">Your message could not be sent. Please try again or email dihan.zhang@outlook.com.</p>}
    </form>
  );
}
