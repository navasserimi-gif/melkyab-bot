"use client";

import { useState, useTransition } from "react";
import { confirmViewingTime } from "@/app/portal/offers/actions";

export function ViewingConfirm({
  viewingId,
  scheduledAt,
  confirmedAt,
}: {
  viewingId: string;
  scheduledAt: string;
  confirmedAt: string | null;
}) {
  const [confirmed, setConfirmed] = useState(!!confirmedAt);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  const formatted = new Date(scheduledAt).toLocaleString("de-DE", {
    dateStyle: "full",
    timeStyle: "short",
  });

  function handleConfirm() {
    setError(null);
    startTransition(async () => {
      const result = await confirmViewingTime(viewingId);
      if (result.error) {
        setError(result.error);
        return;
      }
      setConfirmed(true);
    });
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <p className="text-sm font-medium text-slate-900">Vorgeschlagener Besichtigungstermin</p>
      <p className="mt-1 text-sm text-slate-700">{formatted}</p>
      {confirmed ? (
        <p className="mt-3 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
          ✓ Termin bestätigt.
        </p>
      ) : (
        <div className="mt-3">
          <button
            type="button"
            onClick={handleConfirm}
            disabled={pending}
            className="rounded-lg bg-emerald-600 px-5 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-60"
          >
            {pending ? "Bestätigt…" : "Termin bestätigen"}
          </button>
          {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
        </div>
      )}
    </div>
  );
}
