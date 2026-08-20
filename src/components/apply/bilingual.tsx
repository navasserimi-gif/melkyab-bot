export function Bilingual({ de, fa, className }: { de: string; fa: string; className?: string }) {
  return (
    <span className={className}>
      <span className="block">{de}</span>
      <span className="block text-xs text-slate-400" dir="rtl" lang="fa">
        {fa}
      </span>
    </span>
  );
}

/** Deutsch/Farsi für die admin-konfigurierbaren Dokumenttypen (§17). Fällt auf
 * das deutsche Label zurück, wenn ein Admin später einen neuen Typ ohne
 * Übersetzung anlegt. */
export const DOC_TYPE_FA: Record<string, string> = {
  einkommensnachweis: "فیش حقوقی / گواهی درآمد",
  schufa: "گزارش اعتباری (Schufa)",
  mietschuldenfreiheit: "گواهی نداشتن بدهی اجاره",
  arbeitsvertrag: "قرارداد کار",
  ausweis: "کارت شناسایی / پاسپورت",
  sonstiges: "سایر مدارک",
};
