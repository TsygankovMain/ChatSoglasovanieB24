# Security Audit (OWASP)

**Дата**: апрель 2026
**Спринт**: 1, задача 1.7
**Стандарты**: OWASP Top 10 (2021), 152-ФЗ (ПДн), Bitrix24 marketplace policies

## Сводка

| Severity | Кол-во |
|----------|--------|
| P0 | 1 |
| P1 | 5 |
| P2 | 4 |
| P3 | 3 |

## P0 — критические

### SEC-P0-1 ⚠️ `DEBUG=True` в продакшене
- **Файл**: `backends/python/api/settings.py:9`
- **OWASP**: A05:2021 Security Misconfiguration
- **Риск**: Django при `DEBUG=True` отдаёт полные tracebacks с переменными окружения, путями файлов, секретами в SQL и токенами Bitrix24 при любой 500-ошибке.
- **Эксплуатация**: атакующий вызывает несуществующий путь, видит `SECRET_KEY`, `db_password`, `OAuth refresh_token` в трейсе.
- **Действие**: `DEBUG = config.debug` (default `False`) перед деплоем. **Блокер для Sprint 4.**

## P1 — серьёзные

### SEC-P1-1 ⚠️ OAuth токены в БД хранятся в открытом виде
- **Файл**: `main/models.py` (`Bitrix24Account` модель)
- **OWASP**: A02:2021 Cryptographic Failures
- **Риск**: при компрометации БД (SQL injection, утечка дампа) атакующий получает `access_token`+`refresh_token` для всех порталов и может действовать от имени любого администратора.
- **Действие**: шифрование колонок `auth_id`, `refresh_id`, `refresh_token` через `cryptography.fernet` или `django-cryptography`. Ключ — в env.
- **Альтернатива**: если шифрование сложно — хотя бы зашифровать на уровне диска (LUKS/cloud-managed encryption) и задокументировать.

### SEC-P1-2 ⚠️ `approval_detail` не проверяет права доступа
- **Файл**: `views.approval_detail:223-228`
- **Симптом**: любой аутентифицированный пользователь портала может прочитать любой запрос по ID, даже если он не инициатор и не согласующий.
- **OWASP**: A01:2021 Broken Access Control
- **Эксплуатация**: подбор `request_id` в URL → утечка комментариев/файлов чужих согласований.
- **Действие**: добавить проверку `user_id in approver_ids or user_id == initiator_id` в `services.get_request` или `views.approval_detail`.

### SEC-P1-3 ⚠️ `CORS_ALLOW_ALL_ORIGINS = True`
- **Файл**: `settings.py:90`
- **OWASP**: A05:2021
- **Действие**: whitelist на `[config.app_base_url, *.bitrix24.ru, *.bitrix24.com]`.

### SEC-P1-4 ⚠️ `ALLOWED_HOSTS = ["*"]` при пустом VIRTUAL_HOST
- **Файл**: `settings.py:10, 24`
- **OWASP**: A05:2021 + Host header injection.
- **Действие**: на проде требовать `VIRTUAL_HOST` непустым, иначе fail-fast при старте.

### SEC-P1-5 ⚠️ `csrf_exempt` на всех endpoints
- **Файлы**: `views.py:8, 156, 232, 252` — все основные view-функции декорированы `@csrf_exempt`.
- **OWASP**: A01:2021 + CSRF
- **Контекст**: для webhook от Bitrix24 (`vote_handle`) это правильно — CSRF-токен не передаётся. Но `approval_create`/`approval_cancel` вызываются из браузера через `apiStore` → CSRF здесь нужен.
- **Действие**: на `approval_create`/`approval_cancel` снять `csrf_exempt` и реализовать CSRF через двойной cookie или подпись от `auth_required`. На webhook — оставить, но проверить подпись Bitrix24 (см. SEC-P2-1).

## P2 — серьёзные оптимизации

### SEC-P2-1 ⚠️ Webhook `vote_handle` не проверяет подпись Bitrix24
- **Файл**: `views.vote_handle:251-326`
- **Риск**: любой может отправить POST на `/api/vote/handle` с подмененным `auth.member_id` и проголосовать от чужого имени.
- **Митигация в коде**: `_resolve_account` ищет `Bitrix24Account` по `member_id` + `domain`. Если злоумышленник знает `member_id` (несложно — публичен в URL), он может подделать webhook.
- **Действие**: проверять подпись `application_token` из payload (Bitrix24 посылает в каждом webhook). См. документацию `dev.1c-bitrix.ru/api_help/general/events_method.php`.

### SEC-P2-2 Файлы загружаются без проверки типа
- **Файл**: `disk/service.py` + `serializers.validate_create_form`
- **Риск**: пользователь загружает `.exe`/`.html` с XSS. Bitrix24 disk сам по себе MIME-типы валидирует, но антивирус не гарантирован.
- **Действие**: white-list расширений (`.pdf, .docx, .xlsx, .png, .jpg, .zip`) на серверной стороне в `validate_create_form`.

### SEC-P2-3 Логирование чувствительных полей
- **Файл**: `views.approval_create:169-178` логирует `len(comment)`, без самого comment — это правильно. Но в `views.vote_handle:280` логируется `payload_keys` — норм. **Проверить** `b24_client.http.call` — не логирует ли он body запросов с токенами.
- **Действие**: ревизия логов на отсутствие `auth_id`, `refresh_token`, тел сообщений.

### SEC-P2-4 Отсутствие rate limit
- **OWASP**: A04:2021 Insecure Design + DoS
- **Риск**: атакующий может зафлудить `/api/approval/create` или `/api/vote/handle`.
- **Действие**: `django-ratelimit` или nginx rate limit на чувствительные endpoint'ы.

## P3 — стилевые / процесс

| ID | Проблема | Файл | OWASP |
|----|----------|------|-------|
| SEC-P3-1 | Нет ротации `SECRET_KEY` | `settings.py:8` | A02 |
| SEC-P3-2 | Нет SECURE-флагов на cookies | `settings.py` | A05 |
| SEC-P3-3 | Нет HSTS / X-Frame-Options кроме `xframe_options_exempt` | везде | A05 |

## Соответствие 152-ФЗ (ПДн)

| Требование | Статус |
|------------|--------|
| Согласие на обработку ПДн | ❌ Не оформлено (Sprint 3.5) |
| Уведомление Роскомнадзора | ❌ Не оформлено |
| Локализация ПДн на территории РФ | ✅ при деплое в Timeweb (Sprint 4) |
| Удаление ПДн при деинсталляции | ❌ Нет `ONAPPUNINSTALL` обработчика (FE-P1-1) |
| Шифрование ПДн при передаче | ✅ HTTPS обязателен |
| Шифрование ПДн при хранении | 🟡 Зависит от Timeweb managed PostgreSQL |

## Соответствие политике маркетплейса Bitrix24

(Уточнить через MCP `bitrix-article-details` в Sprint 3.1)

| Требование | Статус |
|------------|--------|
| Политика конфиденциальности на странице приложения | ❌ (Sprint 3.5) |
| Условия использования | ❌ (Sprint 3.5) |
| Указание разработчика и контактов | ❌ (Sprint 3.8) |
| OAuth scopes — минимально необходимые | 🟡 (`userfieldtype` лишний — FE-P3-1) |

## Threat model (краткая)

| Актор | Цель | Вектор | Митигация |
|-------|------|--------|-----------|
| Внешний атакующий | Прочитать чужие запросы | подбор `request_id` | SEC-P1-2 |
| Инсайдер портала | Голосовать за других | webhook spoofing | SEC-P2-1 |
| Утечка БД | Получить OAuth токены | SQL injection / dump | SEC-P1-1 |
| Атакующий через Marketplace | XSS через файл | загрузка `.html` | SEC-P2-2 |
| Атакующий через Marketplace | DoS | флуд `/api/*` | SEC-P2-4 |

## Action plan

| Приоритет | Действие | Спринт |
|-----------|----------|--------|
| P0 | `DEBUG=False` через env | 4 (блокер) |
| P1 | Шифрование OAuth токенов | 2.2 или 4 |
| P1 | Проверка прав в `approval_detail` | 2.2 |
| P1 | CORS whitelist | 4 |
| P1 | `ALLOWED_HOSTS` валидация | 4 |
| P1 | CSRF на business endpoints | 2.2 |
| P2 | Webhook signature verification | 2.2 |
| P2 | File MIME whitelist | 2.3 |
| P2 | Ревизия логов | 2.3 |
| P2 | Rate limit | 4 |
| P3 | Ротация SECRET_KEY | 4 |
| P3 | SECURE cookies + HSTS | 4 |
