/**
 * Подгрузка локальных .env без отдельного npm-пакета dotenv.
 * Порядок: корневой .env репо → tests/integration/.env (поверх).
 * Значения из файла **перезаписывают** process.env — иначе «залипший»
 * export в shell (обрезанный пароль с #) ломает логин.
 * В CI файла .env обычно нет — остаются Variables job’а.
 */
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const integrationDir = join(dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = join(integrationDir, "..", "..");

function applyEnvFile(path: string): void {
  if (!existsSync(path)) {
    return;
  }
  for (const raw of readFileSync(path, "utf8").split(/\r?\n/)) {
    const line = raw.replace(/^\uFEFF/, "").trim();
    if (!line || line.startsWith("#")) {
      continue;
    }
    const eq = line.indexOf("=");
    if (eq <= 0) {
      continue;
    }
    const key = line.slice(0, eq).trim();
    if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(key)) {
      continue;
    }
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

/** Загрузить env и при необходимости взять APP_BASE_URL из PORTAL_PUBLIC_URL. */
export function loadIntegrationEnv(): void {
  applyEnvFile(join(repoRoot, ".env"));
  applyEnvFile(join(integrationDir, ".env"));
  if (!(process.env.APP_BASE_URL ?? "").trim() && (process.env.PORTAL_PUBLIC_URL ?? "").trim()) {
    process.env.APP_BASE_URL = process.env.PORTAL_PUBLIC_URL!.trim();
  }
}
