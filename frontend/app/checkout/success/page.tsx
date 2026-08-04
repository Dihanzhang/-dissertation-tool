import Link from "next/link";

export default function CheckoutSuccessPage() {
  return (
    <main className="mx-auto min-h-screen max-w-xl px-6 py-16 text-slate-900">
      <p className="text-sm font-semibold uppercase tracking-wide text-blue-700">Submission Pass</p>
      <h1 className="mt-4 text-3xl font-bold">Payment received</h1>
      <p className="mt-4 text-slate-600">
        Your Submission Pass is being activated. This usually takes only a few seconds.
      </p>
      <Link href="/account" className="button-primary mt-8 rounded-md px-5 py-3 font-semibold">
        Go to my Submission Pass
      </Link>
    </main>
  );
}
