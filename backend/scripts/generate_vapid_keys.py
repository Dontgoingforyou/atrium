#!/usr/bin/env python3
"""Генерация пары ключей VAPID для Web Push (переменные VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY).

Запуск из корня репозитория:
  backend/.venv/bin/python backend/scripts/generate_vapid_keys.py

Вставьте вывод в .env. Для Docker Compose надёжнее **одна строка** с ``\\n`` (см. блок «Docker» ниже).
Контакт VAPID_CONTACT_EMAIL задайте вручную, например mailto:ops@example.com
"""

from __future__ import annotations

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from py_vapid.utils import b64urlencode


def main() -> None:
    priv = ec.generate_private_key(ec.SECP256R1(), default_backend())
    pub_raw = priv.public_key().public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    pub_b64 = b64urlencode(pub_raw)
    pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    print("# Скопируйте в .env (приватный ключ храните только на сервере / в CI secrets)")
    print(f"VAPID_PUBLIC_KEY={pub_b64}")
    print()
    pem_one = pem.strip().replace("\n", "\\n")
    print("# --- Docker / docker-compose env_file: одна переменная (иначе PEM обрежется до первой строки) ---")
    print(f'VAPID_PRIVATE_KEY="{pem_one}"')
    print()
    print("# --- Многострочный PEM (удобно без Docker; в контейнере может не дойти целиком) ---")
    print("VAPID_PRIVATE_KEY=")
    for line in pem.splitlines():
        print(line)
    print()
    print("# Обязательно задайте контакт для подписи JWT (пример):")
    print("# VAPID_CONTACT_EMAIL=mailto:ops@example.com")


if __name__ == "__main__":
    main()
