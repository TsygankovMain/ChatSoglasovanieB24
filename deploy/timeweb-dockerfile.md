# Деплой на Timeweb Cloud App Platform через один Dockerfile

Этот вариант предназначен для типа приложения **Dockerfile** в Timeweb Cloud App Platform.

## Что собирается

В корне репозитория добавлен `Dockerfile`, который собирает один контейнер:

- `nginx` слушает внешний порт `8080` или значение `$PORT`;
- Nuxt SPA работает внутри контейнера на `127.0.0.1:3000`;
- Django/Gunicorn работает внутри контейнера на `127.0.0.1:8000`;
- nginx проксирует `/api` в Django, все остальные маршруты в Nuxt.

Локальная PostgreSQL не нужна: актуальная версия backend хранит состояние в Bitrix24 Entity Storage.

## Настройки Timeweb

При создании приложения выберите:

| Поле | Значение |
|------|----------|
| Тип | Dockerfile |
| Путь до директории проекта | пусто, если Dockerfile лежит в корне |
| Порт | 8080, определяется через `EXPOSE 8080` |
| Health check path | `/nginx-health` |

## Переменные окружения

Минимальный набор:

```env
BUILD_TARGET=production
NODE_ENV=production
JWT_ALGORITHM=HS256
JWT_SECRET=replace_with_openssl_rand_hex_32
CLIENT_ID=local.xxxxxxxxxxxxxxxx
CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
VIRTUAL_HOST=https://your-app-domain.twc1.net
NUXT_PUBLIC_APP_URL=https://your-app-domain.twc1.net
NUXT_PUBLIC_API_URL=
```

`NUXT_PUBLIC_API_URL` можно оставить пустым: frontend будет обращаться к `/api` на том же домене.

`VIRTUAL_HOST` должен быть публичным HTTPS URL этого же приложения без завершающего слеша. Он используется Django для `ALLOWED_HOSTS`, CSRF/CORS и webhook URL для Bitrix24.

## Bitrix24

В настройках локального приложения Bitrix24 укажите домен Timeweb:

| Поле | Значение |
|------|----------|
| Handler URL | `https://your-app-domain.twc1.net/` |
| Обработчик установки | `https://your-app-domain.twc1.net/api/install` |
| Обработчик удаления | `https://your-app-domain.twc1.net/api/event/onAppUninstall` |

Скоупы приложения: `im, imbot, entity, disk, placement, user`.

## Проверка после деплоя

```bash
curl https://your-app-domain.twc1.net/nginx-health
```

Ожидается `ok` на `/nginx-health`. Маршрут `/api/health` в текущем backend защищён авторизацией приложения, поэтому без JWT может возвращать `400`.

## Важное ограничение первого деплоя

Django в production режиме намеренно не стартует без `VIRTUAL_HOST`. Если технический домен Timeweb неизвестен до первого запуска, используйте заранее подключенный собственный домен или после первого создания приложения задайте `VIRTUAL_HOST` и перезапустите деплой.
