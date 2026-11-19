import jsQR from "jsqr";

/** Decode a QR code from raw RGBA pixels. Returns null when no readable code is found. */
export function decodeImageData(data: Uint8ClampedArray, width: number, height: number): string | null {
  const result = jsQR(data, width, height, { inversionAttempts: "attemptBoth" });
  return result && result.data ? result.data : null;
}

/** Composite RGBA pixels onto white (a transparent background must not become black) and add a white margin. */
export function flattenOnWhite(data: Uint8ClampedArray, width: number, height: number, pad: number) {
  const w = width + 2 * pad;
  const h = height + 2 * pad;
  const out = new Uint8ClampedArray(w * h * 4).fill(255);
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const s = (y * width + x) * 4;
      const d = ((y + pad) * w + (x + pad)) * 4;
      const a = data[s + 3] / 255;
      out[d] = data[s] * a + 255 * (1 - a);
      out[d + 1] = data[s + 1] * a + 255 * (1 - a);
      out[d + 2] = data[s + 2] * a + 255 * (1 - a);
    }
  }
  return { data: out, width: w, height: h };
}

/** Try the image as it is, then with an added white quiet zone (tightly cropped codes have none). */
export function decodeQr(data: Uint8ClampedArray, width: number, height: number): string | null {
  for (const pad of [0, Math.max(16, Math.round(Math.min(width, height) * 0.15))]) {
    const flat = flattenOnWhite(data, width, height, pad);
    const text = decodeImageData(flat.data, flat.width, flat.height);
    if (text) return text;
  }
  return null;
}

/** Decode a QR code from an image file, entirely in the browser. Nothing is uploaded and no link is opened. */
export async function decodeImageFile(file: Blob): Promise<string | null> {
  const bitmap = await createImageBitmap(file);
  try {
    const longest = Math.max(bitmap.width, bitmap.height);
    const scale = longest < 400 ? 400 / longest : Math.min(1, 1600 / longest);
    const w = Math.max(1, Math.round(bitmap.width * scale));
    const h = Math.max(1, Math.round(bitmap.height * scale));
    const canvas = document.createElement("canvas");
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    if (!ctx) return null;
    ctx.imageSmoothingEnabled = scale < 1; // enlarging a tiny code: keep the modules sharp
    ctx.drawImage(bitmap, 0, 0, w, h);
    return decodeQr(ctx.getImageData(0, 0, w, h).data, w, h);
  } finally {
    bitmap.close();
  }
}
