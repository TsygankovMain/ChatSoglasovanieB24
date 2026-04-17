# Approval Workflow — Design Spec

**Дата:** 2026-04-17
**Статус:** Approved

---

## Цель

Приложение для Bitrix24 чата, которое позволяет создавать запросы на согласование прямо из интерфейса. Инициатор заполняет форму, бот публикует сообщение с кнопками, согласующие голосуют одним кликом. Статус обновляется автоматически.

**Основная платформа:** мобильное приложение Bitrix24.

---

## Принятые решения

| Вопрос | Решение |
|--------|---------|
| Бэкенд | Python / Django |
| Хранение данных | Bitrix24 Entity Storage (`entity.*`) — без локальной БД |
| Файлы | Bitrix24 Disk — отдельная папка на каждый запрос |
| Роль бэкенда | Слой бизнес-правил (не тонкий прокси) |
| Форма | Одна страница (не wizard) |
| Бот | Bot Platform 2.0 (`imbot.*` + `keyboard`) |
| UI | B24 UI Kit (`@bitrix24/b24ui-nuxt`), mobile-first |
| Порог одобрения | Задаётся инициатором в форме |

---

## Архитектура

```
Nuxt 3 (тонкий клиент)
  │  JWT
  ▼
Django API (бизнес-логика, единственная точка правды)
  │  Bitrix24 REST API
  ▼
Bitrix24
  ├── Entity Storage  — хранение запросов и голосов
  ├── Disk            — файлы согласований
  └── Bot Platform 2.0 — сообщения с кнопками в чате
```

**Входящий webhook (голосование):**
```
Bitrix24 (клик по кнопке) → POST /api/vote/handle → Django → правила → B24 REST
```

Фронтенд не обращается напрямую к Bitrix24 REST. Все мутации — через Django.

---

## Entity Storage

### entity: `approval_requests`

| Поле | Тип | Описание |
|------|-----|----------|
| `PROPERTY_INITIATOR_ID` | string | ID пользователя-инициатора |
| `PROPERTY_COMMENT` | string | Текст запроса |
| `PROPERTY_APPROVER_IDS` | string (JSON) | Список ID согласующих |
| `PROPERTY_THRESHOLD_TYPE` | string | `all` или `majority` |
| `PROPERTY_STATUS` | string | `collecting` / `approved` / `rejected` / `cancelled` |
| `PROPERTY_BOT_MESSAGE_ID` | string | ID бот-сообщения в чате |
| `PROPERTY_DISK_FOLDER_ID` | string | ID папки на диске |
| `PROPERTY_FILE_IDS` | string (JSON) | Список ID файлов на диске |
| `PROPERTY_CREATED_AT` | string (ISO8601) | Дата создания |

### entity: `approval_votes`

| Поле | Тип | Описание |
|------|-----|----------|
| `PROPERTY_REQUEST_ID` | string | ID запроса |
| `PROPERTY_USER_ID` | string | ID проголосовавшего |
| `PROPERTY_DECISION` | string | `approve` или `reject` |
| `PROPERTY_COMMENT` | string | Комментарий к голосу (опционально) |
| `PROPERTY_VOTED_AT` | string (ISO8601) | Время голосования |

---

## Бизнес-правила (rules.py)

1. **Инициатор не может голосовать** — если `userId == INITIATOR_ID`, отклонить.
2. **Один голос на пользователя** — проверить `approval_votes` по `REQUEST_ID + USER_ID`.
3. **Только согласующие голосуют** — если `userId` не в `APPROVER_IDS`, отклонить.
4. **Мгновенный отказ** — первый голос `reject` → статус `rejected`, кнопки убираются.
5. **Порог одобрения:**
   - `all` — все согласующие проголосовали `approve`
   - `majority` — более 50% согласующих проголосовали `approve`
6. **Неактивный запрос** — если статус не `collecting`, голос игнорируется.

---

## Django API Endpoints

### `POST /api/approval/create`
**Права:** только авторизованный пользователь (JWT)
**Формат:** `multipart/form-data`
**Тело:**
```json
{
  "comment": "string (required)",
  "approver_ids": "[1, 2, 3] (required)",
  "threshold_type": "all | majority (required)",
  "files": "file[] (optional)"
}
```
**Последовательность:**
1. Валидация JWT → извлечь `initiator_id`
2. `disk.folder.add` → создать папку `/Согласования/{timestamp}-{initiator_id}`
3. `disk.folder.uploadfile` × N → загрузить файлы, собрать `file_ids`
4. `entity.item.add` (approval_requests) → статус `collecting`
5. `imbot.message.add` → опубликовать сообщение с Bot Platform 2.0 keyboard
6. `entity.item.update` → записать `bot_message_id`
7. Вернуть `{id, status, bot_message_id}`

---

### `GET /api/approval/list`
**Права:** JWT
**Query:** `?role=initiator|approver`
Возвращает список запросов текущего пользователя (как инициатора или согласующего).

---

### `GET /api/approval/:id`
**Права:** JWT
Детали запроса + список голосов.

---

### `POST /api/vote/handle`
**Права:** Bitrix24 webhook signature
**Тело (от Bot Platform 2.0):**
```json
{
  "BOT_ID": "...",
  "USER_ID": "...",
  "MESSAGE_ID": "...",
  "COMMAND": "approve | reject"
}
```
**Последовательность:**
1. Найти запрос по `MESSAGE_ID`
2. Применить бизнес-правила (rules.py)
3. `entity.item.add` (approval_votes) → записать голос
4. Пересчитать статус
5. `entity.item.update` (approval_requests) → обновить статус
6. `imbot.message.update` → обновить счётчики; если завершён — убрать кнопки

---

### `POST /api/approval/cancel`
**Права:** JWT, только инициатор
Установить статус `cancelled`, убрать кнопки из бот-сообщения.

---

### `POST /api/install`
Регистрация бота, привязка placement `CRM_DEAL_DETAIL_TAB`, создание entity storage.

### `GET /api/health`
Health check.

---

## Структура Django-кода

```
backends/python/api/
├── approvals/
│   ├── views.py          # DRF ViewSets / APIView
│   ├── services.py       # ApprovalService (оркестрирует шаги)
│   ├── rules.py          # ApprovalRules (изолированная логика)
│   ├── b24_client.py     # обёртка всех вызовов B24 REST
│   ├── serializers.py    # DRF serializers
│   └── urls.py
├── bot/
│   ├── handler.py        # VoteWebhookHandler
│   ├── messages.py       # шаблоны текста бот-сообщений
│   └── keyboard.py       # Bot Platform 2.0 keyboard builder
├── disk/
│   └── service.py        # DiskService: create_folder, upload_file
├── core/
│   ├── auth.py           # JWT middleware
│   └── b24_entity.py     # helpers для entity.item.*
└── config/
    ├── settings.py
    └── urls.py
```

---

## Структура Nuxt-кода

```
frontend/app/
├── pages/
│   ├── index.client.vue                              # список запросов (мои / входящие)
│   └── handler/
│       └── placement-crm-deal-detail-tab.client.vue  # вход из CRM сделки
├── components/
│   ├── approval/
│   │   ├── CreateForm.vue    # форма (одна страница, B24UI компоненты)
│   │   ├── RequestCard.vue   # карточка запроса в списке
│   │   ├── VoteStatus.vue    # прогресс-бар голосов
│   │   └── StatusBadge.vue   # бейдж: collecting / approved / rejected
│   └── FileUploadArea.vue    # загрузка файлов
├── composables/
│   ├── useApproval.ts        # create, list, cancel
│   └── useFileUpload.ts      # multipart upload
├── stores/
│   └── approvals.ts          # Pinia store
└── locales/
    ├── ru.json
    └── en.json
```

---

## Поля формы CreateForm.vue

| Поле | Компонент B24UI | Обязательное |
|------|----------------|--------------|
| Комментарий | `UTextarea` | Да |
| Согласующие | `B24UserSelector` (мультиселект) | Да |
| Правило одобрения | `USelect` / toggle: "Все" / "Большинство" | Да |
| Прикрепить файлы | `FileUploadArea` (drag & drop + кнопка) | Нет |

---

## Бот-сообщение (Bot Platform 2.0)

**Текст:**
```
📋 Запрос на согласование #{id}

{comment}

👤 Инициатор: {name}
📎 Файлы: {file_names | "нет"}
⚙️ Правило: {threshold_label}

Голоса: ✓ {approve_count} / ✗ {reject_count} из {total}
Ожидает: {pending_names}
```

**Keyboard (Bot Platform 2.0):**
```json
[
  [
    {"TEXT": "✅ Одобрить", "COMMAND": "approve"},
    {"TEXT": "❌ Отклонить", "COMMAND": "reject"}
  ]
]
```
После завершения (approved/rejected/cancelled) кнопки убираются через `imbot.message.update`.

---

## Технические риски и решения

| Риск | Решение |
|------|---------|
| Двойное голосование при параллельных кликах | Проверка голоса в `approval_votes` перед записью; при дубликате — игнорировать |
| Бот не зарегистрирован | `POST /api/install` проверяет наличие бота перед регистрацией |
| Entity Storage лимиты API | Использовать `batch` запросы где возможно |
| Файл слишком большой | Ограничение на фронте + обработка ошибки от B24 Disk |

---

## Out of Scope (в этой версии)

- Многошаговые согласования
- Делегирование голоса
- SLA и дедлайны
- Уведомления по email
- Аналитика и отчёты
