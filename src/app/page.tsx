import Link from "next/link";

export default function LandingPage() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center px-6 py-24 text-center">
      <p className="mb-3 text-sm font-medium tracking-wide text-slate-500 uppercase">
        Mietwohnungs-CRM
      </p>
      <h1 className="max-w-2xl text-4xl font-semibold tracking-tight text-slate-900 sm:text-5xl">
        Vom Mietinteressenten bis zur Vergabe — alles an einem Ort.
      </h1>
      <p className="mt-6 max-w-xl text-lg text-slate-600">
        Interessenten erfassen, passende Wohnungen finden, Besichtigungen koordinieren und
        Unterlagen verwalten — automatisiert und sicher.
      </p>
      <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
        <Link
          href="/login"
          className="rounded-lg bg-slate-900 px-6 py-3 text-sm font-medium text-white shadow-sm transition hover:bg-slate-700"
        >
          Anmelden
        </Link>
        <Link
          href="/register"
          className="rounded-lg border border-slate-300 bg-white px-6 py-3 text-sm font-medium text-slate-900 shadow-sm transition hover:bg-slate-50"
        >
          Konto erstellen
        </Link>
      </div>
    </main>
  );
}
