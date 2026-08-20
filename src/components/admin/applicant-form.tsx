"use client";

import { useState } from "react";
import type { Applicant, StatusDefinition } from "@/types/models";

const FIELD =
  "mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:ring-1 focus:ring-slate-500 focus:outline-none";
const LABEL = "block text-sm font-medium text-slate-700";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <fieldset className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <legend className="px-1 text-sm font-semibold text-slate-900">{title}</legend>
      <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2">{children}</div>
    </fieldset>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className={LABEL}>
      {label}
      {children}
    </label>
  );
}

export function ApplicantForm({
  applicant,
  statusOptions,
  action,
}: {
  applicant?: Applicant;
  statusOptions: StatusDefinition[];
  action: (formData: FormData) => void;
}) {
  const [pending, setPending] = useState(false);
  const a = applicant;

  return (
    <form
      action={action}
      onSubmit={() => setPending(true)}
      className="space-y-6"
    >
      <Section title="Persönliche Daten">
        <Field label="Vorname *">
          <input name="first_name" defaultValue={a?.first_name} required className={FIELD} />
        </Field>
        <Field label="Nachname *">
          <input name="last_name" defaultValue={a?.last_name} required className={FIELD} />
        </Field>
        <Field label="E-Mail">
          <input name="email" type="email" defaultValue={a?.email ?? ""} className={FIELD} />
        </Field>
        <Field label="Telefonnummer">
          <input name="phone" defaultValue={a?.phone ?? ""} className={FIELD} />
        </Field>
        <Field label="Aktuelle Adresse">
          <input name="current_address" defaultValue={a?.current_address ?? ""} className={FIELD} />
        </Field>
        <Field label="Gewünschte Kontaktart">
          <select name="preferred_contact" defaultValue={a?.preferred_contact ?? ""} className={FIELD}>
            <option value="">–</option>
            <option value="email">E-Mail</option>
            <option value="telefon">Telefon</option>
            <option value="telegram">Telegram</option>
          </select>
        </Field>
        <Field label="Status">
          <select name="status_key" defaultValue={a?.status_key ?? "neu"} className={FIELD}>
            {statusOptions.map((s) => (
              <option key={s.key} value={s.key}>
                {s.label}
              </option>
            ))}
          </select>
        </Field>
      </Section>

      <Section title="Wohnungssuche">
        <Field label="Gewünschter Ort">
          <input name="desired_city" defaultValue={a?.desired_city ?? ""} className={FIELD} />
        </Field>
        <Field label="Gewünschte Stadtteile (Komma-getrennt)">
          <input
            name="desired_districts"
            defaultValue={a?.desired_districts?.join(", ") ?? ""}
            className={FIELD}
          />
        </Field>
        <Field label="Anzahl Personen">
          <input name="num_persons" type="number" min={0} defaultValue={a?.num_persons ?? ""} className={FIELD} />
        </Field>
        <Field label="davon Erwachsene">
          <input name="num_adults" type="number" min={0} defaultValue={a?.num_adults ?? ""} className={FIELD} />
        </Field>
        <Field label="davon Kinder">
          <input name="num_children" type="number" min={0} defaultValue={a?.num_children ?? ""} className={FIELD} />
        </Field>
        <Field label="Gewünschte Zimmeranzahl (mind.)">
          <input
            name="desired_rooms_min"
            type="number"
            step="0.5"
            min={0}
            defaultValue={a?.desired_rooms_min ?? ""}
            className={FIELD}
          />
        </Field>
        <Field label="Mindestfläche (m²)">
          <input
            name="desired_area_min"
            type="number"
            min={0}
            defaultValue={a?.desired_area_min ?? ""}
            className={FIELD}
          />
        </Field>
        <Field label="Höchstfläche (m²)">
          <input
            name="desired_area_max"
            type="number"
            min={0}
            defaultValue={a?.desired_area_max ?? ""}
            className={FIELD}
          />
        </Field>
        <Field label="Maximale Kaltmiete (€)">
          <input
            name="max_cold_rent"
            type="number"
            min={0}
            defaultValue={a?.max_cold_rent ?? ""}
            className={FIELD}
          />
        </Field>
        <Field label="Maximale Warmmiete (€)">
          <input
            name="max_warm_rent"
            type="number"
            min={0}
            defaultValue={a?.max_warm_rent ?? ""}
            className={FIELD}
          />
        </Field>
        <Field label="Gewünschter Einzugstermin">
          <input name="desired_move_in" type="date" defaultValue={a?.desired_move_in ?? ""} className={FIELD} />
        </Field>
      </Section>

      <Section title="Haushalt">
        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input type="checkbox" name="has_pets" defaultChecked={a?.has_pets} />
          Haustiere
        </label>
        <Field label="Art des Haustiers">
          <input name="pet_type" defaultValue={a?.pet_type ?? ""} className={FIELD} />
        </Field>
        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input type="checkbox" name="smoker" defaultChecked={a?.smoker} />
          Raucher im Haushalt
        </label>
        <Field label="Besondere Anforderungen">
          <textarea name="special_requirements" defaultValue={a?.special_requirements ?? ""} rows={2} className={FIELD} />
        </Field>
      </Section>

      <Section title="Einkommen & Beschäftigung">
        <Field label="Monatliches Haushaltsnettoeinkommen (€)">
          <input
            name="household_net_income"
            type="number"
            min={0}
            defaultValue={a?.household_net_income ?? ""}
            className={FIELD}
          />
        </Field>
        <Field label="Anzahl Einkommensbezieher">
          <input
            name="num_income_earners"
            type="number"
            min={0}
            defaultValue={a?.num_income_earners ?? ""}
            className={FIELD}
          />
        </Field>
        <Field label="Beschäftigungsstatus">
          <select name="employment_status" defaultValue={a?.employment_status ?? ""} className={FIELD}>
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
          <select name="employment_type" defaultValue={a?.employment_type ?? ""} className={FIELD}>
            <option value="">–</option>
            <option value="unbefristet">Unbefristet</option>
            <option value="befristet">Befristet</option>
            <option value="probezeit">Probezeit</option>
            <option value="sonstige">Sonstige</option>
          </select>
        </Field>
        <Field label="Sonstige Einkünfte">
          <input name="other_income" defaultValue={a?.other_income ?? ""} className={FIELD} />
        </Field>
      </Section>

      <Section title="Bewerbungsinformationen">
        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input type="checkbox" name="has_schufa" defaultChecked={a?.has_schufa} />
          Schufa-Nachweis vorhanden
        </label>
        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input type="checkbox" name="has_income_proof" defaultChecked={a?.has_income_proof} />
          Einkommensnachweise vorhanden
        </label>
        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input type="checkbox" name="has_debt_clearance_cert" defaultChecked={a?.has_debt_clearance_cert} />
          Mietschuldenfreiheitsbescheinigung vorhanden
        </label>
        <Field label="Weitere Nachweise (Notiz)">
          <input name="further_documents_note" defaultValue={a?.further_documents_note ?? ""} className={FIELD} />
        </Field>
      </Section>

      <Section title="Aufenthaltsstatus">
        <Field label="Angabe (neutral, kein automatisches Ausschlusskriterium)">
          <select name="residence_status" defaultValue={a?.residence_status ?? ""} className={FIELD}>
            <option value="">–</option>
            <option value="deutsche_staatsangehoerigkeit">Deutsche Staatsangehörigkeit</option>
            <option value="eu_aufenthaltsstatus">EU-Aufenthaltsstatus</option>
            <option value="befristeter_aufenthaltstitel">Befristeter Aufenthaltstitel</option>
            <option value="unbefristeter_aufenthaltstitel">Unbefristeter Aufenthaltstitel</option>
            <option value="sonstiger_status">Sonstiger Status</option>
          </select>
        </Field>
      </Section>

      <Section title="Interne Notizen">
        <div className="sm:col-span-2">
          <textarea name="internal_notes" defaultValue={a?.internal_notes ?? ""} rows={3} className={FIELD} />
        </div>
      </Section>

      <div className="flex justify-end gap-3">
        <button
          type="submit"
          disabled={pending}
          className="rounded-lg bg-slate-900 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-slate-700 disabled:opacity-60"
        >
          {pending ? "Speichern…" : a ? "Änderungen speichern" : "Interessent anlegen"}
        </button>
      </div>
    </form>
  );
}
