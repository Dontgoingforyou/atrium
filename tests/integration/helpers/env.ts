import { readFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { loadIntegrationEnv } from "./loadEnv";

loadIntegrationEnv();

export type IntegrationContract = {
  service_id: string;
  kind: string;
  required_env: string[];
  optional_env?: string[];
};

export type ContractsFile = {
  version: string;
  contracts: IntegrationContract[];
};

const here = dirname(fileURLToPath(import.meta.url));

export function loadContracts(path = join(here, "..", "contracts.json")): ContractsFile {
  if (!existsSync(path)) {
    return { version: "1.0", contracts: [] };
  }
  return JSON.parse(readFileSync(path, "utf8")) as ContractsFile;
}

export function missingRequiredEnv(contracts: IntegrationContract[]): string[] {
  const missing: string[] = [];
  const seen = new Set<string>();
  for (const contract of contracts) {
    for (const key of contract.required_env) {
      if (seen.has(key)) continue;
      seen.add(key);
      const value = process.env[key]?.trim() ?? "";
      if (!value || /^change-me$/i.test(value)) {
        missing.push(key);
      }
    }
  }
  return missing;
}

export function requireEnv(key: string): string {
  const value = process.env[key]?.trim() ?? "";
  if (!value) {
    throw new Error(`Не задана переменная окружения: ${key}`);
  }
  return value;
}
