"use client";

import { useState, useTransition } from "react";
import { sendPropertyOffer } from "@/app/admin/properties/actions";

export interface PropertyOption {
  id: string;
  internal_code: string;
  object_name: string | null;
  city: string | null;
}

export function SendOfferFromApplicantForm({
  applicantId,
  properties,
  alreadySentFor,
}: {
  applicantId: string;
  properties: PropertyOption[];
  alreadySentFor: string[];
}) {
  const [propertyId, setPropertyId] = useState("");
  const [message, setMessage] = useState<{ type: "ok" | "error"; text: string } | null>(null);
  const [pending, startTransition] = useTransition();
  const sentSet = new Set(alreadySentFor);

  function handleSend() {
    if (!propertyId) {
      setMessage({ type: "error", text: "Bitte eine Wohnung auswählen." });
      return;
    }
    setMessage(null);
    const formData = new FormData();
    formData.set("applicant_id", applicantId);
    startTransition(async () => {
      const result = await sendPropertyOffer(propertyId, formData);
      if (result.error) {
        setMessage({ type: "error", text: result.error });
        return;
      }
      setMessage({ type: "ok", text: "Exposé wurde gesendet." });
      setPropertyId("");
    });
  }

  return (
    <div className="flex flex-wrap items-end gap-3">
      <div>
        <label className="block text-sm font-medium text-slate-700">Wohnung</label>
        <select
          value={propertyId}
          onChange={(e) => setPropertyId(e.target.value)}
          className="mt-1 min-w-[16rem] rounded-lg border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="">– auswählen –</option>
          {properties.map((p) => (
            <option key={p.id} value={p.id}>
              {p.internal_code} · {p.object_name ?? p.city ?? ""}
              {sentSet.has(p.id) ? " (bereits gesendet)" : ""}
            </option>
          ))}
        </select>
      </div>
      <button
        type="button"
        onClick={handleSend}
        disabled={pending}
        className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-60"
      >
        {pending ? "Wird gesendet…" : "Exposé senden"}
      </button>
      {message && (
        <p className={`text-sm ${message.type === "ok" ? "text-emerald-600" : "text-red-600"}`}>
          {message.text}
        </p>
      )}
    </div>
  );
}
