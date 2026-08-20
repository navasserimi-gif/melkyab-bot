"use client";

import { useState, useTransition } from "react";
import { sendPropertyOffer } from "@/app/admin/properties/actions";

export interface ApplicantOption {
  id: string;
  internal_code: string;
  first_name: string;
  last_name: string;
}

export function SendOfferForm({
  propertyId,
  applicants,
  alreadySentTo,
}: {
  propertyId: string;
  applicants: ApplicantOption[];
  alreadySentTo: string[];
}) {
  const [applicantId, setApplicantId] = useState("");
  const [message, setMessage] = useState<{ type: "ok" | "error"; text: string } | null>(null);
  const [pending, startTransition] = useTransition();
  const sentSet = new Set(alreadySentTo);

  function handleSend() {
    if (!applicantId) {
      setMessage({ type: "error", text: "Bitte einen Interessenten auswählen." });
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
      setApplicantId("");
    });
  }

  return (
    <div className="flex flex-wrap items-end gap-3">
      <div>
        <label className="block text-sm font-medium text-slate-700">Interessent</label>
        <select
          value={applicantId}
          onChange={(e) => setApplicantId(e.target.value)}
          className="mt-1 min-w-[16rem] rounded-lg border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="">– auswählen –</option>
          {applicants.map((a) => (
            <option key={a.id} value={a.id}>
              {a.internal_code} · {a.first_name} {a.last_name}
              {sentSet.has(a.id) ? " (bereits gesendet)" : ""}
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
