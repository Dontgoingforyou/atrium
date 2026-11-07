import path from "node:path";
import { fileURLToPath } from "node:url";

const integrationRoot = path.dirname(fileURLToPath(import.meta.url));

/** Cookie/localStorage после setup-логина. Не коммитить (см. .gitignore). */
export const AUTH_STATE_PATH = path.join(integrationRoot, "..", ".auth", "user.json");
