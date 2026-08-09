"use client";

import Image from "next/image";
import Link from "next/link";
import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const BETA_VERSION = process.env.NEXT_PUBLIC_BETA_VERSION || "Beta v0.1";
const FEEDBACK_EMAIL = process.env.NEXT_PUBLIC_FEEDBACK_EMAIL || "";

function betaToken(): string {
  return typeof window === "undefined" ? "" : localStorage.getItem("beta-access-token") || "";
}

function authHeaders(): Record<string, string> {
  const beta = betaToken();
  if (beta) return { "X-Beta-Access": beta };
  const token = typeof window === "undefined" ? "" : localStorage.getItem("submission-pass-token") || sessionStorage.getItem("submission-pass-token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Finding {
  rule_id: string;
  severity: "error" | "warning" | "suggestion" | "info";
  paragraph_index: number;
  message: string;
  suggested_fix: string;
  autofixable: boolean;
  excerpt: string;
  location_hint: string;
}

interface CheckResponse {
  apa_findings: Finding[];
  missing_references: Array<CitationIssue>;
  uncited_references: Array<CitationIssue>;
  year_mismatches: Array<CitationIssue>;
  spelling_mismatches: Array<CitationIssue>;
  co_author_only_matches: Array<CitationIssue>;
  scope_warning: string;
  stats: { paragraphs_checked: number; apa_findings_count: number; citations_found: number; references_parsed: number };
}

interface CitationIssue {
  citation?: string;
  reference?: string;
  paragraph_index?: number;
  line_index?: number;
  page_number?: number;
  paragraph_number_on_page?: number;
  location_hint?: string;
  message: string;
  severity?: string;
  distance?: number;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Split pasted text into body + references on a "References" heading. */
function splitOnReferences(text: string): { body: string; refs: string } {
  const refHeading = /^references?\s*$/im;
  const lines = text.split("\n");
  const idx = lines.findIndex((l) => refHeading.test(l.trim()));
  if (idx === -1) return { body: text, refs: "" };
  return {
    body: lines.slice(0, idx).join("\n").trim(),
    refs: lines.slice(idx + 1).join("\n").trim(),
  };
}

function wordCount(text: string) {
  return text.trim().split(/\s+/).filter(Boolean).length;
}

const RULE_LABELS: Record<string, string> = {
  PRF001: "Short paragraph",
  REF010: "Publisher business designation",
  STY001: "Passive voice",
  MEC023: "First-line paragraph indent",
};

function ruleLabel(f: Finding) {
  if (RULE_LABELS[f.rule_id]) return RULE_LABELS[f.rule_id];
  const withoutApa = f.message.replace(/^APA\s+§[\d.]+:\s*/, "");
  const firstClause = withoutApa.split(/[.:(-]/)[0]?.trim();
  return firstClause || f.rule_id;
}

function citationIssueOrder(issue: CitationIssue) {
  return [
    issue.page_number ?? Number.MAX_SAFE_INTEGER,
    issue.paragraph_number_on_page ?? Number.MAX_SAFE_INTEGER,
    issue.paragraph_index ?? Number.MAX_SAFE_INTEGER,
    issue.line_index ?? Number.MAX_SAFE_INTEGER,
  ];
}

function compareCitationIssues(a: CitationIssue, b: CitationIssue) {
  const ao = citationIssueOrder(a);
  const bo = citationIssueOrder(b);
  for (let i = 0; i < ao.length; i += 1) {
    if (ao[i] !== bo[i]) return ao[i] - bo[i];
  }
  return a.message.localeCompare(b.message);
}

function buildFeedbackTemplate({
  mode,
  fileName,
  checkResult,
}: {
  mode: "paste" | "upload";
  fileName: string;
  checkResult: CheckResponse | null;
}) {
  const stats = checkResult
    ? [
        `APA findings: ${checkResult.apa_findings.length}`,
        `Citation issues: ${
          checkResult.missing_references.length +
          checkResult.uncited_references.length +
          checkResult.year_mismatches.length +
          checkResult.spelling_mismatches.length +
          checkResult.co_author_only_matches.length
        }`,
        `Paragraphs checked: ${checkResult.stats.paragraphs_checked}`,
      ].join("\n")
    : "No check result yet.";

  return [
    `Version: ${BETA_VERSION}`,
    `Mode: ${mode}`,
    `File: ${fileName || "N/A"}`,
    stats,
    "",
    "1. What worked well?",
    "",
    "2. What was confusing?",
    "",
    "3. False positives or wrong APA suggestions:",
    "",
    "4. Missing issues the tool should have found:",
    "",
    "5. Reviewed DOCX formatting/comment problems:",
    "",
    "6. Overall: Would you use this again? Why or why not?",
  ].join("\n");
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

const SEV_BORDER: Record<string, string> = {
  error: "border-red-200 bg-white",
  warning: "border-amber-200 bg-white",
  suggestion: "border-teal-200 bg-white",
  info: "border-sky-200 bg-white",
};
const SEV_BADGE: Record<string, string> = {
  error: "bg-red-50 text-red-700 ring-1 ring-red-200",
  warning: "bg-amber-50 text-amber-800 ring-1 ring-amber-200",
  suggestion: "bg-teal-50 text-teal-800 ring-1 ring-teal-200",
  info: "bg-sky-50 text-sky-800 ring-1 ring-sky-200",
};

const SEVERITY_GUIDE = [
  {
    label: "Info",
    className: "bg-sky-50 text-sky-800 border-sky-200",
    text: "Check program preference.",
  },
  {
    label: "Suggestion",
    className: "bg-teal-50 text-teal-800 border-teal-200",
    text: "Optional style improvement.",
  },
  {
    label: "Warning",
    className: "bg-amber-50 text-amber-800 border-amber-200",
    text: "Review and usually fix.",
  },
  {
    label: "Error",
    className: "bg-red-100 text-red-800 border-red-200",
    text: "Correct before submission.",
  },
];

function FindingCard({ f }: { f: Finding }) {
  const accent: Record<string, string> = {
    error: "before:bg-red-500",
    warning: "before:bg-amber-500",
    suggestion: "before:bg-teal-500",
    info: "before:bg-sky-500",
  };

  return (
    <div className={`relative overflow-hidden border rounded-lg p-4 mb-3 shadow-sm before:absolute before:left-0 before:top-0 before:h-full before:w-1 ${accent[f.severity] ?? "before:bg-slate-300"} ${SEV_BORDER[f.severity] ?? "border-slate-200 bg-white"}`}>
      <div className="flex items-center gap-2 mb-1">
        <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${SEV_BADGE[f.severity] ?? ""}`}>
          {f.severity.toUpperCase()}
        </span>
        <span className="text-xs text-slate-600 font-medium">{ruleLabel(f)}</span>
      </div>
      <p className="text-sm text-slate-800 mb-2 leading-6">{f.message}</p>
      {f.excerpt && (
        <p className="text-xs text-slate-600 font-mono bg-slate-50 rounded-md px-2 py-1.5 border border-slate-200 mb-1 break-words">
          <span className="text-slate-400 select-none">Context: </span>{f.excerpt}
        </p>
      )}
      {f.location_hint && (
        <p className="text-xs text-slate-400 italic mb-1">
          <span className="font-medium not-italic text-slate-500">Find in doc: </span>{f.location_hint}
        </p>
      )}
      {f.suggested_fix && (
        <p className="text-xs text-emerald-700 mt-1">Suggested fix: {f.suggested_fix}</p>
      )}
    </div>
  );
}

function CitationIssueCard({ issue, label }: { issue: Record<string, unknown>; label: string }) {
  const locationHint = typeof issue.location_hint === "string" ? issue.location_hint : "";
  return (
    <div className="border border-amber-200 bg-white rounded-lg p-3 mb-2 shadow-sm">
      <p className="text-xs font-semibold text-amber-700 mb-1">{label}</p>
      <p className="text-sm text-slate-800 leading-6">{String(issue.message)}</p>
      {locationHint && (
        <p className="text-xs text-slate-400 italic mt-1">
          <span className="font-medium not-italic text-slate-500">Find in doc: </span>{locationHint}
        </p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function ReviewPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"paste" | "upload">("upload");
  const [pastedText, setPastedText] = useState("");
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [checking, setChecking] = useState(false);
  const [annotating, setAnnotating] = useState(false);
  const [checkResult, setCheckResult] = useState<CheckResponse | null>(null);
  const [checkError, setCheckError] = useState("");
  const [feedbackCopied, setFeedbackCopied] = useState(false);
  const [tab, setTab] = useState<"apa" | "citations">("apa");

  const [accessChecked, setAccessChecked] = useState(false);
  const [betaExpiry, setBetaExpiry] = useState("");
  const [waking, setWaking] = useState(false);

  useEffect(() => {
    const beta = betaToken();
    const token = localStorage.getItem("submission-pass-token") || sessionStorage.getItem("submission-pass-token") || "";
    if (!beta && !token) {
      router.replace("/account");
      return;
    }
    // The API sleeps when idle and can take up to a minute to wake, so say so
    // rather than leaving a blank screen, and retry once before giving up.
    const slowTimer = window.setTimeout(() => setWaking(true), 4000);
    const askForAccess = () => beta
      ? fetch(`${API_BASE}/api/beta/access`, { headers: { "X-Beta-Access": beta } })
      : fetch(`${API_BASE}/api/account/entitlement`, { headers: { Authorization: `Bearer ${token}` } });
    const accessRequest = askForAccess().catch(() => askForAccess());
    const fallback = beta ? "/beta" : "/account";
    void accessRequest
      .finally(() => window.clearTimeout(slowTimer))
      .then(async (response) => response.ok ? response.json() : null)
      .then((access: { can_submit?: boolean; expires_at?: string | null } | null) => {
        if (!access?.can_submit) {
          if (beta) localStorage.removeItem("beta-access-token");
          router.replace(fallback);
          return;
        }
        if (beta && access.expires_at) setBetaExpiry(access.expires_at);
        setAccessChecked(true);
      })
      .catch(() => router.replace(fallback));
  }, [router]);

  // ---------------------------------------------------------------------------
  // APA check
  // ---------------------------------------------------------------------------

  async function handleCheck(e: React.FormEvent) {
    e.preventDefault();
    setChecking(true);
    setCheckError("");
    setCheckResult(null);

    try {
      let data: CheckResponse;

      if (mode === "upload" && uploadedFile) {
        const form = new FormData();
        form.append("file", uploadedFile);
        const res = await fetch(`${API_BASE}/api/check/docx`, { method: "POST", body: form, headers: authHeaders() });
        if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `HTTP ${res.status}`);
        data = await res.json();
      } else {
        const { body, refs } = splitOnReferences(pastedText);
        const res = await fetch(`${API_BASE}/api/check/text`, {
          method: "POST",
          headers: { "Content-Type": "application/json", ...authHeaders() },
          body: JSON.stringify({ body_text: body, reference_text: refs, levenshtein_threshold: 2 }),
        });
        if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `HTTP ${res.status}`);
        data = await res.json();
      }

      setCheckResult(data);
      setTab("apa");
    } catch (err) {
      setCheckError(err instanceof Error ? err.message : "Request failed.");
    } finally {
      setChecking(false);
    }
  }

  async function handleDownloadAnnotated() {
    if (!uploadedFile) return;
    setAnnotating(true);
    setCheckError("");

    try {
      const form = new FormData();
      form.append("file", uploadedFile);
      const res = await fetch(`${API_BASE}/api/check/docx/annotated`, { method: "POST", body: form, headers: authHeaders() });
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `HTTP ${res.status}`);

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      const baseName = uploadedFile.name.replace(/\.docx$/i, "");
      link.href = url;
      link.download = `${baseName}_reviewed.docx`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setCheckError(err instanceof Error ? err.message : "Could not create annotated document.");
    } finally {
      setAnnotating(false);
    }
  }

  async function handleCopyFeedbackTemplate() {
    const template = buildFeedbackTemplate({
      mode,
      fileName: uploadedFile?.name ?? "",
      checkResult,
    });
    await navigator.clipboard.writeText(template);
    setFeedbackCopied(true);
    window.setTimeout(() => setFeedbackCopied(false), 2500);
  }

  function handleEmailFeedback() {
    const template = buildFeedbackTemplate({
      mode,
      fileName: uploadedFile?.name ?? "",
      checkResult,
    });
    const subject = encodeURIComponent(`APA 7 Review Tool beta feedback - ${BETA_VERSION}`);
    const body = encodeURIComponent(template);
    window.location.href = `mailto:${FEEDBACK_EMAIL}?subject=${subject}&body=${body}`;
  }

  const citationTotal = checkResult
    ? checkResult.missing_references.length + checkResult.uncited_references.length +
      checkResult.year_mismatches.length + checkResult.spelling_mismatches.length +
      checkResult.co_author_only_matches.length
    : 0;
  const citationIssues = checkResult
    ? [
        ...checkResult.spelling_mismatches.map((issue) => ({
          issue,
          label: "Possible spelling mismatch - review, do not auto-correct",
        })),
        ...checkResult.year_mismatches.map((issue) => ({ issue, label: "Year mismatch" })),
        ...checkResult.missing_references.map((issue) => ({
          issue,
          label: issue.severity === "error" ? "Missing reference" : "Possible missing reference",
        })),
        ...checkResult.co_author_only_matches.map((issue) => ({
          issue,
          label: "Co-author-only match (soft flag)",
        })),
        ...checkResult.uncited_references.map((issue) => ({
          issue,
          label: "Reference not cited in text",
        })),
      ].sort((a, b) => compareCitationIssues(a.issue, b.issue))
    : [];

  const words = mode === "paste" ? wordCount(pastedText) : uploadedFile ? null : 0;
  const canSubmit = mode === "paste" ? pastedText.trim().length > 0 : uploadedFile !== null;

  if (!accessChecked) {
    return (
      <main className="mx-auto min-h-screen max-w-xl px-6 py-16 text-slate-700">
        <p>Opening your review…</p>
        {waking && (
          <p className="mt-3 text-sm text-slate-500">
            The server is waking up after being idle. This can take up to a minute the first time — no need to refresh.
          </p>
        )}
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#f7f8f5] text-slate-900">
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 sm:py-10">

        <div className="mx-auto mb-7 max-w-2xl border-b border-[#dce4db] pb-5 text-center">
          {betaExpiry ? (
            <p className="text-sm font-semibold text-[#2f7d6b]">
              Private beta access — expires {new Date(betaExpiry).toLocaleDateString()}
            </p>
          ) : (
            <Link href="/account" className="text-sm font-semibold text-blue-700">Manage Submission Pass</Link>
          )}
          <h1 className="text-3xl font-semibold tracking-normal text-slate-950 sm:text-4xl">
            Review your document before submission
          </h1>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            Upload a Word document to find APA, citation, style, and formatting issues. Download a reviewed copy with comments in the same document.
          </p>
          <p className="mt-2 text-xs leading-5 text-slate-500">
            <span className="font-semibold text-slate-600">Privacy:</span> Uploaded documents and pasted text are processed securely on the server for the purpose of generating this review, deleted immediately after processing, and are not stored or used for model training.
          </p>
          <p className="mt-2 text-xs leading-5 text-slate-500">
            <span className="font-semibold text-slate-600">Review method:</span> Findings are produced by deterministic, rule-based checks. No large language model generates the review results.
          </p>
        </div>

        {/* Input form */}
        <form onSubmit={handleCheck} className="mx-auto mb-5 max-w-2xl">

          {/* Mode toggle */}
          <div className="mb-3 flex justify-center">
            <div className="flex gap-1 rounded-lg border border-[#dce4db] bg-white p-1 shadow-sm">
              <button
                type="button"
                onClick={() => setMode("upload")}
                className={`button-interaction rounded-md px-4 py-1.5 text-sm font-semibold ${mode === "upload" ? "bg-[#e8efe8] text-[#123c3d] shadow-sm" : "text-slate-500 hover:bg-[#eef3ee] hover:text-slate-800"}`}
              >
                Upload .docx
              </button>
              <button
                type="button"
                onClick={() => { setMode("paste"); setUploadedFile(null); }}
                className={`button-interaction rounded-md px-4 py-1.5 text-sm font-semibold ${mode === "paste" ? "bg-[#e8efe8] text-[#123c3d] shadow-sm" : "text-slate-500 hover:bg-[#eef3ee] hover:text-slate-800"}`}
              >
                Paste text
              </button>
            </div>
          </div>

          {mode === "paste" ? (
            <div>
              <textarea
                value={pastedText}
                onChange={(e) => setPastedText(e.target.value)}
                rows={16}
                placeholder={`Paste your text here — body and references together.\n\nIf your reference list starts with a "References" heading, citation matching will work automatically.`}
                className="w-full resize-y rounded-lg border border-[#cfd9cf] bg-white px-3 py-2.5 font-mono text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-[#2f7d6b]"
              />
              {words !== null && words > 0 && (
                <p className="mt-1 text-xs text-slate-400">{words.toLocaleString()} words</p>
              )}
            </div>
          ) : (
            <div
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                const f = e.dataTransfer.files[0];
                if (f?.name.endsWith(".docx")) setUploadedFile(f);
              }}
              className="cursor-pointer rounded-lg border-2 border-dashed border-[#b8c9bd] bg-white p-8 text-center shadow-sm transition hover:border-[#2f7d6b] hover:bg-[#f4faf6]"
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".docx"
                className="hidden"
                onChange={(e) => setUploadedFile(e.target.files?.[0] ?? null)}
              />
              {uploadedFile ? (
                <div>
                  <p className="text-sm font-semibold text-slate-900">{uploadedFile.name}</p>
                  <p className="mt-1 text-xs text-slate-400">{(uploadedFile.size / 1024).toFixed(0)} KB</p>
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); setUploadedFile(null); }}
                    className="button-interaction mt-2 rounded text-xs font-medium text-red-600 underline"
                  >
                    Remove
                  </button>
                </div>
              ) : (
                <div>
                  <p className="text-sm font-semibold text-slate-800">Drop a .docx file here, or click to browse</p>
                  <p className="mt-1 text-xs text-slate-500">Heading styles, block quotes, bullet lists, tables, and figures are handled automatically</p>
                </div>
              )}
            </div>
          )}

          <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:justify-center">
            <button
              type="submit"
              disabled={checking || !canSubmit}
              className="button-interaction rounded-lg bg-[#123c3d] px-6 py-2.5 font-semibold text-white hover:bg-[#0b3031] disabled:opacity-50"
            >
              {checking ? "Checking..." : "Run APA 7 check"}
            </button>
            {mode === "upload" && uploadedFile && checkResult && (
              <button
                type="button"
                onClick={handleDownloadAnnotated}
                disabled={annotating}
                className="button-interaction rounded-lg bg-[#123c3d] px-6 py-2.5 font-semibold text-white hover:bg-[#0b3031] disabled:opacity-50"
              >
                {annotating ? "Preparing..." : "Download reviewed .docx"}
              </button>
            )}
          </div>
        </form>

        <section className="mx-auto mb-6 max-w-4xl">
          <div className="grid gap-4 rounded-lg border border-[#dce4db] bg-white/85 p-3 shadow-sm sm:grid-cols-[0.95fr_1.35fr] sm:items-center">
            <div className="px-1 py-2 sm:px-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-[#2f7d6b]">Sample reviewed document</p>
              <h2 className="mt-2 text-lg font-semibold text-slate-950">See comments beside the highlighted text</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                The reviewed DOCX keeps your document format and adds color-coded highlights with comments beside the relevant sentence or phrase.
              </p>
            </div>
            <div className="overflow-hidden rounded-md border border-[#dce4db] bg-slate-50">
              <Image
                src="/review-output-sample.png"
                alt="Sample reviewed Word document with highlighted text and review comments"
                width={1143}
                height={813}
                unoptimized
                priority
                className="h-auto w-full"
              />
            </div>
          </div>
        </section>

        <div className="mx-auto mb-5 flex max-w-4xl flex-wrap items-center justify-center gap-2 text-xs">
          <span className="mr-1 font-semibold text-slate-700">Severity Category with Suggested Action</span>
          {SEVERITY_GUIDE.map((item) => (
            <span key={item.label} className={`rounded-full border px-2.5 py-1 ${item.className}`}>
              <span className="font-semibold">{item.label}:</span> {item.text}
            </span>
          ))}
        </div>

        <div className="mx-auto mb-6 flex max-w-4xl flex-col items-center gap-3 border-t border-[#dce4db] pt-4 text-center">
          <p className="text-xs text-slate-500">
            {BETA_VERSION} private beta: check the on-screen findings and reviewed DOCX, then report false positives or confusing comments.
          </p>
          {checkResult && (
            <div className="flex flex-wrap justify-center gap-2">
              <button
                type="button"
                onClick={handleCopyFeedbackTemplate}
                className="button-secondary rounded-md border-[#cfd9cf] px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-[#f4faf6]"
              >
                {feedbackCopied ? "Template copied" : "Copy feedback template"}
              </button>
              {FEEDBACK_EMAIL && (
                <button
                  type="button"
                  onClick={handleEmailFeedback}
                  className="button-interaction rounded-md bg-slate-900 px-3 py-2 text-xs font-semibold text-white hover:bg-slate-800"
                >
                  Email beta feedback
                </button>
              )}
            </div>
          )}
        </div>

        {checkError && (
          <div className="mb-6 rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-700">
            Error: {checkError}
          </div>
        )}

        {/* Results */}
        {checkResult && (
          <div className="mb-8">
            <div className="mb-4 grid gap-3 rounded-lg border border-[#dce4db] bg-white p-3 text-sm shadow-sm sm:grid-cols-5">
              <span className="rounded-md bg-[#f4faf6] px-3 py-2"><strong>{checkResult.stats.paragraphs_checked}</strong> paragraphs</span>
              <span className="rounded-md bg-[#f4faf6] px-3 py-2"><strong>{checkResult.apa_findings.length}</strong> APA findings</span>
              <span className="rounded-md bg-[#f4faf6] px-3 py-2"><strong>{checkResult.stats.citations_found}</strong> citations</span>
              <span className="rounded-md bg-[#f4faf6] px-3 py-2"><strong>{checkResult.stats.references_parsed}</strong> references</span>
              {citationTotal > 0 && <span className="rounded-md bg-amber-50 px-3 py-2 text-amber-700"><strong>{citationTotal}</strong> citation issues</span>}
            </div>

            {checkResult.scope_warning && (
              <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
                {checkResult.scope_warning}
              </div>
            )}

            <div className="mb-4 flex border-b border-[#dce4db]">
              {(["apa", "citations"] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className={`button-interaction px-4 py-2 text-sm font-semibold ${tab === t ? "border-b-2 border-[#123c3d] text-[#123c3d]" : "text-slate-500 hover:text-slate-700"}`}
                >
                  {t === "apa" ? `APA Rules (${checkResult.apa_findings.length})` : `Citations (${citationTotal})`}
                </button>
              ))}
            </div>

            {tab === "apa" && (
              checkResult.apa_findings.length === 0
                ? <p className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">No APA 7 rule findings.</p>
                : checkResult.apa_findings.map((f, i) => <FindingCard key={i} f={f} />)
            )}

            {tab === "citations" && (
              <div>
                {citationIssues.map(({ issue, label }, i) => (
                  <CitationIssueCard key={`ci-${i}`} issue={issue as unknown as Record<string, unknown>} label={label} />
                ))}
                {citationTotal === 0 && (
                  <p className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">
                    No citation issues.
                    {checkResult.stats.references_parsed === 0 && " No reference list detected — include a \"References\" heading in your text for citation matching."}
                  </p>
                )}
              </div>
            )}
          </div>
        )}

      </div>
    </main>
  );
}
