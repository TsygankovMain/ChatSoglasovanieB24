# Деплой на Timeweb Cloud App Platform

## Архитектура

Приложение разворачивается как **два отдельных сервиса**:

| Сервис | Технология | Порт | Dockerfile target |
|--------|-----------|------|------------------|
| **backend** | Django + Gunicorn | 8000 | `prod` |
| **frontend** | Nuxt 3 SPA (Node) | 3000 | `production` |

> База данных не нужна — все данные хранятся в Entity Storage Битрикс24.

Схема взаимодействия:
```
Bitrix24 → HTTPS → frontend (Nuxt SPA, порт 3000)
                         │
              browser → HTTPS → backend (Django, порт 8000)
```

---

## Шаг 1. Создание сервиса Backend

### 1.1 Создайте новый сервис в App Platform

В Timeweb Cloud → App Platform → **Создать приложение** → тип **Docker**.

### 1.2 Укажите исходный код

| Параметр | Значение |
|----------|---------|
| Репозиторий | ваш GitHub/GitLab репозиторий |
| Ветка | `main` (или нужная) |
| Контекст сборки | `backends/python` |
| Путь к Dockerfile | `api/Dockerfile` |
| Target stage | `prod` |

### 1.3 Порт

Укажите порт **8000**.

### 1.4 Переменные окружения

Добавьте все переменные (см. `deploy/backend.env.example`):

| Переменная | Пример | Описание |
|-----------|--------|---------|
| `BUILD_TARGET` | `production` | **Обязательно** — включает продакшен-режим Django |
| `CLIENT_ID` | `local.abc123…` | ID приложения из Битрикс24 |
| `CLIENT_SECRET` | `xyz789…` | Секрет приложения из Битрикс24 |
| `JWT_SECRET` | `(random 64 hex)` | Секрет для JWT токенов |
| `JWT_ALGORITHM` | `HS256` | Алгоритм JWT (оставить как есть) |
| `VIRTUAL_HOST` | `https://your-frontend.twc1.net` | **URL фронтенда** — используется для CORS |
| `DJANGO_SUPERUSER_USERNAME` | `admin` | Опционально |
| `DJANGO_SUPERUSER_EMAIL` | `admin@example.com` | Опционально |
| `DJANGO_SUPERUSER_PASSWORD` | `strongpass` | Опционально |

> ⚠️ `VIRTUAL_HOST` должен указывать на **URL фронтенда**, а не бэкенда.
> Это нужно, чтобы бэкенд добавил фронтенд в `CORS_ALLOWED_ORIGINS`.

### 1.5 Запустите деплой

После деплоя Timeweb выдаст домен вида `https://chat-app-api-xxxxx.twc1.net`.
**Сохраните этот URL** — он понадобится для настройки фронтенда.

---

## Шаг 2. Создание сервиса Frontend

### 2.1 Создайте новый сервис

В App Platform → **Создать приложение** → тип **Docker**.

### 2.2 Укажите исходный код

| Параметр | Значение |
|----------|---------|
| Репозиторий | тот же репозиторий |
| Ветка | `main` |
| Контекст сборки | `frontend` |
| Путь к Dockerfile | `Dockerfile` |
| Target stage | `production` |

### 2.3 Порт

Укажите порт **3000**.

### 2.4 Переменные окружения

| Переменная | Пример | Описание |
|-----------|--------|---------|
| `NUXT_PUBLIC_API_URL` | `https://chat-app-api-xxxxx.twc1.net` | **URL бэкенда** из шага 1.5 |
| `NODE_ENV` | `production` | Режим Node.js |

> `NUXT_PUBLIC_API_URL` — адрес бэкенда, который **браузер** будет вызывать напрямую.
> Это публичный URL из шага 1.5.

### 2.5 Запустите деплой

После деплоя Timeweb выдаст домен фронтенда, например `https://chat-app-xxxxx.twc1.net`.
**Сохраните этот URL** — он нужен для шагов 3 и 4.

---

## Шаг 3. Обновите VIRTUAL_HOST на бэкенде

Вернитесь в переменные окружения **backend** и обновите:

```
VIRTUAL_HOST=https://chat-app-xxxxx.twc1.net   ← URL фронтенда из шага 2.5
```

Перезапустите сервис бэкенда.

---

## Шаг 4. Обновите настройки приложения в Битрикс24

В Битрикс24 → Разработчикам → Ваше приложение:

| Поле | Значение |
|------|---------|
| **Handler URL** | `https://chat-app-xxxxx.twc1.net/handler` |
| Обработчик установки | `https://chat-app-xxxxx.twc1.net/api/install` *(если используется)* |

Где `https://chat-app-xxxxx.twc1.net` — URL фронтенда из шага 2.5.

---

## Шаг 5. Выполните Install Flow

После первого деплоя (и после добавления новых полей в Entity Storage) нужно запустить инсталляцию:

1. Откройте приложение в Битрикс24
2. Или вручную вызовите: `POST https://chat-app-api-xxxxx.twc1.net/api/install` с данными от B24

Это создаст/обновит структуры данных в Entity Storage Битрикс24.

> ⚠️ Если вы добавляли новые поля в `b24_client.py` (например, `FILE_NAMES`),
> обязательно переустановите приложение, чтобы новое свойство появилось в хранилище.

---

## Итоговая схема URL

```
Frontend:  https://chat-app-xxxxx.twc1.net
Backend:   https://chat-app-api-xxxxx.twc1.net

Переменные бэкенда:
  VIRTUAL_HOST = https://chat-app-xxxxx.twc1.net   ← фронтенд

Переменные фронтенда:
  NUXT_PUBLIC_API_URL = https://chat-app-api-xxxxx.twc1.net   ← бэкенд

Битрикс24 Handler URL = https://chat-app-xxxxx.twc1.net/handler
```

---

## Проверка работоспособности

```bash
# Бэкенд — health check
curl https://chat-app-api-xxxxx.twc1.net/api/health

# Фронтенд — должен вернуть HTML
curl -I https://chat-app-xxxxx.twc1.net
```

Ожидаемый ответ health check:
```json
{"status": "ok", "backend": "python", "timestamp": 1234567890}
```

---

## Частые проблемы

### CORS ошибки в браузере
- Проверьте, что `VIRTUAL_HOST` на бэкенде точно совпадает с URL фронтенда (включая `https://`, без слеша на конце).

### 500 при старте бэкенда
- Убедитесь, что `BUILD_TARGET=production` выставлен — без него Django отказывается стартовать без `VIRTUAL_HOST`.
- Проверьте логи сервиса в Timeweb.

### Файлы не загружаются / не открываются
- Убедитесь, что `CLIENT_ID` и `CLIENT_SECRET` верные.
- Перезапустите Install Flow (шаг 5).

### Nuxt не находит бэкенд
- Проверьте `NUXT_PUBLIC_API_URL` — это должен быть **публичный** HTTPS URL бэкенда.
- В SPA (ssr: false) запросы делает браузер, не сервер, поэтому нельзя использовать внутренние Docker-имена.
