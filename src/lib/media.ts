// KI-generierte Platzhalterbilder (Higgsfield). Bei Bedarf durch echte Fotos
// eigener Objekte ersetzen — einfach die URLs hier austauschen.
export const HERO_IMAGE_URL =
  "https://d8j0ntlcm91z4.cloudfront.net/user_3F34Sz8rfgnjbIR8HyASsrGpYKu/hf_20260820_200600_7c3b193c-e942-4be7-8015-19a14076d001.png";

export const AUTH_PANEL_IMAGE_URL =
  "https://d8j0ntlcm91z4.cloudfront.net/user_3F34Sz8rfgnjbIR8HyASsrGpYKu/hf_20260820_200600_3c760c87-40c3-4aa3-a76d-6358eb56da8d.png";

export const PEOPLE_IMAGE_URL =
  "https://d8j0ntlcm91z4.cloudfront.net/user_3F34Sz8rfgnjbIR8HyASsrGpYKu/hf_20260820_204622_35d768ca-3ecf-4e56-bc83-9ca958cb3d5c.png";

export const HANDOVER_IMAGE_URL =
  "https://d8j0ntlcm91z4.cloudfront.net/user_3F34Sz8rfgnjbIR8HyASsrGpYKu/hf_20260820_204644_f3465743-a865-4477-a416-47718e737f1c.png";

export const DASHBOARD_3D_IMAGE_URL =
  "https://d8j0ntlcm91z4.cloudfront.net/user_3F34Sz8rfgnjbIR8HyASsrGpYKu/hf_20260820_205259_2518c267-86c9-4751-8719-acc6618282f6.png";

/** Themen-Hintergrund je Admin-Bereich (Pfad-Präfix -> Bild + Deckkraft).
 * Dezent im Layout eingeblendet, Inhalt liegt immer auf deckenden weißen
 * Karten. Der 3D-Look auf dem Dashboard verträgt etwas mehr Deckkraft als
 * die Foto-Hintergründe der übrigen Bereiche. */
export const ADMIN_SECTION_BACKGROUNDS: { prefix: string; url: string; opacity?: number }[] = [
  { prefix: "/admin/dashboard", url: DASHBOARD_3D_IMAGE_URL, opacity: 0.28 },
  { prefix: "/admin/applicants", url: PEOPLE_IMAGE_URL },
  { prefix: "/admin/properties", url: HERO_IMAGE_URL },
  { prefix: "/admin/viewings", url: HANDOVER_IMAGE_URL },
];
