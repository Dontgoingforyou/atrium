import { requireEnv } from "../env";

/**
 * Скелет адаптера HTTP API / storage стенда (kind=http_api | storage).
 * Пример: Nextcloud WebDAV — baseUrlEnv=NEXTCLOUD_BASE_URL, healthPath=/status.php.
 * Допишите пути и заголовки под конкретный сервис.
 */
export async function pingHttpApiStand(options?: {
  baseUrlEnv?: string;
  tokenEnv?: string;
  healthPath?: string;
}): Promise<{ ok: boolean; status: number; body: string }> {
  const base = requireEnv(options?.baseUrlEnv ?? "KB_BASE_URL").replace(/\/$/, "");
  const path = options?.healthPath ?? "/health";
  const headers: Record<string, string> = { Accept: "application/json" };
  const tokenKey = options?.tokenEnv ?? "KB_API_TOKEN";
  const token = process.env[tokenKey]?.trim();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const response = await fetch(`${base}${path.startsWith("/") ? path : `/${path}`}`, {
    headers,
  });
  const body = await response.text();
  return { ok: response.ok, status: response.status, body };
}
