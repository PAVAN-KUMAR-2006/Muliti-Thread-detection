import { readFileSync } from "node:fs";
import { renderToString } from "react-dom/server";
import { StaticRouter } from "react-router-dom/server";
import { describe, expect, it } from "vitest";
import { ResultView } from "../src/pages/Scanner";

// A real response body captured from POST /api/scan/website on the running backend (scores came from a throwaway test
// model, so this checks that the page renders a genuine API response, not that the classification is meaningful).
const real = JSON.parse(readFileSync(new URL("./fixtures/website_scan.json", import.meta.url), "utf8"));
const html = (r: unknown) => renderToString(<StaticRouter location="/scan/website"><ResultView r={r as never} /></StaticRouter>);

describe("website scan result page", () => {
  it("renders a real API response", () => {
    const out = html(real);
    expect(out).toContain(real.label === "Safe" ? "NO THREAT DETECTED" : `${String(real.label).toUpperCase()} DETECTED`);
    expect(out).toContain(real.details.host);
    expect(out).toContain("URL characteristics");
    expect(out).toContain(`/history/${real.id}`);
  });
  it("does not crash on older or partial responses", () => {
    expect(() => html({ ...real, details: undefined })).not.toThrow();
    expect(() => html({ ...real, details: {} })).not.toThrow();
    expect(() => html({ ...real, confidence: null, indicators: [], protective: [] })).not.toThrow();
  });
});
