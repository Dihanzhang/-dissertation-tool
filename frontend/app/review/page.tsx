"use client";

import { useState, useCallback, useRef } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const BETA_VERSION = process.env.NEXT_PUBLIC_BETA_VERSION || "Beta v0.1";
const FEEDBACK_EMAIL = process.env.NEXT_PUBLIC_FEEDBACK_EMAIL || "";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Finding {
  rule_id: string;
  severity: "error" | "warning" | "info";
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

interface Suggestion {
  original: string;
  revised: string;
  reason: string;
  edit_type: "light" | "heavy";
  change_ratio: number;
}

interface ReviewResponse {
  status: "ok" | "oversized_confirmation" | "no_credits" | "error";
  suggestions: Suggestion[];
  word_count: number;
  chunk_count: number;
  credits_required: number;
  credits_remaining: number;
  model_used: string;
  rejected_by_citation_lock: number;
  rejected_sentence_not_found: number;
  message: string;
  test_mode: boolean;
}

type SuggestionDecision = "pending" | "accepted" | "rejected";

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

function randomId() {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

const RULE_LABELS: Record<string, string> = {
  PRF001: "Short paragraph",
  REF010: "Publisher business designation",
  STY001: "Passive voice",
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
  error: "border-red-300 bg-red-50",
  warning: "border-yellow-300 bg-yellow-50",
  info: "border-blue-200 bg-blue-50",
};
const SEV_BADGE: Record<string, string> = {
  error: "bg-red-100 text-red-700",
  warning: "bg-yellow-100 text-yellow-700",
  info: "bg-blue-100 text-blue-700",
};

function FindingCard({ f }: { f: Finding }) {
  return (
    <div className={`border rounded-lg p-4 mb-3 ${SEV_BORDER[f.severity] ?? "border-gray-200 bg-gray-50"}`}>
      <div className="flex items-center gap-2 mb-1">
        <span className={`text-xs font-semibold px-2 py-0.5 rounded ${SEV_BADGE[f.severity] ?? ""}`}>
          {f.severity.toUpperCase()}
        </span>
        <span className="text-xs text-gray-600 font-medium">{ruleLabel(f)}</span>
      </div>
      <p className="text-sm text-gray-800 mb-2">{f.message}</p>
      {f.excerpt && (
        <p className="text-xs text-gray-600 font-mono bg-white/70 rounded px-2 py-1 border border-gray-200 mb-1 break-words">
          <span className="text-gray-400 select-none">Context: </span>{f.excerpt}
        </p>
      )}
      {f.location_hint && (
        <p className="text-xs text-gray-400 italic mb-1">
          <span className="font-medium not-italic text-gray-500">Find in doc: </span>{f.location_hint}
        </p>
      )}
      {f.suggested_fix && (
        <p className="text-xs text-green-700 mt-1">Suggested fix: {f.suggested_fix}</p>
      )}
    </div>
  );
}

function CitationIssueCard({ issue, label }: { issue: Record<string, unknown>; label: string }) {
  const locationHint = typeof issue.location_hint === "string" ? issue.location_hint : "";
  return (
    <div className="border border-orange-200 bg-orange-50 rounded-lg p-3 mb-2">
      <p className="text-xs font-semibold text-orange-700 mb-1">{label}</p>
      <p className="text-sm text-gray-800">{String(issue.message)}</p>
      {locationHint && (
        <p className="text-xs text-gray-400 italic mt-1">
          <span className="font-medium not-italic text-gray-500">Find in doc: </span>{locationHint}
        </p>
      )}
    </div>
  );
}

function SuggestionCard({
  s, index, decision, onDecide,
}: {
  s: Suggestion; index: number; decision: SuggestionDecision; onDecide: (d: SuggestionDecision) => void;
}) {
  const heavy = s.edit_type === "heavy";
  const border =
    decision === "accepted" ? "border-green-400 bg-green-50" :
    decision === "rejected" ? "border-gray-200 bg-gray-50 opacity-60" :
    heavy ? "border-amber-300 bg-amber-50" : "border-blue-200 bg-white";

  return (
    <div className={`border rounded-lg p-4 mb-3 transition-all ${border}`}>
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-semibold text-gray-400">#{index + 1}</span>
        <span className="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-600">{s.reason}</span>
        {heavy && (
          <span className="text-xs px-2 py-0.5 rounded bg-amber-100 text-amber-700 font-semibold">
            HEAVY EDIT — review carefully
          </span>
        )}
        <span className="text-xs text-gray-400 ml-auto">{Math.round(s.change_ratio * 100)}% changed</span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
        <div>
          <p className="text-xs font-medium text-gray-500 mb-1">Original</p>
          <p className="text-sm text-gray-700 bg-gray-50 rounded p-2 border border-gray-200 leading-relaxed">{s.original}</p>
        </div>
        <div>
          <p className="text-xs font-medium text-gray-500 mb-1">Revised</p>
          <p className="text-sm text-gray-800 bg-blue-50 rounded p-2 border border-blue-200 leading-relaxed">{s.revised}</p>
        </div>
      </div>
      {decision === "pending" ? (
        <div className="flex gap-2">
          <button onClick={() => onDecide("accepted")} className="px-3 py-1.5 text-xs font-semibold bg-green-600 text-white rounded hover:bg-green-700 transition">Accept</button>
          <button onClick={() => onDecide("rejected")} className="px-3 py-1.5 text-xs font-semibold bg-gray-200 text-gray-700 rounded hover:bg-gray-300 transition">Reject</button>
        </div>
      ) : (
        <div className="flex items-center gap-2">
          <span className={`text-xs font-semibold ${decision === "accepted" ? "text-green-700" : "text-gray-500"}`}>
            {decision === "accepted" ? "✓ Accepted" : "✗ Rejected"}
          </span>
          <button onClick={() => onDecide("pending")} className="text-xs text-gray-400 underline hover:text-gray-600">Undo</button>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function ReviewPage() {
  const [mode, setMode] = useState<"paste" | "upload">("paste");
  const [pastedText, setPastedText] = useState("");
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [checking, setChecking] = useState(false);
  const [annotating, setAnnotating] = useState(false);
  const [checkResult, setCheckResult] = useState<CheckResponse | null>(null);
  const [checkError, setCheckError] = useState("");
  const [feedbackCopied, setFeedbackCopied] = useState(false);
  const [tab, setTab] = useState<"apa" | "citations">("apa");

  const [reviewing, setReviewing] = useState(false);
  const [reviewResult, setReviewResult] = useState<ReviewResponse | null>(null);
  const [reviewError, setReviewError] = useState("");
  const [pendingOversized, setPendingOversized] = useState<ReviewResponse | null>(null);
  const [decisions, setDecisions] = useState<Record<number, SuggestionDecision>>({});
  const [requestId] = useState(randomId);

  // The body text used for Module 1 (set after check so we know what was submitted)
  const [submittedBodyText, setSubmittedBodyText] = useState("");

  // ---------------------------------------------------------------------------
  // APA check
  // ---------------------------------------------------------------------------

  async function handleCheck(e: React.FormEvent) {
    e.preventDefault();
    setChecking(true);
    setCheckError("");
    setCheckResult(null);
    setReviewResult(null);
    setPendingOversized(null);
    setDecisions({});

    try {
      let data: CheckResponse;

      if (mode === "upload" && uploadedFile) {
        const form = new FormData();
        form.append("file", uploadedFile);
        const res = await fetch(`${API_BASE}/api/check/docx`, { method: "POST", body: form });
        if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `HTTP ${res.status}`);
        data = await res.json();
        setSubmittedBodyText("");  // docx body managed server-side
      } else {
        const { body, refs } = splitOnReferences(pastedText);
        setSubmittedBodyText(body);
        const res = await fetch(`${API_BASE}/api/check/text`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
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
      const res = await fetch(`${API_BASE}/api/check/docx/annotated`, { method: "POST", body: form });
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
    const subject = encodeURIComponent(`Dissertation Review beta feedback - ${BETA_VERSION}`);
    const body = encodeURIComponent(template);
    window.location.href = `mailto:${FEEDBACK_EMAIL}?subject=${subject}&body=${body}`;
  }

  // ---------------------------------------------------------------------------
  // AI polish (Module 1) — paste mode only for now
  // ---------------------------------------------------------------------------

  const runReview = useCallback(async (confirmed = false) => {
    const text = submittedBodyText || pastedText;
    if (!text.trim()) return;
    setReviewing(true);
    setReviewError("");
    setPendingOversized(null);

    try {
      const res = await fetch(`${API_BASE}/api/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          body_text: text,
          request_id: requestId + (confirmed ? "_c" : ""),
          user_id: "anonymous",
          tier: "paid",
          confirmed_oversized: confirmed,
        }),
      });
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `HTTP ${res.status}`);
      const data: ReviewResponse = await res.json();
      if (data.status === "oversized_confirmation") {
        setPendingOversized(data);
      } else {
        setReviewResult(data);
        setDecisions({});
      }
    } catch (err) {
      setReviewError(err instanceof Error ? err.message : "Review failed.");
    } finally {
      setReviewing(false);
    }
  }, [submittedBodyText, pastedText, requestId]);

  function decide(i: number, d: SuggestionDecision) {
    setDecisions((prev) => ({ ...prev, [i]: d }));
  }

  function buildAcceptedText() {
    if (!reviewResult) return submittedBodyText || pastedText;
    let text = submittedBodyText || pastedText;
    reviewResult.suggestions
      .filter((_, i) => decisions[i] === "accepted")
      .forEach((s) => { text = text.replace(s.original, s.revised); });
    return text;
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

  const acceptedCount = Object.values(decisions).filter((d) => d === "accepted").length;
  const words = mode === "paste" ? wordCount(pastedText) : uploadedFile ? null : 0;
  const canSubmit = mode === "paste" ? pastedText.trim().length > 0 : uploadedFile !== null;

  return (
    <main className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-10">

        <h1 className="text-2xl font-bold text-gray-900 mb-1">Dissertation Review</h1>
        <p className="text-sm text-gray-500 mb-4">
          APA 7 rule checking is free. AI-assisted polish uses credits.
        </p>

        <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-2 text-xs text-blue-700 mb-6">
          Your text is processed server-side and deleted immediately. Not stored, not used for training.
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-4 mb-6">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <div className="flex flex-wrap items-center gap-2 mb-2">
                <span className="text-xs font-semibold px-2 py-0.5 rounded bg-indigo-100 text-indigo-700">
                  {BETA_VERSION}
                </span>
                <span className="text-sm font-semibold text-gray-900">Private beta test</span>
              </div>
              <ol className="list-decimal list-inside text-xs text-gray-600 space-y-1">
                <li>Upload a DOCX chapter or paste a short sample.</li>
                <li>Run the free APA check and review the on-screen findings.</li>
                <li>For DOCX uploads, download the reviewed copy and inspect Word comments.</li>
                <li>Report false positives, missing issues, confusing wording, and formatting problems.</li>
              </ol>
              <p className="text-xs text-gray-500 mt-3">
                For testing, remove sensitive names or confidential content when possible.
              </p>
            </div>
            <div className="flex flex-col gap-2 sm:min-w-48">
              <button
                type="button"
                onClick={handleCopyFeedbackTemplate}
                className="px-3 py-2 text-xs font-semibold border border-gray-300 rounded bg-white text-gray-700 hover:bg-gray-50 transition"
              >
                {feedbackCopied ? "Template copied" : "Copy feedback template"}
              </button>
              {FEEDBACK_EMAIL && (
                <button
                  type="button"
                  onClick={handleEmailFeedback}
                  className="px-3 py-2 text-xs font-semibold bg-gray-900 text-white rounded hover:bg-gray-800 transition"
                >
                  Email beta feedback
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Input form */}
        <form onSubmit={handleCheck} className="mb-6">

          {/* Mode toggle */}
          <div className="flex gap-1 p-1 bg-gray-100 rounded-lg w-fit mb-4">
            <button
              type="button"
              onClick={() => { setMode("paste"); setUploadedFile(null); }}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition ${mode === "paste" ? "bg-white shadow text-gray-900" : "text-gray-500 hover:text-gray-700"}`}
            >
              Paste text
            </button>
            <button
              type="button"
              onClick={() => setMode("upload")}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition ${mode === "upload" ? "bg-white shadow text-gray-900" : "text-gray-500 hover:text-gray-700"}`}
            >
              Upload .docx
            </button>
          </div>

          {mode === "paste" ? (
            <div>
              <textarea
                value={pastedText}
                onChange={(e) => setPastedText(e.target.value)}
                rows={16}
                placeholder={`Paste your text here — body and references together.\n\nIf your reference list starts with a "References" heading, citation matching will work automatically.`}
                className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
              />
              {words !== null && words > 0 && (
                <p className="text-xs text-gray-400 mt-1">{words.toLocaleString()} words</p>
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
              className="border-2 border-dashed border-gray-300 rounded-lg p-10 text-center cursor-pointer hover:border-blue-400 hover:bg-blue-50 transition"
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
                  <p className="text-sm font-medium text-gray-800">{uploadedFile.name}</p>
                  <p className="text-xs text-gray-400 mt-1">{(uploadedFile.size / 1024).toFixed(0)} KB</p>
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); setUploadedFile(null); }}
                    className="text-xs text-red-500 underline mt-2"
                  >
                    Remove
                  </button>
                </div>
              ) : (
                <div>
                  <p className="text-sm text-gray-500">Drop a .docx file here, or click to browse</p>
                  <p className="text-xs text-gray-400 mt-1">Heading styles, block quotes, and tables are handled automatically</p>
                </div>
              )}
            </div>
          )}

          <button
            type="submit"
            disabled={checking || !canSubmit}
            className="mt-4 px-6 py-2.5 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50 transition"
          >
            {checking ? "Checking…" : "Run APA 7 check (free)"}
          </button>
        </form>

        {checkError && (
          <div className="border border-red-300 bg-red-50 rounded-lg p-4 text-red-700 text-sm mb-6">
            Error: {checkError}
          </div>
        )}

        {/* Results */}
        {checkResult && (
          <div className="mb-8">
            <div className="bg-white border border-gray-200 rounded-lg p-4 mb-4 flex flex-wrap gap-6 text-sm">
              <span><strong>{checkResult.stats.paragraphs_checked}</strong> paragraphs</span>
              <span><strong>{checkResult.apa_findings.length}</strong> APA findings</span>
              <span><strong>{checkResult.stats.citations_found}</strong> citations</span>
              <span><strong>{checkResult.stats.references_parsed}</strong> references</span>
              {citationTotal > 0 && <span className="text-orange-600"><strong>{citationTotal}</strong> citation issues</span>}
            </div>

            {checkResult.scope_warning && (
              <div className="border border-yellow-200 bg-yellow-50 rounded-lg px-4 py-2 text-sm text-yellow-800 mb-4">
                {checkResult.scope_warning}
              </div>
            )}

            {mode === "upload" && uploadedFile && (
              <div className="bg-white border border-gray-200 rounded-lg p-4 mb-4 flex flex-col sm:flex-row sm:items-center gap-3 sm:justify-between">
                <div>
                  <p className="text-sm font-semibold text-gray-800">Annotated DOCX</p>
                  <p className="text-xs text-gray-500">Downloads a copy with highlighted findings and Word comments beside the problem text.</p>
                </div>
                <button
                  type="button"
                  onClick={handleDownloadAnnotated}
                  disabled={annotating}
                  className="px-4 py-2 bg-green-600 text-white text-sm font-semibold rounded hover:bg-green-700 disabled:opacity-50 transition"
                >
                  {annotating ? "Preparing..." : "Download reviewed .docx"}
                </button>
              </div>
            )}

            <div className="flex border-b border-gray-200 mb-4">
              {(["apa", "citations"] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className={`px-4 py-2 text-sm font-medium ${tab === t ? "border-b-2 border-blue-600 text-blue-600" : "text-gray-500 hover:text-gray-700"}`}
                >
                  {t === "apa" ? `APA Rules (${checkResult.apa_findings.length})` : `Citations (${citationTotal})`}
                </button>
              ))}
            </div>

            {tab === "apa" && (
              checkResult.apa_findings.length === 0
                ? <p className="text-sm text-green-700 bg-green-50 border border-green-200 rounded-lg p-4">No APA 7 rule findings.</p>
                : checkResult.apa_findings.map((f, i) => <FindingCard key={i} f={f} />)
            )}

            {tab === "citations" && (
              <div>
                {citationIssues.map(({ issue, label }, i) => (
                  <CitationIssueCard key={`ci-${i}`} issue={issue as unknown as Record<string, unknown>} label={label} />
                ))}
                {citationTotal === 0 && (
                  <p className="text-sm text-green-700 bg-green-50 border border-green-200 rounded-lg p-4">
                    No citation issues.
                    {checkResult.stats.references_parsed === 0 && " No reference list detected — include a \"References\" heading in your text for citation matching."}
                  </p>
                )}
              </div>
            )}
          </div>
        )}

        {/* AI Polish — only available for pasted text (docx body not retained client-side) */}
        {checkResult && mode === "paste" && (
          <div className="border-t border-gray-200 pt-8">
            <h2 className="text-lg font-semibold text-gray-900 mb-1">AI-Assisted Polish</h2>
            <p className="text-sm text-gray-500 mb-4">
              Improves clarity, reduces passive voice, raises doctoral register.
              Every suggestion requires your approval — citations are locked and cannot be changed.
            </p>

            {pendingOversized && (
              <div className="border border-amber-300 bg-amber-50 rounded-lg p-4 mb-4">
                <p className="text-sm font-semibold text-amber-800 mb-1">Multi-credit submission</p>
                <p className="text-sm text-amber-700 mb-3">{pendingOversized.message}</p>
                <div className="flex gap-3">
                  <button onClick={() => runReview(true)} className="px-4 py-2 bg-amber-600 text-white text-sm font-semibold rounded hover:bg-amber-700 transition">
                    Confirm — use {pendingOversized.credits_required} credits
                  </button>
                  <button onClick={() => setPendingOversized(null)} className="px-4 py-2 bg-white border border-gray-300 text-gray-700 text-sm font-semibold rounded hover:bg-gray-50 transition">
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {reviewError && (
              <div className="border border-red-300 bg-red-50 rounded-lg p-4 text-red-700 text-sm mb-4">{reviewError}</div>
            )}

            {!reviewResult && !pendingOversized && (
              <button
                onClick={() => runReview(false)}
                disabled={reviewing}
                className="px-6 py-2.5 bg-violet-600 text-white rounded-lg font-semibold hover:bg-violet-700 disabled:opacity-50 transition"
              >
                {reviewing ? "Running AI review…" : "Run AI polish (1 credit)"}
              </button>
            )}

            {reviewing && <p className="text-sm text-gray-500 mt-2 animate-pulse">Sending to AI… 10–30 seconds.</p>}

            {reviewResult && (
              <div>
                <div className="bg-white border border-gray-200 rounded-lg p-4 mb-4 flex flex-wrap gap-6 text-sm">
                  <span><strong>{reviewResult.suggestions.length}</strong> suggestion(s)</span>
                  <span><strong>{acceptedCount}</strong> accepted</span>
                  {reviewResult.rejected_by_citation_lock > 0 && (
                    <span className="text-amber-700"><strong>{reviewResult.rejected_by_citation_lock}</strong> blocked by citation lock</span>
                  )}
                  {reviewResult.model_used && <span className="text-gray-400 font-mono text-xs ml-auto">{reviewResult.model_used}</span>}
                  {reviewResult.test_mode && <span className="text-purple-600 text-xs font-semibold">TEST MODE</span>}
                </div>

                {reviewResult.suggestions.length === 0 ? (
                  <p className="text-sm text-green-700 bg-green-50 border border-green-200 rounded-lg p-4">
                    No clarity or register improvements found. Your writing looks strong on these dimensions.
                  </p>
                ) : (
                  <>
                    {reviewResult.suggestions.map((s, i) => (
                      <SuggestionCard key={i} s={s} index={i} decision={decisions[i] ?? "pending"} onDecide={(d) => decide(i, d)} />
                    ))}

                    {acceptedCount > 0 && (
                      <div className="mt-6">
                        <h3 className="text-sm font-semibold text-gray-700 mb-2">Preview with accepted changes ({acceptedCount})</h3>
                        <textarea
                          readOnly
                          value={buildAcceptedText()}
                          rows={10}
                          className="w-full border border-green-300 rounded-lg px-3 py-2 text-sm font-mono bg-green-50 resize-y"
                        />
                        <button
                          onClick={() => navigator.clipboard.writeText(buildAcceptedText())}
                          className="mt-2 px-4 py-1.5 text-xs bg-green-600 text-white rounded hover:bg-green-700 transition"
                        >
                          Copy to clipboard
                        </button>
                      </div>
                    )}
                  </>
                )}
              </div>
            )}
          </div>
        )}

      </div>
    </main>
  );
}
