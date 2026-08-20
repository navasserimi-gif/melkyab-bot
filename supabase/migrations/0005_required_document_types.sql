-- Nur Schufa, Einkommensnachweis und Ausweis sind für den Self-Service-Upload
-- (Formular + Portal) als "erforderlich" markiert; die übrigen Dokumenttypen
-- bleiben als optionale Kategorien bestehen (z. B. wenn Staff manuell weitere
-- Nachweise hochlädt).

update public.document_types set required = true where key in ('schufa', 'einkommensnachweis', 'ausweis');
update public.document_types set required = false where key in ('mietschuldenfreiheit', 'arbeitsvertrag', 'sonstiges');
