"use client";

import { useActionState } from "react";
import Link from "next/link";
import { register, type AuthFormState } from "../actions";
import { AuthShell } from "@/components/auth/auth-shell";

const initialState: AuthFormState = {};

export default function RegisterPage() {
  const [state, formAction, pending] = useActionState(register, initialState);

  return (
    <AuthShell>
      <div className="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-xl font-semibold text-slate-900">Konto erstellen</h1>
        <p className="mt-1 text-sm text-slate-500">
          Als Mietinteressent registrieren, um dein Profil anzulegen.
        </p>

        <form action={formAction} className="mt-6 space-y-4">
          <div>
            <label htmlFor="full_name" className="block text-sm font-medium text-slate-700">
              Vollständiger Name
            </label>
            <input
              id="full_name"
              name="full_name"
              type="text"
              required
              autoComplete="name"
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:ring-1 focus:ring-slate-500 focus:outline-none"
            />
          </div>
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-slate-700">
              E-Mail
            </label>
            <input
              id="email"
              name="email"
              type="email"
              required
              autoComplete="email"
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:ring-1 focus:ring-slate-500 focus:outline-none"
            />
          </div>
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-slate-700">
              Passwort
            </label>
            <input
              id="password"
              name="password"
              type="password"
              required
              minLength={8}
              autoComplete="new-password"
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:ring-1 focus:ring-slate-500 focus:outline-none"
            />
            <p className="mt-1 text-xs text-slate-400">Mindestens 8 Zeichen.</p>
          </div>

          {state.error && <p className="text-sm text-red-600">{state.error}</p>}

          <button
            type="submit"
            disabled={pending}
            className="w-full rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-slate-700 disabled:opacity-60"
          >
            {pending ? "Wird erstellt…" : "Konto erstellen"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-slate-500">
          Bereits registriert?{" "}
          <Link href="/login" className="font-medium text-slate-900 hover:underline">
            Anmelden
          </Link>
        </p>
      </div>
    </AuthShell>
  );
}
