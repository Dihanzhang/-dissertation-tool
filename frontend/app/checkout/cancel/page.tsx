import Link from "next/link";

export default function CheckoutCancelPage() {
  return (
    <main className="mx-auto min-h-screen max-w-xl px-6 py-16 text-slate-900">
      <p className="text-sm font-semibold uppercase tracking-wide text-blue-700">Submission Pass</p>
      <h1 className="mt-4 text-3xl font-bold">Checkout cancelled</h1>
      <p className="mt-4 text-slate-600">No payment was taken. You can return whenever you are ready.</p>
      <Link href="/account" className="button-primary mt-8 rounded-md px-5 py-3 font-semibold">
        Return to my account
      </Link>
    </main>
  );
}
