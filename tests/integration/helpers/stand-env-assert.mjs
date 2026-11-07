#!/usr/bin/env node
/**
 * Код выхода: 0 — ок; 2 — нет обязательных env (blocked); 1 — прочая ошибка.
 * Читает корневой .env репо и tests/integration/.env (как Playwright).
 */
import { readFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const integrationDir = join(here, "..");
const repoRoot = join(integrationDir, "..", "..");
const contractsPath = join(integrationDir, "contracts.json");

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
if (!(process.env.APP_BASE_URL ?? "").trim() && (process.env.PORTAL_PUBLIC_URL ?? "").trim()) {
  process.env.APP_BASE_URL = process.env.PORTAL_PUBLIC_URL.trim();
}

if (!existsSync(contractsPath)) {
  console.error("contracts.json не найден");
  process.exit(1);
}

const data = JSON.parse(readFileSync(contractsPath, "utf8"));
const missing = [];
const seen = new Set();
for (const contract of data.contracts ?? []) {
  for (const key of contract.required_env ?? []) {
    if (seen.has(key)) continue;
    seen.add(key);
    const value = (process.env[key] ?? "").trim();
    if (!value || /^change-me$/i.test(value)) {
      missing.push(key);
    }
  }
}

if (missing.length) {
  console.error("Не заданы обязательные переменные стенда:", missing.join(", "));
  process.exit(2);
}

console.log("переменные стенда заданы");
process.exit(0);
