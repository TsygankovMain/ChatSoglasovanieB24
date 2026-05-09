# Архитектура системы

Полное описание проектирования системы, потока данных и архитектурных паттернов. Документ обновлён по итогам Sprint 2.2 (отказ от собственной БД, переход на полностью stateless-бэкенд).

## Общая архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                      Портал Bitrix24                        │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Чат (IM_TEXTAREA placement)                          │   │
│  │ └─ Иконка приложения над полем ввода                 │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Универсальный бот (imbot)                            │   │
│  │ └─ Публикует запросы и обновляет статусы             │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Хранилище сущностей (entity)                         │   │
│  │ ├─ appr_requests   (метаданные запросов)             │   │
│  │ └─ approval_votes  (решения голосующих)              │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Диск (Bitrix24 Disk)                                 │   │
│  │ └─ Прикреплённые файлы по папкам "Согласования/..."  │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
       ▲   ▲                                       │
       │   │ REST API / Webhooks (ONIMCOMMANDADD,  │
       │   │  ONAPPUNINSTALL)                      ▼
┌──────┴───┴──────────────────────────────────────────────────┐
│        Фронтенд: Vue 3 + Nuxt 4 (iframe в Bitrix24)         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ @bitrix24/b24jssdk-nuxt — OAuth/iframe SDK           │   │
│  │ Pinia stores: api, approvals                         │   │
│  └──────────────────────────────────────────────────────┘   │
└──────┬──────────────────────────────────────────────────────┘
       │ JWT-Bearer  (60 мин, HS256, payload = OAuth-токены)
       ▼
┌─────────────────────────────────────────────────────────────┐
│        Бэкенд API: Python + Django (stateless)              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ B24AuthContext (in-memory, нет БД)                   │   │
│  │ b24pysdk — OAuth-клиент для Bitrix24                 │   │
│  │ ApprovalService + ApprovalB24Client                  │   │
│  └──────────────────────────────────────────────────────┘   │
│              ▲                                               │
│              │  «база данных» = Bitrix24 entity на портале  │
└─────────────────────────────────────────────────────────────┘
```

> **Stateless-инвариант (Sprint 2.2)**: бэкенд не имеет ни PostgreSQL, ни ORM-моделей `Bitrix24Account`/`ApplicationInstallation`. Все OAuth-токены живут в JWT (фронт→бэк) или в webhook-payload'е от Bitrix24 (Bitrix24→бэк) и существуют только на время одного HTTP-запроса. См. `backends/python/api/main/b24_auth.py::B24AuthContext`.

## Основные модули

### 1. Хранилище сущностей (Bitrix24 entity)

Это **единственный** долгоживущий стор данных приложения. Принадлежит порталу клиента, не нашему бэкенду — поэтому удаление приложения с одного портала не затрагивает другие.

**`appr_requests`** — метаданные запроса:

| Поле | Тип | Описание |
|------|-----|----------|
| `INITIATOR_ID` | string | ID пользователя-создателя |
| `COMMENT` | text | Описание запроса |
| `APPROVER_IDS` | JSON-string | Массив ID согласующих |
| `THRESHOLD_TYPE` | string | `all` (единогласно) или `majority` |
| `STATUS` | string | `collecting` / `approved` / `rejected` / `cancelled` |
| `DIALOG_ID` | string | ID исходного чата для контекста |
| `BOT_MESSAGE_ID` | string | ID последнего сообщения бота |
| `BOT_MESSAGE_IDS` | JSON-string | Все сообщения, которые мы поддерживаем (для multi-dialog) |
| `BOT_DIALOG_IDS` | JSON-string | Чаты, в которых мы постили |
| `DISK_FOLDER_ID` | string | Папка с вложениями |
| `FILE_IDS` | JSON-string | Массив ID загруженных файлов |
| `FILE_NAMES` | JSON-string | Имена файлов (отображаемые) |
| `CREATED_AT` | string | ISO timestamp создания |

**`approval_votes`** — решения согласующих:

| Поле | Тип | Описание |
|------|-----|----------|
| `REQUEST_ID` | string | Внешний ключ к `appr_requests.ID` |
| `USER_ID` | string | ID голосующего |
| `DECISION` | string | `APPROVE` или `REJECT` |
| `COMMENT` | text | Опциональный комментарий |
| `VOTED_AT` | string | ISO timestamp голоса |

> Поле «индексы» как в реляционной БД здесь не применимо: Bitrix24 entity предоставляет только встроенные `FILTER` и `SORT`. См. раздел «Оптимизация».

### 2. Слой ботов (imbot)

- `imbot.register` — регистрация бота при первой установке (флаг `app.option["bot_id"]` хранит результат).
- `imbot.message.add` — публикация исходного сообщения с кнопками голосования.
- `imbot.message.update` — обновление того же сообщения после каждого голоса (показываем актуальные счётчики).
- Webhook `ONIMCOMMANDADD` — Bitrix24 присылает события нажатия кнопок (legacy keyboard-button payload и современный event-payload оба обрабатываются `_extract_vote_payload`).

### 3. Слой размещений

```
Placement: IM_TEXTAREA
Handler:   {VIRTUAL_HOST}/
Title:     "Запрос согласования"
Width:     400, Height: 300, fitWindow: true
```

Iframe-загрузка через `@bitrix24/b24jssdk-nuxt`; OAuth-bundle получает фронт от Bitrix24 SDK и обменивает на JWT через `/api/auth/get-token`.

### 4. Slim Django backend

Контейнер существенно меньше типового Django:

- **Нет БД** — `DATABASES.default.ENGINE = django.db.backends.dummy`.
- **Нет admin** — удалён вместе с моделями.
- **Нет миграций** — нечего мигрировать.
- **`INSTALLED_APPS`**: `contenttypes`, `staticfiles`, `corsheaders`, `main` (наш entry-point app).
- **CORS**: whitelist `*.bitrix24.*` через regex (Sprint 2.2).
- **Безопасность**: `DEBUG=False` в проде, `ALLOWED_HOSTS` строится из `VIRTUAL_HOST` (fail-fast если пусто).

## Жизненный цикл запроса

```
COLLECTING (собираем голоса)
    ├─ (все согласуют, threshold=all) ────→ APPROVED
    ├─ (>50%, threshold=majority) ────────→ APPROVED
    ├─ (кто-то отклоняет, threshold=all)──→ REJECTED
    └─ (инициатор нажимает «Отменить») ───→ CANCELLED
```

> Состояние `EXPIRED` присутствует в более старых черновиках доки, но в текущей реализации **не используется** — таймаута голосования нет. Если потребуется, реализация — это cron, который читает `appr_requests` с `CREATED_AT < now() - TTL` и переводит в `CANCELLED`. (исправляет ARCH-3)

## Поток данных: создание запроса

```
1. Пользователь нажимает иконку приложения в чате
2. iframe Nuxt-app поднимается, b24jssdk даёт OAuth-bundle
3. Frontend → /api/auth/get-token  (выдаём JWT)
4. Пользователь заполняет CreateForm (комментарий, согласующие, файлы)
5. Frontend → POST /api/approval/create  (multipart, JWT в Authorization)
6. Backend:
   6.1. validate_create_form + validate_uploaded_files (Sprint 2.3)
   6.2. ApprovalService.create():
        - upload_file → Bitrix24 Disk (для каждого вложения)
        - entity.item.add → appr_requests
        - imbot.message.add → ставим сообщение в исходный чат и
          в личные чаты согласующих (best-effort, ошибки → bot_issue)
        - entity.item.update → запоминаем bot_message_id(s)
   6.3. Возвращаем JSON: {id, status, bot_message_id(s), bot_issue?}
7. Frontend: показывает успех; если bot_issue — баннер пользователю
```

## Поток данных: голосование

```
1. Согласующий нажимает кнопку «Согласовать» или «Отклонить» в боте
2. Bitrix24 отправляет webhook ONIMCOMMANDADD на /api/approval/vote
   (auth-bundle прикреплён в payload — без БД нам этого хватает)
3. Backend:
   3.1. _extract_vote_payload  (поддержка legacy и event-формата)
   3.2. _resolve_account → B24AuthContext.from_webhook_auth(auth)
   3.3. ApprovalService.handle_vote():
        - rules.is_valid_voter (initiator не может голосовать)
        - entity.item.add (или update) → approval_votes
        - get_votes() → пост-проверка против race-condition (Sprint 2.1)
        - Пересчёт агрегатов (approve_count, reject_count, pending_count)
        - rules.compute_status → новый STATUS
        - entity.item.update → appr_requests.STATUS
        - imbot.message.update → обновлённый текст + кнопки
        - imbot.answer_command → toast пользователю в Bitrix24
4. Webhook возвращает 200 OK Bitrix24-у
```

> Race-condition защита: между `entity.item.add` (голос) и `get_votes()` (агрегация) теоретически могут вклиниться параллельные голоса. С Sprint 2.1 после агрегации делается `get_votes` повторно — если число голосов изменилось, результат пересчитывается, прежде чем мы трогаем `appr_requests.STATUS`. (исправляет ARCH-4)

## Паттерны проектирования

### JWT-Bearer (Sprint 2.2)

JWT сериализует весь OAuth-bundle в payload и подписывается HMAC-SHA256 ключом `JWT_SECRET`. Срок жизни — 60 минут; ключи payload'а:

```
uid  → user_id (b24_user_id)
mid  → member_id
dom  → domain_url
tok  → access_token
rfr  → refresh_token
oxp  → OAuth expires (unix timestamp)
oxpi → OAuth expires_in
atk  → application_token
av   → application_version
st   → app status
adm  → is_b24_user_admin
sc   → current_scope
iat  → JWT issued-at
exp  → JWT expiration
```

> Ключи `oxp`/`oxpi` (а не `exp`/`expi`) — намеренный выбор: иначе `oxp` коллизировал бы со стандартным JWT-claim `exp`, и OAuth-`expires` затирался бы на roundtrip. Зафиксировано unit-тестом `test_jwt_roundtrip_preserves_identity`.

### Command Pattern (кнопки клавиатуры)

```python
button = {
    "TEXT": "Согласовать",
    "COMMAND": "approval_vote",
    "COMMAND_PARAMS": json.dumps({"request_id": "123", "decision": "APPROVE"}),
}
```

`b24_client.py` имеет fallback: если Bitrix24 ругается на `KEYBOARD: dict` — повторяет с `KEYBOARD: list`.

### Observer Pattern (обновления сообщений)

После каждого голоса агрегат пересчитывается, и **то же самое** сообщение бота обновляется через `imbot.message.update`. Это сохраняет историю чата чистой и не плодит уведомлений.

### State Machine (статусы запроса)

См. жизненный цикл выше. Переходы реализованы в `approvals/rules.py::compute_status`.

## Оптимизация

### Кэш `app.option`

`ApprovalB24Client` (Sprint 2.2) имеет per-instance `_option_cache: dict[str, str]` — за один HTTP-запрос к нашему бэку каждая опция (например, `bot_id`, `storages_ready`) читается из Bitrix24 максимум один раз.

### Кэш bot_id

`ApprovalService._bot_id_cache` (Sprint 2.2) — `_get_bot_id()` ходит в Bitrix24 только один раз на жизнь сервиса (= один HTTP-запрос).

### Batching `user.get`

`get_user_names` (Sprint 2.1) использует `FILTER[ID]` массивом, заменяя N+1 на один вызов.

### Bitrix24 entity limits

Entity API не позволяет произвольных индексов; в `get_votes` мы фильтруем по `REQUEST_ID` (это предусмотренный паттерн). С Sprint 2.2 `entity.items.get + локальная агрегация` используется в `list_requests`, чтобы избежать N+1 при выводе списка. (исправляет ARCH-1)

### Frontend

- Pinia stores: `api` (HTTP) и `approvals` (state).
- `import.meta.dev` guard вокруг console-логов (Sprint 2.3) — продакшн консоль чистая.
- i18n: 82 ключа в RU и EN (paroled CI'ем — `i18n-parity` job).

## Безопасность

| Контроль | Реализация |
|----------|------------|
| Аутентификация фронта | JWT-Bearer (HS256), `JWT_SECRET ≥ 32 байт` |
| Аутентификация webhook'а | OAuth-bundle в payload + `application_token` сверка (Sprint 2.2 P2-1) |
| Авторизация на чтение | `approval_detail`: 403 для всех, кроме initiator/approver/admin (Sprint 2.2 SEC-P1-2) |
| Авторизация на голос | `rules.is_valid_voter` (initiator не голосует за себя) |
| CSRF | Не применимо: только Bearer-токен; `csrf_exempt` намеренно (Sprint 2.2) |
| CORS | Whitelist `^https://[a-z0-9\-]+\.bitrix24\.[a-z]+$` (Sprint 2.2) |
| Размер/тип файлов | Whitelist расширений + 25 МиБ × 10 файлов (Sprint 2.3) |
| `DEBUG` | ENV-driven, default `False` (Sprint 2.2) |
| `ALLOWED_HOSTS` | Из `VIRTUAL_HOST`; прод fail-fast если пусто |
| HTTPS | На уровне reverse-proxy / Timeweb |

---

**Последнее обновление**: апрель 2026, Sprint 2.3.
