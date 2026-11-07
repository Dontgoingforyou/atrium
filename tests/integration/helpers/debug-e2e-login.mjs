#!/usr/bin/env node
/**
 * Диагностика E2E login без печати пароля.
 * Запуск из корня: node tests/integration/helpers/debug-e2e-login.mjs
 */
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const integrationDir = join(here, "..");
const repoRoot = join(integrationDir, "..", "..");

function applyEnvFile(path) {
  if (!existsSync(path)) return;
  for (const raw of readFileSync(path, "utf8").split(/\r?\n/)) {
    const line = raw.replace(/^\uFEFF/, "").trim();
    if (!line || line.startsWith("#")) continue;
    const eq = line.indexOf("=");
    if (eq <= 0) continue;
    const key = line.slice(0, eq).trim();
    if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(key)) continue;
    let val = line.slice(eq + 1).trim();
    if (
      (val.startsWith('"') && val.endsWith('"')) ||
      (val.startsWith("'") && val.endsWith("'"))
    ) {
      val = val.slice(1, -1);
    }
    process.env[key] = val;
  }
}

applyEnvFile(join(repoRoot, ".env"));
applyEnvFile(join(integrationDir, ".env"));

const email = (process.env.E2E_SSO_USER_EMAIL ?? "").trim();
const pw = process.env.E2E_SSO_USER_PASSWORD ?? "";
const base = (process.env.APP_BASE_URL || process.env.PORTAL_PUBLIC_URL || "http://127.0.0.1:9088").replace(
  /\/$/,
  "",
);

console.log("email:", email);
console.log("password_len:", pw.length);
console.log("password_has_#:", pw.includes("#"));
console.log("APP_BASE_URL:", base);

const res = await fetch(`${base}/api/v1/auth/login`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    email,
    password: pw,
    redirect_uri: `${base}/auth/callback`,
  }),
});

const text = await res.text();
let data = {};
try {
  data = JSON.parse(text);
} catch {
  data = { raw: text.slice(0, 300) };
}

if (!res.ok) {
  console.log("login_fail status:", res.status);
  console.log("login_fail body:", JSON.stringify(data).slice(0, 400));
  process.exit(1);
}

const u = data.user || {};
console.log("login_ok");
console.log("is_portal_admin:", u.is_portal_admin);
console.log("position:", u.position);
console.log("idp_groups:", u.idp_groups);
