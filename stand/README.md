# stand/ — локальный стенд

Локальный Docker-стек разработчика (не staging/prod). Prod и staging — [`deploy/README.md`](../deploy/README.md) и корневые `docker-compose.staging.yml` / `docker-compose.prod.yml`.

## Содержимое

| Файл | Назначение |
|------|------------|
| `docker-compose.yml` | local compose (`web` + `api` + `gateway` + инфраструктура) |
| `.env.example` | куда класть локальный env (канон — **корневой** `.env`) |
| `README.md` | этот файл |

Пути внутри compose (`context: .`, `./backend`, `./deploy/…`, `env_file: .env`) считаются от **корня репозитория**. Поэтому compose всегда запускают с `--project-directory` на корень.

## Запуск

Из корня репозитория:

```bash
make up-build    # сборка + старт, логи в терминале
make up          # уже собранные образы, фон
make status
make down
```

Без Make:

```bash
docker compose --project-directory . -f stand/docker-compose.yml up --build
docker compose --project-directory . -f stand/docker-compose.yml ps
```

**Нельзя** `cd stand && docker compose up` без `--project-directory` на корень: сломаются build context, тома `./deploy/…` и корневой `.env`.

## Точки входа

- Шлюз: http://127.0.0.1:9088/
- API напрямую: http://127.0.0.1:9062/
- Статика web: http://127.0.0.1:9060/
- Grafana: http://127.0.0.1:9090/ (по умолчанию `admin` / `admin`)

Реальный `.env` не коммитить.
