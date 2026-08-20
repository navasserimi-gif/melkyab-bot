/**
 * Verkleinert Bilddateien im Browser, bevor sie hochgeladen werden, damit der
 * Supabase-Speicher bei vielen Kunden/Wohnungen nicht unnötig vollläuft.
 * PDFs und bereits kleine Dateien bleiben unverändert.
 */
export async function compressImageFile(
  file: File,
  { maxDimension = 1600, quality = 0.8, skipBelowBytes = 300 * 1024 }: {
    maxDimension?: number;
    quality?: number;
    skipBelowBytes?: number;
  } = {},
): Promise<File> {
  if (!file.type.startsWith("image/") || file.type === "image/svg+xml") return file;
  if (file.size <= skipBelowBytes) return file;

  const bitmap = await createImageBitmap(file).catch(() => null);
  if (!bitmap) return file;

  const scale = Math.min(1, maxDimension / Math.max(bitmap.width, bitmap.height));
  const width = Math.round(bitmap.width * scale);
  const height = Math.round(bitmap.height * scale);

  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  if (!ctx) return file;
  ctx.drawImage(bitmap, 0, 0, width, height);

  const blob: Blob | null = await new Promise((resolve) =>
    canvas.toBlob(resolve, "image/jpeg", quality),
  );
  if (!blob || blob.size >= file.size) return file;

  const newName = file.name.replace(/\.\w+$/, "") + ".jpg";
  return new File([blob], newName, { type: "image/jpeg" });
}
