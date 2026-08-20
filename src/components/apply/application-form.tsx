"use client";

import { useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { createOwnApplicant } from "@/app/apply/actions";
import { DocumentUploadStep, type RequiredDocType } from "./document-upload-step";

const FIELD =
  "mt-1 w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-slate-500 focus:ring-1 focus:ring-slate-500 focus:outline-none";
const LABEL = "block text-sm font-medium text-slate-700";

const STEPS = [
  "Persönliche Daten",
  "Wohnungssuche",
  "Haushalt",
  "Einkommen",
  "Aufenthaltsstatus",
  "Dokumente",
] as const;

const REQUIRED_DOC_TYPES: RequiredDocType[] = [
  { key: "schufa", label: "Schufa-Auskunft" },
  { key: "einkommensnachweis", label: "Lohn-/Gehaltsabrechnung" },
  { key: "ausweis", label: "Personalausweis" },
];

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className={LABEL}>
      {label}
      {children}
    </label>
  );
}

export function ApplicationForm({ defaultEmail }: { defaultEmail: string }) {
  const [step, setStep] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [applicantId, setApplicantId] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const formRef = useRef<HTMLFormElement>(null);
  const router = useRouter();

  const isDataStep = step < STEPS.length - 1;
  const isLastDataStep = step === STEPS.length - 2;

  function next() {
    setError(null);
    setStep((s) => Math.min(s + 1, STEPS.length - 1));
  }
  function back() {
    setError(null);
    setStep((s) => Math.max(s - 1, 0));
  }

  function handleSubmitData() {
    if (!formRef.current) return;
    const formData = new FormData(formRef.current);
    startTransition(async () => {
      const result = await createOwnApplicant(formData);
      if (result.error) {
        setError(result.error);
        return;
      }
      setApplicantId(result.id ?? null);
      setStep(STEPS.length - 1);
    });
  }

  return (
    <div className="mx-auto w-full max-w-xl">
      <ol className="mb-8 flex items-center justify-between text-xs text-slate-400">
        {STEPS.map((label, i) => (
          <li
            key={label}
            className={`flex-1 border-t-2 pt-2 text-center ${
              i <= step ? "border-slate-900 text-slate-900" : "border-slate-200"
            }`}
          >
            {label}
          </li>
        ))}
      </ol>

      {isDataStep ? (
        <form
          ref={formRef}
          onSubmit={(e) => {
            e.preventDefault();
            if (isLastDataStep) handleSubmitData();
            else next();
          }}
          className="space-y-6"
        >
          <input type="hidden" name="email" value={defaultEmail} />

          <div className={step === 0 ? "space-y-4" : "hidden"}>
            <Field label="Vorname *">
              <input name="first_name" required={step === 0} className={FIELD} />
            </Field>
            <Field label="Nachname *">
              <input name="last_name" required={step === 0} className={FIELD} />
            </Field>
            <Field label="Telefonnummer">
              <input name="phone" className={FIELD} />
            </Field>
            <Field label="Aktuelle Adresse">
              <input name="current_address" className={FIELD} />
            </Field>
            <Field label="Gewünschte Kontaktart">
              <select name="preferred_contact" defaultValue="" className={FIELD}>
                <option value="">–</option>
                <option value="email">E-Mail</option>
                <option value="telefon">Telefon</option>
                <option value="telegram">Telegram</option>
              </select>
            </Field>
          </div>

          <div className={step === 1 ? "space-y-4" : "hidden"}>
            <Field label="Gewünschter Ort">
              <input name="desired_city" className={FIELD} />
            </Field>
            <Field label="Gewünschte Stadtteile (Komma-getrennt)">
              <input name="desired_districts" className={FIELD} />
            </Field>
            <Field label="Anzahl Personen">
              <input name="num_persons" type="number" min={0} className={FIELD} />
            </Field>
            <Field label="davon Erwachsene">
              <input name="num_adults" type="number" min={0} className={FIELD} />
            </Field>
            <Field label="davon Kinder">
              <input name="num_children" type="number" min={0} className={FIELD} />
            </Field>
            <Field label="Gewünschte Zimmeranzahl (mind.)">
              <input name="desired_rooms_min" type="number" step="0.5" min={0} className={FIELD} />
            </Field>
            <Field label="Mindestfläche (m²)">
              <input name="desired_area_min" type="number" min={0} className={FIELD} />
            </Field>
            <Field label="Höchstfläche (m²)">
              <input name="desired_area_max" type="number" min={0} className={FIELD} />
            </Field>
            <Field label="Maximale Kaltmiete (€)">
              <input name="max_cold_rent" type="number" min={0} className={FIELD} />
            </Field>
            <Field label="Maximale Warmmiete (€)">
              <input name="max_warm_rent" type="number" min={0} className={FIELD} />
            </Field>
            <Field label="Gewünschter Einzugstermin">
              <input name="desired_move_in" type="date" className={FIELD} />
            </Field>
          </div>

          <div className={step === 2 ? "space-y-4" : "hidden"}>
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input type="checkbox" name="has_pets" /> Haustiere
            </label>
            <Field label="Art des Haustiers">
              <input name="pet_type" className={FIELD} />
            </Field>
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input type="checkbox" name="smoker" /> Raucher im Haushalt
            </label>
            <Field label="Besondere Anforderungen">
              <textarea name="special_requirements" rows={3} className={FIELD} />
            </Field>
          </div>

          <div className={step === 3 ? "space-y-4" : "hidden"}>
            <Field label="Monatliches Haushaltsnettoeinkommen (€)">
              <input name="household_net_income" type="number" min={0} className={FIELD} />
            </Field>
            <Field label="Anzahl Einkommensbezieher">
              <input name="num_income_earners" type="number" min={0} className={FIELD} />
            </Field>
            <Field label="Beschäftigungsstatus">
              <select name="employment_status" defaultValue="" className={FIELD}>
                <option value="">–</option>
                <option value="angestellt">Angestellt</option>
                <option value="selbststaendig">Selbstständig</option>
                <option value="ausbildung">Ausbildung</option>
                <option value="studium">Studium</option>
                <option value="rente">Rente</option>
                <option value="sonstige">Sonstige</option>
              </select>
            </Field>
            <Field label="Art der Beschäftigung">
              <select name="employment_type" defaultValue="" className={FIELD}>
                <option value="">–</option>
                <option value="unbefristet">Unbefristet</option>
                <option value="befristet">Befristet</option>
                <option value="probezeit">Probezeit</option>
                <option value="sonstige">Sonstige</option>
              </select>
            </Field>
            <Field label="Sonstige Einkünfte">
              <input name="other_income" className={FIELD} />
            </Field>
          </div>

          <div className={step === 4 ? "space-y-4" : "hidden"}>
            <p className="text-sm text-slate-500">
              Diese Angabe dient ausschließlich internen Zwecken und führt zu keiner automatischen
              Ablehnung.
            </p>
            <Field label="Aufenthaltsstatus">
              <select name="residence_status" defaultValue="" className={FIELD}>
                <option value="">–</option>
                <option value="deutsche_staatsangehoerigkeit">Deutsche Staatsangehörigkeit</option>
                <option value="eu_aufenthaltsstatus">EU-Aufenthaltsstatus</option>
                <option value="befristeter_aufenthaltstitel">Befristeter Aufenthaltstitel</option>
                <option value="unbefristeter_aufenthaltstitel">Unbefristeter Aufenthaltstitel</option>
                <option value="sonstiger_status">Sonstiger Status</option>
              </select>
            </Field>
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <div className="flex items-center justify-between pt-2">
            <button
              type="button"
              onClick={back}
              disabled={step === 0}
              className="rounded-lg px-4 py-2 text-sm font-medium text-slate-500 disabled:opacity-0"
            >
              Zurück
            </button>
            <button
              type="submit"
              disabled={pending}
              className="rounded-lg bg-slate-900 px-6 py-2.5 text-sm font-medium text-white transition hover:bg-slate-700 disabled:opacity-60"
            >
              {pending ? "Wird gespeichert…" : isLastDataStep ? "Profil absenden" : "Weiter"}
            </button>
          </div>
        </form>
      ) : (
        <DocumentUploadStep
          applicantId={applicantId}
          requiredTypes={REQUIRED_DOC_TYPES}
          onFinish={() => router.push("/portal")}
        />
      )}
    </div>
  );
}
