import { readFileSync } from "node:fs";
import { renderToString } from "react-dom/server";
import { StaticRouter } from "react-router-dom/server";
import { describe, expect, it } from "vitest";
import { PhoneResult } from "../src/pages/PhoneScanner";
import { validatePhoneInput } from "../src/phone/validate";

// Real responses captured from POST /api/phone/scan on the running backend (community reports created through the API).
const load = (n: string) => JSON.parse(readFileSync(new URL(`./fixtures/${n}`, import.meta.url), "utf8"));
const high = load("phone_scan_high.json");
const unknown = load("phone_scan_unknown.json");
const html = (r: unknown, report?: () => void) => renderToString(<StaticRouter location="/scan/phone"><PhoneResult r={r as never} onReport={report} /></StaticRouter>);

describe("phone input validation", () => {
  it.each([
    ["", "IN", "Enter a phone number."],
    ["   ", "IN", "Enter a phone number."],
    ["abc", "IN", "A phone number can contain only digits, spaces and the characters + ( ) - ."],
    ["12", "IN", "That is too short to be a phone number."],
    ["1".repeat(16), "IN", "That is too long to be a phone number."],
    ["98765 43210", "", "Choose a country, or start the number with + and its country code."],
  ])("rejects %j (region %j)", (raw, region, message) => expect(validatePhoneInput(raw, region)).toBe(message));
  it.each([["98765 43210", "IN"], ["+1 650 253 0000", ""], ["(650) 253-0000", "US"]])("accepts %j", (raw, region) => expect(validatePhoneInput(raw, region)).toBe(""));
});

describe("phone result page", () => {
  it("renders a scored, reported number", () => {
    const out = html(high, () => undefined);
    expect(out).toContain("HIGH RISK");
    expect(out).toContain(high.details.number_display);
    expect(out).toContain("Report this number");
    expect(out).toContain("Score breakdown");
    expect(out).toContain("Reports are submitted by Sentinel users and are not independently verified");
    expect(out).not.toContain("Caller 0 claimed");   // other users' descriptions are never in the response
  });
  it("renders an unknown number as not scored and not safe", () => {
    const out = html(unknown);
    expect(out).toContain("NO KNOWN THREAT");
    expect(out).toContain("Not scored");
    expect(out).toContain("does not mean it is safe");
    expect(out).not.toContain("Risk score");
    expect(out).not.toContain("Score breakdown");
  });
  it("does not crash on partial responses", () => {
    expect(() => html({ ...high, details: undefined })).not.toThrow();
    expect(() => html({ ...unknown, indicators: undefined })).not.toThrow();
  });
});
