// Lighthouse accessibility on /, /demo and a real round page (spec gate: >= 95).
// Starts its own API (:8010, LLM_MODE=off) and production web (:3100) if they are not running.
import { spawn, execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const web = path.resolve(here, "..");
const root = path.resolve(web, "..");
const API = "http://127.0.0.1:8010";
const WEB = "http://127.0.0.1:3100";
const kids = [];

async function up(url) {
  try {
    return (await fetch(url)).ok;
  } catch {
    return false;
  }
}
async function waitFor(url, ms) {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) {
    if (await up(url)) return;
    await new Promise((r) => setTimeout(r, 1000));
  }
  throw new Error(`timeout waiting for ${url}`);
}
function start(cmd, cwd, env) {
  const p = spawn("bash", ["-lc", cmd], { cwd, env: { ...process.env, ...env }, stdio: "ignore", detached: true });
  kids.push(p);
}

try {
  if (!(await up(`${API}/api/health`))) {
    start(`uv run uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8010`, root, {
      LLM_MODE: "off", CREATE_LIMIT_PER_HOUR: "1000", FALKORDB_HOST: "localhost",
    });
    await waitFor(`${API}/api/health`, 120_000);
  }
  if (!(await up(WEB))) {
    start(`API_ORIGIN=${API} pnpm build && API_ORIGIN=${API} pnpm start -p 3100`, web, {});
    await waitFor(WEB, 300_000);
  }
  const call = async (p, body, token) =>
    (await fetch(`${API}/api${p}`, {
      method: body === undefined && !p.endsWith("/families") ? "GET" : "POST",
      headers: { "content-type": "application/json", ...(token ? { authorization: `Bearer ${token}` } : {}) },
      body: body === undefined ? undefined : JSON.stringify(body),
    })).json();
  const c = await (await fetch(`${API}/api/families`, { method: "POST" })).json();
  const t = c.family_token;
  const ex = await call(`/families/${c.family_id}/story`, {
    text: "Kabir has low muscle tone, delayed walking, delayed speech, a squint, a small head, a heart murmur and feeding problems.",
    child_age_months: 30,
  }, t);
  await call(`/families/${c.family_id}/confirm`, { accept: ex.extraction_to_confirm.map((i) => i.id), reject: [], edits: [] }, t);

  const pages = { "/": `${WEB}/`, "/demo": `${WEB}/demo`, "round page": `${WEB}/j/${c.family_id}/round/1#t=${encodeURIComponent(t)}` };
  const chrome = fs.readdirSync(path.join(process.env.HOME, "Library/Caches/ms-playwright")).find((d) => /^chromium-\d+$/.test(d));
  const out = {};
  for (const [name, url] of Object.entries(pages)) {
    const res = execFileSync(
      "pnpm",
      ["exec", "lighthouse", url, "--only-categories=accessibility", "--output=json", "--quiet",
        '--chrome-flags=--headless=new --no-sandbox'],
      { cwd: web, env: { ...process.env, CHROME_PATH: findChrome(chrome) }, maxBuffer: 64 * 1024 * 1024 },
    ).toString();
    const j = JSON.parse(res);
    out[name] = Math.round(j.categories.accessibility.score * 100);
    const bad = Object.values(j.audits).filter((a) => a.score === 0 && a.scoreDisplayMode === "binary").map((a) => a.id);
    console.log(`${name}: ${out[name]}${bad.length ? "  failing: " + bad.join(", ") : ""}`);
  }
  fs.mkdirSync(path.join(root, ".build/logs"), { recursive: true });
  fs.writeFileSync(path.join(root, ".build/logs/lighthouse.json"), JSON.stringify(out, null, 2));
  if (Object.values(out).some((s) => s < 95)) process.exitCode = 1;
} finally {
  for (const k of kids) try { process.kill(-k.pid); } catch { /* already gone */ }
}

function findChrome(dir) {
  const base = path.join(process.env.HOME, "Library/Caches/ms-playwright", dir);
  const guess = ["chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
    "chrome-mac/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"].map((g) => path.join(base, g));
  const hit = guess.find((g) => fs.existsSync(g));
  if (!hit) throw new Error(`Chromium not found under ${base}`);
  return hit;
}
