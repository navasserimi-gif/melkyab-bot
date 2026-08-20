"use client";

import { useRef, useState, useTransition } from "react";
import { uploadApplicantDocument } from "@/lib/actions/applicant-documents";
import { Bilingual, DOC_TYPE_FA } from "./bilingual";

export interface RequiredDocType {
  key: string;
  label: string;
  labelFa?: string;
}

export function DocumentUploadStep({
  applicantId,
  requiredTypes,
  uploadedKeys = [],
  onFinish,
  finishLabel = "Fertig — zum Portal",
  finishLabelFa = "پایان — به پورتال",
}: {
  applicantId: string | null;
  requiredTypes: RequiredDocType[];
  uploadedKeys?: string[];
  onFinish?: () => void;
  finishLabel?: string;
  finishLabelFa?: string;
}) {
  const [uploaded, setUploaded] = useState<Set<string>>(new Set(uploadedKeys));
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [pendingKey, setPendingKey] = useState<string | null>(null);
  const [, startTransition] = useTransition();
  const fileInputs = useRef<Record<string, HTMLInputElement | null>>({});

  if (!applicantId) {
    return (
      <p className="text-sm text-red-600">
        Dein Profil konnte nicht gefunden werden. Bitte lade die Seite neu.
        <span className="mt-1 block" dir="rtl" lang="fa">
          پروفایل شما یافت نشد. لطفاً صفحه را دوباره بارگذاری کنید.
        </span>
      </p>
    );
  }

  function handleUpload(docTypeKey: string) {
    const input = fileInputs.current[docTypeKey];
    const file = input?.files?.[0];
    if (!file) {
      setErrors((e) => ({ ...e, [docTypeKey]: "Bitte zuerst eine Datei auswählen. / لطفاً ابتدا یک فایل انتخاب کنید." }));
      return;
    }
    setErrors((e) => ({ ...e, [docTypeKey]: "" }));
    setPendingKey(docTypeKey);

    const formData = new FormData();
    formData.set("applicant_id", applicantId as string);
    formData.set("doc_type_key", docTypeKey);
    formData.set("file", file);

    startTransition(async () => {
      const result = await uploadApplicantDocument(formData);
      setPendingKey(null);
      if (result.error) {
        setErrors((e) => ({ ...e, [docTypeKey]: result.error! }));
        return;
      }
      setUploaded((prev) => new Set(prev).add(docTypeKey));
      if (input) input.value = "";
    });
  }

  return (
    <div className="space-y-6">
      <p className="text-sm text-slate-500">
        Bitte lade folgende Unterlagen hoch. Deine Dokumente werden sicher und ausschließlich für
        die Bearbeitung deiner Bewerbung gespeichert — niemals öffentlich einsehbar.
        <span className="mt-1 block" dir="rtl" lang="fa">
          لطفاً مدارک زیر را بارگذاری کنید. مدارک شما به‌صورت امن و فقط برای بررسی درخواست شما
          ذخیره می‌شود — هرگز به‌صورت عمومی قابل مشاهده نیست.
        </span>
      </p>

      <div className="space-y-4">
        {requiredTypes.map((docType) => {
          const isUploaded = uploaded.has(docType.key);
          const fa = docType.labelFa ?? DOC_TYPE_FA[docType.key] ?? docType.label;
          return (
            <div
              key={docType.key}
              className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
            >
              <div>
                <p className="text-sm font-medium text-slate-900">
                  {isUploaded ? "✓ " : ""}
                  {docType.label}
                </p>
                <p className="text-xs text-slate-400" dir="rtl" lang="fa">
                  {fa}
                </p>
                {errors[docType.key] && (
                  <p className="text-xs text-red-600">{errors[docType.key]}</p>
                )}
              </div>
              <div className="flex items-center gap-2">
                <input
                  ref={(el) => {
                    fileInputs.current[docType.key] = el;
                  }}
                  type="file"
                  accept="application/pdf,image/*"
                  className="text-xs"
                />
                <button
                  type="button"
                  onClick={() => handleUpload(docType.key)}
                  disabled={pendingKey === docType.key}
                  className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60"
                >
                  {pendingKey === docType.key
                    ? "Lädt… / در حال بارگذاری…"
                    : isUploaded
                      ? "Ersetzen / جایگزینی"
                      : "Hochladen / بارگذاری"}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {onFinish && (
        <div className="flex justify-end pt-2">
          <button
            type="button"
            onClick={onFinish}
            className="rounded-lg bg-slate-900 px-6 py-2.5 text-sm font-medium text-white transition hover:bg-slate-700"
          >
            <Bilingual de={finishLabel} fa={finishLabelFa} />
          </button>
        </div>
      )}
    </div>
  );
}
