"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** Private beta links are served as /beta/<token>; the token is the last path segment. */
function tokenFromPath() {
  const segments = window.location.pathname.split("/").filter(Boolean);
  return segments[0] === "beta" && segments.length > 1 ? segments[1] : "";
}

export default function BetaPage() {
  const router = useRouter();
  const [notice, setNotice] = useState("");

  useEffect(() => {
    async function openBeta() {
      const token = tokenFromPath();
      if (!token) {
        setNotice("This beta is invite-only. Open the private link you were sent to start reviewing.");
        return;
      }
      try {
        const response = await fetch(`${API_BASE}/api/beta/access`, { headers: { "X-Beta-Access": token } });
        if (!response.ok) {
          setNotice("This private beta link is not valid or has expired. Please ask for a new link.");
          return;
        }
        localStorage.setItem("beta-access-token", token);
        router.replace("/review");
      } catch {
        setNotice("We could not confirm your beta access. Please check your connection and try again.");
      }
    }
    void openBeta();
  }, [router]);

  return (
    <main className="mx-auto min-h-screen max-w-xl px-6 py-16">
      <Link href="/" className="text-sm font-semibold text-blue-700">← Dissertation Review</Link>
      <h1 className="mt-8 text-3xl font-bold">Private beta access</h1>
      <p className="mt-3 text-slate-600">
        {notice || "Opening your review…"}
      </p>
      <p className="mt-10 text-sm text-slate-600">
        Your link is personal. Please do not forward or post it — it can be revoked if it is shared.
      </p>
      <p className="mt-3 text-sm text-slate-600">
        Need help? <a className="underline" href="mailto:dihan.zhang@outlook.com">dihan.zhang@outlook.com</a>
      </p>
    </main>
  );
}
