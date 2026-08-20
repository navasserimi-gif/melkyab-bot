import Image from "next/image";
import Link from "next/link";
import { HERO_IMAGE_URL } from "@/lib/media";

const FEATURES = [
  {
    title: "Automatisches Matching",
    text: "Passende Wohnungen werden anhand von Ort, Budget, Zimmerzahl und mehr automatisch gefunden.",
    icon: (
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
      />
    ),
  },
  {
    title: "Sichere Unterlagen",
    text: "Schufa, Einkommensnachweis & Co. werden verschlüsselt gespeichert — nie öffentlich einsehbar.",
    icon: (
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M12 2.25 4.5 5.25v6c0 5.108 3.24 8.79 7.5 10.5 4.26-1.71 7.5-5.392 7.5-10.5v-6L12 2.25Z"
      />
    ),
  },
  {
    title: "Alles an einem Ort",
    text: "Interessenten, Wohnungen, Besichtigungen und Status-Verlauf in einem gemeinsamen Dashboard.",
    icon: (
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M3.75 6A2.25 2.25 0 0 1 6 3.75h3A2.25 2.25 0 0 1 11.25 6v3A2.25 2.25 0 0 1 9 11.25H6A2.25 2.25 0 0 1 3.75 9V6ZM3.75 15A2.25 2.25 0 0 1 6 12.75h3A2.25 2.25 0 0 1 11.25 15v3A2.25 2.25 0 0 1 9 20.25H6A2.25 2.25 0 0 1 3.75 18v-3ZM12.75 6A2.25 2.25 0 0 1 15 3.75h3A2.25 2.25 0 0 1 20.25 6v3A2.25 2.25 0 0 1 18 11.25h-3A2.25 2.25 0 0 1 12.75 9V6ZM12.75 15A2.25 2.25 0 0 1 15 12.75h3A2.25 2.25 0 0 1 20.25 15v3A2.25 2.25 0 0 1 18 20.25h-3A2.25 2.25 0 0 1 12.75 18v-3Z"
      />
    ),
  },
];

export default function LandingPage() {
  return (
    <main className="flex flex-1 flex-col">
      <section className="relative isolate flex min-h-[85vh] items-center overflow-hidden">
        <Image
          src={HERO_IMAGE_URL}
          alt="Modernes Wohngebäude"
          fill
          priority
          sizes="100vw"
          className="object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-slate-950/90 via-slate-950/70 to-slate-950/30" />
        <div className="relative z-10 mx-auto w-full max-w-6xl px-6 py-24">
          <p className="mb-3 text-sm font-semibold tracking-wide text-emerald-400 uppercase">
            Mietwohnungs-CRM
          </p>
          <h1 className="max-w-2xl text-4xl font-semibold tracking-tight text-white sm:text-5xl">
            Vom Mietinteressenten bis zur Vergabe — alles an einem Ort.
          </h1>
          <p className="mt-6 max-w-xl text-lg text-slate-200">
            Interessenten erfassen, passende Wohnungen finden, Besichtigungen koordinieren und
            Unterlagen verwalten — automatisiert und sicher.
          </p>
          <div className="mt-10 flex flex-wrap items-center gap-4">
            <Link
              href="/register"
              className="rounded-lg bg-white px-6 py-3 text-sm font-medium text-slate-900 shadow-sm transition hover:bg-slate-100"
            >
              Konto erstellen
            </Link>
            <Link
              href="/login"
              className="rounded-lg border border-white/40 px-6 py-3 text-sm font-medium text-white transition hover:bg-white/10"
            >
              Anmelden
            </Link>
          </div>
        </div>
      </section>

      <section className="mx-auto w-full max-w-6xl px-6 py-20">
        <div className="grid grid-cols-1 gap-8 sm:grid-cols-3">
          {FEATURES.map((feature) => (
            <div
              key={feature.title}
              className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
            >
              <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-emerald-50 text-emerald-600">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={1.5}
                  stroke="currentColor"
                  className="h-6 w-6"
                >
                  {feature.icon}
                </svg>
              </div>
              <h3 className="mt-4 text-base font-semibold text-slate-900">{feature.title}</h3>
              <p className="mt-2 text-sm text-slate-600">{feature.text}</p>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
