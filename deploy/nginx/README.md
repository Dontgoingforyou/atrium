# Nginx: маршрутизация Atrium

## Файлы

| Файл | Где используется |
|------|------------------|
| `atrium-server.vhost.conf.example` | Системный nginx на сервере (staging + production). **HTTP :80**, TLS снаружи |
| `atrium-server.vhost.ssl-snippet.example` | Опционально: certbot на этом же хосте |
| `gateway.local.conf` | Docker gateway, корневой `docker-compose.yml` → `:9088` |
| `web-spa.conf` | Внутри контейнера `web` (только SPA) |

## Деплой конфига на сервер

```bash
# из клона репозитория на сервере
sudo cp deploy/nginx/atrium-server.vhost.conf.example /etc/nginx/sites-available/atrium
sudo ln -sf /etc/nginx/sites-available/atrium /etc/nginx/sites-enabled/atrium
sudo nginx -t && sudo systemctl reload nginx
```

Файл **можно копировать целиком** — в нём нет `/etc/letsencrypt/`.

## Внешний TLS

Пример vhost слушает HTTP `:80`. TLS можно завершать на внешнем прокси. `client_max_body_size` на этом прокси должен быть **`2200m`**, иначе загрузка оборвётся HTML `413` до API. `/tg/` в примере остаётся `1m`.

## Обязательные location на API

Перед `location /` (прокси на SPA):

- `/api/`, `/tg/`, `/admin/`, `/static/`
- `/docs`, `/redoc`, `/openapi.json`
- **`/vendor/`** — без него `/docs` отдаёт HTML, а CSS/JS Swagger — `index.html` SPA
- **`/static/admin-brand/`** — брендинг SQLAdmin (CSS); путь уже покрыт `location ^~ /static/`

## Проверка

```bash
curl -sI https://atrium.example.com/vendor/swagger-ui/swagger-ui.css | grep -i content-type
# text/css

curl -sI https://atrium.stage.example.com/vendor/swagger-ui/swagger-ui.css | grep -i content-type
# text/css
```

Если `text/html` — запрос ушёл в SPA (нет `location ^~ /vendor/` или nginx не перезагружен).

### Стили SQLAdmin (`/admin/`) и mixed content

```bash
curl -sI https://atrium.stage.example.com/admin/ | grep -i location
# location: https://...   — правильно
# location: http://...    — схема http: SQLAdmin отдаст статику по http://,
#                           браузер заблокирует её как mixed content, стили админки «слетят»
```

Схему определяет `map $http_x_forwarded_proto $forwarded_proto` в vhost: при пустом
заголовке от внешнего TLS-прокси форсируется `https`. Также проверить `FORWARDED_ALLOW_IPS`
в `.env` (см. `backend/app/core/config.py`) — без доверенного IP/подсети nginx бэкенд
игнорирует `X-Forwarded-Proto` и остаётся на http.
