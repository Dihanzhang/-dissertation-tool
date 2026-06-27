import Link from "next/link";

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-white">
      {/* Hero */}
      <section className="max-w-3xl mx-auto px-6 py-20 text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          Dissertation APA&nbsp;7 Review Assistant
        </h1>
        <p className="text-lg text-gray-600 mb-2">
          Doctoral writing review, APA&nbsp;7 alignment, citation/reference
          checking, and professor-rule compliance.
        </p>
        <p className="text-base text-gray-500 mb-8">
          Flags and suggests — you approve every change. Designed to stay on
          the right side of university academic-integrity policies.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 justify-center mb-12">
          <Link
            href="/review"
            className="px-8 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition"
          >
            Try one section free
          </Link>
          <a
            href="#pricing"
            className="px-8 py-3 border border-gray-300 text-gray-700 rounded-lg font-semibold hover:bg-gray-50 transition"
          >
            See pricing
          </a>
        </div>

        {/* Data notice */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-blue-800 text-left">
          <strong>Data handling:</strong> Your uploaded text is processed to
          generate your review and then deleted. It is not used to train models
          and is not retained.
        </div>
      </section>

      {/* Feature list */}
      <section className="max-w-3xl mx-auto px-6 pb-16">
        <h2 className="text-2xl font-semibold text-gray-800 mb-6">
          What it checks (free — no login required)
        </h2>
        <ul className="space-y-3 text-gray-700">
          {[
            "APA 7 heading levels (Levels 1–5, skipped levels, headings with no body text)",
            "Numbers: spelled-out vs numeral rule, with unit/statistic/table exemptions",
            'Demonstrative pronouns as bare subjects (“This shows” flagged; “This study” not)',
            "Personal pronouns in author prose — softened in positionality/reflexivity sections",
            "Banned words and expeditionary verbs — in author prose only, never inside quotes",
            "Repeated narrative citations within the same paragraph (APA §8.16)",
            "Citation–reference cross-matching: missing, uncited, year mismatches",
            "Spelling mismatches between citation and reference (Levenshtein ≤ 2, same year)",
            "Co-author-only soft flags (e.g. Davis as co-author but not first author)",
            "Compound and group author parsing (Al Abri, APA, Van den Berg)",
          ].map((item) => (
            <li key={item} className="flex gap-2">
              <span className="text-blue-500 mt-0.5">✓</span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </section>

      {/* Pricing */}
      <section id="pricing" className="bg-gray-50 py-16">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <h2 className="text-2xl font-semibold text-gray-800 mb-4">
            Pricing
          </h2>
          <div className="inline-block bg-white border border-gray-200 rounded-xl p-8 shadow-sm text-left">
            <p className="text-3xl font-bold text-gray-900 mb-1">$14.99</p>
            <p className="text-gray-600 mb-4">
              10 AI-assisted reviews of up to 5,000 words each — use them
              across one document or many, in any order.
            </p>
            <ul className="text-sm text-gray-600 space-y-1 mb-6">
              <li>› Re-running a revised section uses one review</li>
              <li>› APA rule-checking is always free (no credit used)</li>
              <li>› Credits are non-expiring at launch</li>
            </ul>
            <Link
              href="/review"
              className="block text-center px-6 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition"
            >
              Try one section free first
            </Link>
          </div>
        </div>
      </section>

      {/* Limitation notice */}
      <section className="max-w-3xl mx-auto px-6 py-10 text-sm text-gray-500">
        <p>
          <strong>Limitation notice:</strong> This tool supports writing review
          and APA alignment. It does not replace supervisor feedback,
          institutional review, or professional editorial judgment. Source
          verification depends on available reference metadata, uploaded
          sources, abstracts, or full text.
        </p>
      </section>
    </main>
  );
}
