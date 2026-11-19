import { readFileSync } from "node:fs";
import { PNG } from "pngjs";
import { describe, expect, it } from "vitest";
import { decodeQr } from "../src/qr/decodeFrame";

const load = (name: string) => {
  const png = PNG.sync.read(readFileSync(new URL(`./fixtures/${name}`, import.meta.url)));
  return { data: new Uint8ClampedArray(png.data), width: png.width, height: png.height };
};

describe("browser QR decoding of real QR images (generated with the qrcode package)", () => {
  for (const name of ["normal", "no-margin", "small-modules", "transparent", "inverted", "small-on-page"]) {
    it(`decodes ${name}.png`, () => {
      const f = load(`${name}.png`);
      expect(decodeQr(f.data, f.width, f.height)).toBe("https://example.com");
    });
  }
  it("returns null for an image with no QR code", () => {
    const f = load("blank.png");
    expect(decodeQr(f.data, f.width, f.height)).toBeNull();
  });
});
