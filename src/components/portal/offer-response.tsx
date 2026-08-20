"use client";

import { useState, useTransition } from "react";
import { respondToOffer } from "@/app/portal/offers/actions";

const OPTIONS = [
  { value: "interesse", label: "Ich habe Interesse", style: "bg-emerald-600 hover:bg-emerald-500" },
  {
    value: "besichtigung_angefragt",
    label: "Besichtigung anfragen",
    style: "bg-slate-900 hover:bg-slate-700",
  },
  { value: "kein_interesse", label: "Kein Interesse", style: "bg-slate-200 text-slate-700 hover:bg-slate-300" },
] as const;

export function OfferResponse({
  offerId,
  currentResponse,
}: {
  offerId: string;
  currentResponse: string;
}) {
  const [response, setResponse] = useState(currentResponse);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  function handleRespond(value: (typeof OPTIONS)[number]["value"]) {
    setError(null);
    startTransition(async () => {
      const result = await respondToOffer(offerId, value);
      if (result.error) {
        setError(result.error);
        return;
      }
      setResponse(value);
    });
  }

  if (response !== "offen") {
    const label = OPTIONS.find((o) => o.value === response)?.label ?? response;
    return (
      <p className="rounded-lg bg-slate-100 px-4 py-3 text-sm font-medium text-slate-700">
        Deine Antwort: {label}
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-3">
        {OPTIONS.map((option) => (
          <button
            key={option.value}
            type="button"
            disabled={pending}
            onClick={() => handleRespond(option.value)}
            className={`rounded-lg px-5 py-2.5 text-sm font-medium text-white transition disabled:opacity-60 ${option.style}`}
          >
            {option.label}
          </button>
        ))}
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  );
}
