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
  const [fileNames, setFileNames] = useState<Record<string, string>>({});
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

  function handleFileChange(docTypeKey: string) {
    const input = fileInputs.current[docTypeKey];
    const file = input?.files?.[0];
    setFileNames((f) => ({ ...f, [docTypeKey]: file?.name ?? "" }));
    if (file) setErrors((e) => ({ ...e, [docTypeKey]: "" }));
  }

  function handleUpload(docTypeKey: string) {
    const input = fileInputs.current[docTypeKey];
    const file = input?.files?.[0];
    if (!file) {
      setErrors((e) => ({
        ...e,
        [docTypeKey]: "Bitte zuerst oben auf „Datei auswählen“ klicken und eine Datei wählen. / لطفاً ابتدا روی «انتخاب فایل» کلیک کنید.",
      }));
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
      setFileNames((f) => ({ ...f, [docTypeKey]: "" }));
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
          const fileName = fileNames[docType.key];
          const isPending = pendingKey === docType.key;

          return (
            <div
              key={docType.key}
              className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
            >
              <p className="text-sm font-medium text-slate-900">
                {isUploaded ? "✓ " : ""}
                {docType.label}
              </p>
              <p className="text-xs text-slate-400" dir="rtl" lang="fa">
                {fa}
              </p>
              {errors[docType.key] && (
                <p className="mt-1 text-xs text-red-600">{errors[docType.key]}</p>
              )}

              <div className="mt-3 flex flex-wrap items-center gap-3">
                <div className="flex items-center gap-2">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-slate-900 text-[10px] font-semibold text-white">
                    1
                  </span>
                  <label className="cursor-pointer rounded-lg border border-slate-400 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100">
                    Datei auswählen / انتخاب فایل
                    <input
                      ref={(el) => {
                        fileInputs.current[docType.key] = el;
                      }}
                      type="file"
                      accept="application/pdf,image/*"
                      onChange={() => handleFileChange(docType.key)}
                      className="hidden"
                    />
                  </label>
                  <span className="max-w-[10rem] truncate text-xs text-slate-500">
                    {fileName || "keine Datei / بدون فایل"}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-slate-900 text-[10px] font-semibold text-white">
                    2
                  </span>
                  <button
                    type="button"
                    onClick={() => handleUpload(docType.key)}
                    disabled={isPending || !fileName}
                    className="rounded-lg bg-slate-900 px-4 py-1.5 text-xs font-medium text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    {isPending
                      ? "Lädt… / در حال بارگذاری…"
                      : isUploaded
                        ? "Ersetzen / جایگزینی"
                        : "Hochladen / بارگذاری"}
                  </button>
                </div>
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
