#!/usr/bin/env bash
# Подменяет favicon PNG/SVG и логотип сайдбара в frontend/public на production-версии из deploy/assets.
# Вызывается только при сборке web-образа с DEPLOY_ENVIRONMENT=production.
# PNG уже закоммичены (без rsvg/apt на сервере — часто нет доступа к deb.debian.org).
# Stage/local: фиолетовые фавиконы + brand-waves.svg; prod: оранжевые.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
SRC_DIR="${ROOT_DIR}/deploy/assets/favicons/production"
DEST_DIR="${1:-${ROOT_DIR}/frontend/public}"

if [[ ! -d "$SRC_DIR" ]]; then
  echo "Каталог production-фавиконов не найден: ${SRC_DIR}" >&2
  exit 1
fi

for size in 16 32 48 192 512; do
  src="${SRC_DIR}/favicon ${size}х${size}.png"
  dest="${DEST_DIR}/favicon ${size}х${size}.png"
  if [[ ! -f "$src" ]]; then
    echo "Нет файла: ${src}" >&2
    exit 1
  fi
  cp "$src" "$dest"
done

cp "${SRC_DIR}/favicon 32х32.svg" "${DEST_DIR}/favicon.svg"
cp "${SRC_DIR}/brand-waves.svg" "${DEST_DIR}/brand-waves.svg"
echo "Production-фавиконы и brand-waves применены в ${DEST_DIR}"
