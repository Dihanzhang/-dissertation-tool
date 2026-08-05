"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

/** Private beta links are served as /beta/<token>; the token is the last path segment. */
function tokenFromPath() {
  const segments = window.location.pathname.split("/").filter(Boolean);
  return segments[0] === "beta" && segments.length > 1 ? segments[1] : "";
}

export default function BetaPage() {
  const router = useRouter();
  const [notice, setNotice] = useState("");

  useEffect(() => {
    async function openReview() {
      const token = tokenFromPath();
      if (!token) {
        setNotice("This beta is invite-only. Open the private link you were sent to start reviewing.");
        return;
      }
      // The review page verifies the token, so going straight there keeps this
      // to a single server call and the tester sees the tool sooner.
      localStorage.setItem("beta-access-token", token);
      router.replace("/review");
    }
    void openReview();
  }, [router]);

  return (
    <main className="mx-auto min-h-screen max-w-xl px-6 py-16">
      <Link href="/" className="text-sm font-semibold text-blue-700">← Dissertation Review</Link>
      <h1 className="mt-8 text-3xl font-bold">Private beta access</h1>
      <p className="mt-3 text-slate-600">{notice || "Opening your review…"}</p>
      <p className="mt-10 text-sm text-slate-600">
        Your link is personal. Please do not forward or post it — it can be revoked if it is shared.
      </p>
      <p className="mt-3 text-sm text-slate-600">
        Need help? <a className="underline" href="mailto:dihan.zhang@outlook.com">dihan.zhang@outlook.com</a>
      </p>
    </main>
  );
}
