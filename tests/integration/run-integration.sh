#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPORT_DIR="$ROOT/reports"
mkdir -p "$REPORT_DIR"

STARTED_AT="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
BLOCKED=0
FAILED=0

# Локальный .env (секреты не в git). Уже заданные в shell/CI переменные не перезаписываем.
# Порядок: корневой .env репо → tests/integration/.env (поверх для E2E-ключей).
# Важно: пароли с # { } и т.п. пишите в кавычках: E2E_SSO_USER_PASSWORD='...#...'
load_dotenv_file() {
  local env_file="$1"
  local label="$2"
  if [ ! -f "$env_file" ]; then
    return 0
  fi
  echo "== Загрузка ${label} =="
  while IFS= read -r line || [ -n "$line" ]; do
    # только целая строка-комментарий; НЕ резать value по «#» внутри пароля
    line="${line#"${line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"
    [ -z "$line" ] && continue
    case "$line" in
      \#*) continue ;;
      *=*) ;;
      *) continue ;;
    esac
    local key="${line%%=*}"
    local val="${line#*=}"
    key="${key%"${key##*[![:space:]]}"}"
    key="${key#"${key%%[![:space:]]*}"}"
    [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || continue
    val="${val#"${val%%[![:space:]]*}"}"
    if [[ "$val" =~ ^\"(.*)\"$ ]]; then
      val="${BASH_REMATCH[1]}"
    elif [[ "$val" =~ ^\'(.*)\'$ ]]; then
      val="${BASH_REMATCH[1]}"
    fi
    # Файл побеждает «залипший» export в shell (типично обрезанный пароль с #).
    export "${key}=${val}"
  done < "$env_file"
}

REPO_ROOT="$(cd "$INT_DIR/../.." && pwd)"
load_dotenv_file "$REPO_ROOT/.env" "корневой .env"
load_dotenv_file "$INT_DIR/.env" "tests/integration/.env"
if [ -z "${APP_BASE_URL:-}" ] && [ -n "${PORTAL_PUBLIC_URL:-}" ]; then
  export APP_BASE_URL="$PORTAL_PUBLIC_URL"
fi

# TC ids for blocked mapping: SOFTGEN_INTEGRATION_TC_IDS=TC-001,TC-010 или аннотации в specs/
collect_blocked_tc_ids() {
  if [ -n "${SOFTGEN_INTEGRATION_TC_IDS:-}" ]; then
    printf '%s' "$SOFTGEN_INTEGRATION_TC_IDS" | tr ',' '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | grep -E '^TC-[0-9]+$' || true
    return
  fi
  if [ -d "$INT_DIR/specs" ]; then
    grep -RhoE 'TC-[0-9]+' "$INT_DIR/specs" 2>/dev/null | sort -u || true
  fi
}

echo "== Проверка переменных integration =="
ASSERT_JS="$INT_DIR/helpers/integration-env-assert.mjs"
if [ -f "$ASSERT_JS" ]; then
  set +e
  if command -v bun >/dev/null 2>&1; then
    bun "$ASSERT_JS"
    RC=$?
  elif command -v node >/dev/null 2>&1; then
    node "$ASSERT_JS"
    RC=$?
  else
    echo "нужен bun или node"
    exit 1
  fi
  set -e
  if [ "$RC" -eq 2 ]; then
    BLOCKED=1
    echo "blocked: не заданы обязательные переменные integration"
  elif [ "$RC" -ne 0 ]; then
    FAILED=1
  fi
else
  echo "нет integration-env-assert.mjs"
  FAILED=1
fi

if [ "$BLOCKED" -eq 1 ]; then
  FINISHED_AT="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  MSG="Не заданы обязательные переменные integration (contracts.json / required_env)"
  RESULTS_JSON="["
  FIRST=1
  while IFS= read -r TC_ID; do
    [ -z "$TC_ID" ] && continue
    if [ "$FIRST" -eq 1 ]; then FIRST=0; else RESULTS_JSON+=","; fi
    RESULTS_JSON+=$(printf '\n    {"tc_id":"%s","status":"blocked","message":"%s"}' "$TC_ID" "$MSG")
  done < <(collect_blocked_tc_ids)
  if [ "$FIRST" -eq 1 ]; then
    # Mapping fallback: нет TC в specs / env → TC-001 (см. README)
    RESULTS_JSON+=$(printf '\n    {"tc_id":"TC-001","status":"blocked","message":"%s"}' "$MSG")
  fi
  RESULTS_JSON+=$'\n  ]'
  cat > "$REPORT_DIR/test-run-results.json" <<EOF
{
  "version": "1.0",
  "run_id": "integration-blocked",
  "started_at": "$STARTED_AT",
  "finished_at": "$FINISHED_AT",
  "source": "integration",
  "results": $RESULTS_JSON,
  "unmapped": [],
  "summary": { "passed": 0, "failed": 0, "skipped": 0, "blocked": 1, "unmapped": 0 }
}
EOF
  echo "Записан blocked: $REPORT_DIR/test-run-results.json (exit non-zero)"
  exit 1
fi

echo "== Playwright integration =="
if [ -f "$INT_DIR/playwright.config.ts" ] && command -v npx >/dev/null 2>&1; then
  set +e
  (
    cd "$INT_DIR"
    if [ ! -d node_modules ]; then
      echo "npm ci в tests/integration..."
      npm ci || exit 1
    fi
    # Браузеры не входят в npm-пакет — лежат в ~/.cache/ms-playwright.
    # install идемпотентен: если ревизия уже есть, сразу выходит.
    echo "npx playwright install chromium..."
    npx playwright install chromium || exit 1
    npx playwright test -c playwright.config.ts
  )
  PW_RC=$?
  set -e
  if [ "$PW_RC" -ne 0 ]; then
    FAILED=$((FAILED + 1))
  fi
else
  echo "skip: playwright недоступен"
  FAILED=$((FAILED + 1))
fi

if [ -f "$ROOT/scripts/import-test-results.mjs" ]; then
  node "$ROOT/scripts/import-test-results.mjs" \
    --reports-dir "$REPORT_DIR" \
    --output "$REPORT_DIR/test-run-results.json" \
    --started-at "$STARTED_AT" \
    --source integration || FAILED=$((FAILED + 1))
fi

exit $(( FAILED > 0 ? 1 : 0 ))
