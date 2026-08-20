"use client";

import { useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { createOwnApplicant } from "@/app/apply/actions";
import { DocumentUploadStep, type RequiredDocType } from "./document-upload-step";
import { Bilingual } from "./bilingual";

const FIELD =
  "mt-1 w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-slate-500 focus:ring-1 focus:ring-slate-500 focus:outline-none";
const LABEL = "block text-sm font-medium text-slate-700";

const STEPS = [
  { de: "Persönliche Daten", fa: "اطلاعات شخصی" },
  { de: "Wohnungssuche", fa: "جستجوی مسکن" },
  { de: "Haushalt", fa: "خانوار" },
  { de: "Einkommen", fa: "درآمد" },
  { de: "Aufenthaltsstatus", fa: "وضعیت اقامت" },
  { de: "Dokumente", fa: "مدارک" },
] as const;

const REQUIRED_DOC_TYPES: RequiredDocType[] = [
  { key: "schufa", label: "Schufa-Auskunft", labelFa: "گزارش اعتباری (Schufa)" },
  { key: "einkommensnachweis", label: "Lohn-/Gehaltsabrechnung", labelFa: "فیش حقوقی" },
  { key: "ausweis", label: "Personalausweis", labelFa: "کارت شناسایی / پاسپورت" },
];

function Field({ de, fa, children }: { de: string; fa: string; children: React.ReactNode }) {
  return (
    <label className={LABEL}>
      <Bilingual de={de} fa={fa} />
      {children}
    </label>
  );
}

function Check({ name, de, fa }: { name: string; de: string; fa: string }) {
  return (
    <label className="flex items-center gap-2 text-sm text-slate-700">
      <input type="checkbox" name={name} />
      <Bilingual de={de} fa={fa} />
    </label>
  );
}

function BtnText({ de, fa }: { de: string; fa: string }) {
  return (
    <span className="flex flex-col items-center leading-tight">
      <span>{de}</span>
      <span className="text-[11px] opacity-80" dir="rtl" lang="fa">
        {fa}
      </span>
    </span>
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
      <ol className="mb-8 flex items-start justify-between text-center text-[11px] text-slate-400">
        {STEPS.map((s, i) => (
          <li
            key={s.de}
            className={`flex-1 border-t-2 pt-2 ${i <= step ? "border-slate-900 text-slate-900" : "border-slate-200"}`}
          >
            <span className="block">{s.de}</span>
            <span className="block" dir="rtl" lang="fa">
              {s.fa}
            </span>
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
            <Field de="Vorname *" fa="نام *">
              <input name="first_name" required={step === 0} className={FIELD} />
            </Field>
            <Field de="Nachname *" fa="نام خانوادگی *">
              <input name="last_name" required={step === 0} className={FIELD} />
            </Field>
            <Field de="Telefonnummer" fa="شماره تلفن">
              <input name="phone" className={FIELD} />
            </Field>
            <Field de="Aktuelle Adresse" fa="آدرس فعلی">
              <input name="current_address" className={FIELD} />
            </Field>
            <Field de="Gewünschte Kontaktart" fa="روش تماس ترجیحی">
              <select name="preferred_contact" defaultValue="" className={FIELD}>
                <option value="">–</option>
                <option value="email">E-Mail / ایمیل</option>
                <option value="telefon">Telefon / تلفن</option>
                <option value="telegram">Telegram / تلگرام</option>
              </select>
            </Field>
          </div>

          <div className={step === 1 ? "space-y-4" : "hidden"}>
            <Field de="Gewünschter Ort" fa="شهر مورد نظر">
              <input name="desired_city" className={FIELD} />
            </Field>
            <Field de="Gewünschte Stadtteile (Komma-getrennt)" fa="محله‌های مورد نظر (با کاما جدا شود)">
              <input name="desired_districts" className={FIELD} />
            </Field>
            <Field de="Anzahl Personen" fa="تعداد افراد">
              <input name="num_persons" type="number" min={0} className={FIELD} />
            </Field>
            <Field de="davon Erwachsene" fa="تعداد بزرگسالان">
              <input name="num_adults" type="number" min={0} className={FIELD} />
            </Field>
            <Field de="davon Kinder" fa="تعداد کودکان">
              <input name="num_children" type="number" min={0} className={FIELD} />
            </Field>
            <Field de="Gewünschte Zimmeranzahl (mind.)" fa="تعداد اتاق مورد نظر (حداقل)">
              <input name="desired_rooms_min" type="number" step="0.5" min={0} className={FIELD} />
            </Field>
            <Field de="Mindestfläche (m²)" fa="حداقل متراژ (متر مربع)">
              <input name="desired_area_min" type="number" min={0} className={FIELD} />
            </Field>
            <Field de="Höchstfläche (m²)" fa="حداکثر متراژ (متر مربع)">
              <input name="desired_area_max" type="number" min={0} className={FIELD} />
            </Field>
            <Field de="Maximale Warmmiete (€)" fa="حداکثر اجاره کل (یورو)">
              <input name="max_warm_rent" type="number" min={0} className={FIELD} />
            </Field>
            <Field de="Gewünschter Einzugstermin" fa="تاریخ مورد نظر برای اسکان">
              <input name="desired_move_in" type="date" className={FIELD} />
            </Field>
          </div>

          <div className={step === 2 ? "space-y-4" : "hidden"}>
            <Check name="has_pets" de="Haustiere" fa="حیوان خانگی" />
            <Field de="Art des Haustiers" fa="نوع حیوان خانگی">
              <input name="pet_type" className={FIELD} />
            </Field>
            <Check name="smoker" de="Raucher im Haushalt" fa="سیگاری در خانواده" />
            <Field de="Besondere Anforderungen" fa="نیازهای خاص">
              <textarea name="special_requirements" rows={3} className={FIELD} />
            </Field>
          </div>

          <div className={step === 3 ? "space-y-4" : "hidden"}>
            <Field de="Monatliches Haushaltsnettoeinkommen (€)" fa="درآمد خالص ماهانه خانوار (یورو)">
              <input name="household_net_income" type="number" min={0} className={FIELD} />
            </Field>
            <Field de="Anzahl Einkommensbezieher" fa="تعداد افراد دارای درآمد">
              <input name="num_income_earners" type="number" min={0} className={FIELD} />
            </Field>
            <Field de="Beschäftigungsstatus" fa="وضعیت شغلی">
              <select name="employment_status" defaultValue="" className={FIELD}>
                <option value="">–</option>
                <option value="angestellt">Angestellt / کارمند</option>
                <option value="selbststaendig">Selbstständig / خوداشتغال</option>
                <option value="ausbildung">Ausbildung / کارآموزی</option>
                <option value="studium">Studium / دانشجو</option>
                <option value="rente">Rente / بازنشسته</option>
                <option value="sonstige">Sonstige / سایر</option>
              </select>
            </Field>
            <Field de="Art der Beschäftigung" fa="نوع قرارداد شغلی">
              <select name="employment_type" defaultValue="" className={FIELD}>
                <option value="">–</option>
                <option value="unbefristet">Unbefristet / دائم</option>
                <option value="befristet">Befristet / موقت</option>
                <option value="probezeit">Probezeit / دوره آزمایشی</option>
                <option value="sonstige">Sonstige / سایر</option>
              </select>
            </Field>
            <Field de="Sonstige Einkünfte" fa="سایر منابع درآمد">
              <input name="other_income" className={FIELD} />
            </Field>
          </div>

          <div className={step === 4 ? "space-y-4" : "hidden"}>
            <p className="text-sm text-slate-500">
              Diese Angabe dient ausschließlich internen Zwecken und führt zu keiner automatischen
              Ablehnung.
              <span className="mt-1 block" dir="rtl" lang="fa">
                این اطلاعات صرفاً برای مقاصد داخلی استفاده می‌شود و منجر به رد خودکار درخواست
                نمی‌شود.
              </span>
            </p>
            <Field de="Aufenthaltsstatus" fa="وضعیت اقامت">
              <select name="residence_status" defaultValue="" className={FIELD}>
                <option value="">–</option>
                <option value="deutsche_staatsangehoerigkeit">
                  Deutsche Staatsangehörigkeit / تابعیت آلمانی
                </option>
                <option value="eu_aufenthaltsstatus">
                  EU-Aufenthaltsstatus / اقامت اتحادیه اروپا
                </option>
                <option value="befristeter_aufenthaltstitel">
                  Befristeter Aufenthaltstitel / اجازه اقامت موقت
                </option>
                <option value="unbefristeter_aufenthaltstitel">
                  Unbefristeter Aufenthaltstitel / اجازه اقامت دائم
                </option>
                <option value="sonstiger_status">Sonstiger Status / وضعیت دیگر</option>
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
              <BtnText de="Zurück" fa="بازگشت" />
            </button>
            <button
              type="submit"
              disabled={pending}
              className="rounded-lg bg-slate-900 px-6 py-2.5 text-sm font-medium text-white transition hover:bg-slate-700 disabled:opacity-60"
            >
              {pending ? (
                <BtnText de="Wird gespeichert…" fa="در حال ذخیره…" />
              ) : isLastDataStep ? (
                <BtnText de="Profil absenden" fa="ارسال پروفایل" />
              ) : (
                <BtnText de="Weiter" fa="بعدی" />
              )}
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
