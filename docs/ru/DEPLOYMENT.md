# Развёртывание

*Состояние на 02.10.2026.*

Приложение собирается в один образ из корневого `Dockerfile`. Внутри три процесса за одним nginx на порту 8080: Nuxt (интерфейс), Django под gunicorn (API) и сам nginx. Скрипт запуска — `deploy/timeweb/entrypoint.sh`. База данных не нужна.

## Где работает

| Площадка | Адрес | Что развёрнуто | Как обновляется |
|---|---|---|---|
| Timeweb App Platform | `tsygankovmain-chatsoglasovanieb24-c9c9.twc1.net` | ветка `prod`, на этот адрес смотрят установленные порталы | из ветки `prod`; пуш в неё считать выкаткой |
| Сервер Мейнсофт `main.mainsoft.su` | `soglasovanie.apps.mainsoft.su` | с 02.10.2026 ветка `claude/tech-debt` (`a42b887`), сеть `edge`, выход в интернет открыт. Порталы на этот адрес пока не переведены | вручную, см. ниже |

На Timeweb остаётся прежняя версия из `prod`.

## Переменные окружения

| Переменная | Обязательна | Значение |
|---|---|---|
| `JWT_SECRET` | да | Случайная строка не короче 32 символов: `openssl rand -hex 32`. С более коротким значением бэкенд в боевом режиме не стартует |
| `VIRTUAL_HOST` | да | Публичный адрес приложения с `https://`. По нему регистрируются бот, кнопки и встройки на портале |
| `APP_URL` | нет | То же, что `VIRTUAL_HOST`; подставляется, если тот не задан |
| `ALLOWED_HOSTS` | нет | Дополнительные имена хоста через запятую |
| `BUILD_TARGET` | нет | `production` задан в образе; `dev` включает отладку Django |
| `CLIENT_ID`, `CLIENT_SECRET` | нет | Нужны только для продления OAuth-токена на стороне сервера. Приложение из Маркета работает без них: свежий токен каждый раз приносит портал |
| `GUNICORN_WORKERS`, `GUNICORN_TIMEOUT` | нет | По умолчанию 2 и 120 |

`JWT_SECRET` при переезде на другой адрес сохранять не нужно: JWT живёт час и привязан к адресу, с которого открыт интерфейс.

## Выкатка на `main.mainsoft.su`

Папка приложения — `/srv/prod/soglasovanie`: исходники в `src`, настройки в `compose.yml` и `soglasovanie.env`, ревизия в `REVISION`. Вход — Caddy (`/srv/prod/proxy/sites/apps.caddy`), сертификат выпускается сам.

Шаги для новой ревизии:

```bash
# 1. На машине с репозиторием: архив нужной ветки
git archive --format=tar <ветка> > soglasovanie-src.tar
scp soglasovanie-src.tar prod-main:/tmp/

# 2. На сервере: сохранить текущий образ для отката и заменить исходники
ssh prod-main
cd /srv/prod/soglasovanie
docker tag mainsoft/soglasovanie:latest mainsoft/soglasovanie:prev
mkdir src.new && tar -xf /tmp/soglasovanie-src.tar -C src.new
mv src src.prev && mv src.new src
echo "<ветка> <короткий хеш>" > REVISION

# 3. Собрать и перезапустить
docker build -t mainsoft/soglasovanie:latest src
docker compose up -d
docker compose ps        # ждать healthy
```

Приложение работает в сети `edge` — ему нужен выход в интернет, чтобы обращаться к порталам. Прежний зеркальный вариант настроек сохранён на сервере как `compose.yml.mirror`.

Проверка снаружи:

```bash
curl -fsS https://soglasovanie.apps.mainsoft.su/nginx-health        # ok
# Заведомо неверный токен: бэкенд должен дойти до портала и получить отказ — 401
curl -s -o /dev/null -w '%{http_code}\n' -X POST https://soglasovanie.apps.mainsoft.su/api/getToken \
  -H 'Content-Type: application/json' \
  -d '{"DOMAIN":"mainsoft.bitrix24.ru","AUTH_ID":"x","member_id":"x"}'
```

Откат: `docker tag mainsoft/soglasovanie:prev mainsoft/soglasovanie:latest && docker compose up -d`, исходники вернуть из `src.prev`. Версия до 02.10.2026 сохранена как образ `mainsoft/soglasovanie:prod-ceec187` и папка `src.ceec187`.

## Перевод порталов на новый адрес

Адреса обработчиков записаны на каждом портале: бот, две команды кнопок, три встройки в чат, событие удаления. Приложение не хранит токены порталов и само их переписать не может. Адрес меняется, когда на портале проходит установка или обновление приложения: мастер установки заново регистрирует всё на адрес из `VIRTUAL_HOST`.

Поэтому порядок такой:

1. Выкатить и проверить приложение на новом адресе — сделано 02.10.2026. Timeweb при этом продолжает работать.
2. В кабинете разработчика выпустить новую версию приложения: ссылка на приложение `https://soglasovanie.apps.mainsoft.su/`, установочная — `https://soglasovanie.apps.mainsoft.su/install`. Версия 2 отправлена на модерацию 02.10.2026.
3. Порталы переходят на новый адрес по мере обновления приложения. Пока портал не обновился, он работает через Timeweb.
4. Timeweb выключать после прохождения модерации. Портал, который к этому моменту не обновил приложение, продолжит обращаться к адресу Timeweb и перестанет работать до обновления — перед выключением стоит оценить, сколько таких установок.

Обе площадки могут работать одновременно: общих данных между ними нет.

До слияния этой ветки в `prod` проверить `JWT_SECRET` в панели Timeweb: если там строка короче 32 символов, новая версия на Timeweb не запустится.

## Локальная разработка

```bash
cp .env.example .env      # VIRTUAL_HOST, CLOUDPUB_TOKEN, JWT_SECRET
make dev-python           # интерфейс + API + туннель cloudpub
make test                 # тесты бэкенда
make lint                 # линтер фронтенда
```

Dev-окружение описано в `docker-compose.dev.yml`. `docker-compose.yml` — вариант из трёх контейнеров для своего сервера; боевые площадки используют корневой `Dockerfile`.

## Проверки в CI

`.github/workflows/ci.yml`, запускается на пуш в `prod` и `DEV` и на каждый PR:

- тесты бэкенда и загрузка боевых настроек;
- линтер и сборка фронтенда из lock-файла;
- совпадение ключей переводов RU и EN.

Деплоя в CI нет.
