// Static check: every quick action points at a scanner page that exists. Run with: npm run check:actions
import { readFileSync } from "node:fs";
const read = (p) => readFileSync(new URL(`../${p}`, import.meta.url), "utf8");
const scanner = read("src/pages/Scanner.tsx"), app = read("src/App.tsx"), qa = read("src/components/QuickActions.tsx");
const kinds = [...scanner.slice(scanner.indexOf("const CFG")).matchAll(/^ {2}(\w+): \{ title:/gm)].map((m) => m[1]);
const links = [...qa.matchAll(/to: "\/scan\/(\w+)"/g)].map((m) => m[1]);
const problems = [];
if (!kinds.length) problems.push("could not read the scanner kinds from pages/Scanner.tsx");
if (!links.length) problems.push("no quick-action links found in components/QuickActions.tsx");
if (!/path="\/scan\/:kind"/.test(app)) problems.push('App.tsx has no route path="/scan/:kind"');
if (!/<Scanner\s*\/>/.test(app)) problems.push("App.tsx does not render <Scanner />");
for (const l of links) if (!kinds.includes(l)) problems.push(`quick action /scan/${l} has no scanner page (known: ${kinds.join(", ")})`);
console.log(`scanner pages: ${kinds.join(", ")}\nquick actions: ${links.join(", ")}`);
if (problems.length) { console.error("FAILED:\n- " + problems.join("\n- ")); process.exit(1); }
console.log("OK: every quick action targets an existing scanner page");
