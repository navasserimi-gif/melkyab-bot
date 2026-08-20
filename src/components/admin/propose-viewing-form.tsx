"use client";

import { useState, useTransition } from "react";
import { proposeViewingTime } from "@/app/admin/viewings/actions";

export function ProposeViewingForm({ viewingId }: { viewingId: string }) {
  const [value, setValue] = useState("");
  const [message, setMessage] = useState<{ type: "ok" | "error"; text: string } | null>(null);
  const [pending, startTransition] = useTransition();

  function handleSubmit() {
    if (!value) {
      setMessage({ type: "error", text: "Bitte Datum und Uhrzeit wählen." });
      return;
    }
    setMessage(null);
    const formData = new FormData();
    formData.set("scheduled_at", value);
    startTransition(async () => {
      const result = await proposeViewingTime(viewingId, formData);
      if (result.error) {
        setMessage({ type: "error", text: result.error });
        return;
      }
      setMessage({ type: "ok", text: "Termin vorgeschlagen." });
    });
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <input
        type="datetime-local"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        className="rounded-lg border border-slate-300 px-2 py-1.5 text-xs"
      />
      <button
        type="button"
        onClick={handleSubmit}
        disabled={pending}
        className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-700 disabled:opacity-60"
      >
        {pending ? "Sendet…" : "Termin vorschlagen"}
      </button>
      {message && (
        <span className={`text-xs ${message.type === "ok" ? "text-emerald-600" : "text-red-600"}`}>
          {message.text}
        </span>
      )}
    </div>
  );
}
