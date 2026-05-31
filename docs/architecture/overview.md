# Архитектура: Краткий обзор

Общая архитектура приложения **Приложение для согласований в чате Bitrix24** с фокусом на взаимодействие компонентов, потоки данных и интеграцию с Bitrix24.

Для детальной архитектуры см. [../ru/ARCHITECTURE.md](../ru/ARCHITECTURE.md).

---

## 1. Общая система

```
┌─────────────────────────────────────────────────────────────┐
│                     Bitrix24 Портал                         │
│  ├─ Чат (IM_TEXTAREA placement) — точка входа             │
│  ├─ Бот (imbot) — публикация сообщений                     │
│  ├─ Entity Storage — хранилище (appr_requests, approval_votes) │
│  └─ Disk — файлы вложений                                   │
└──────────────┬──────────────────────────────────────────────┘
               │ REST API + Webhooks
     ┌─────────┴──────────┐
     │                    │
┌────▼─────────────┐  ┌──▼─────────────────┐
│ Frontend         │  │ Backend            │
│ (Vue 3/Nuxt 3)   │  │ (Python/Django)    │
│ ├─ Pages         │  │ ├─ REST API        │
│ ├─ Components    │  │ ├─ B24 Client      │
│ ├─ Pinia stores  │  │ └─ Stateless       │
│ └─ Composables   │  │    (no DB)         │
└──────────────────┘  └────────────────────┘
```

---

## 2. Слои системы

### 2.1 Фронтенд (Vue 3 + Nuxt 3 + TypeScript)

**Назначение**: UI для создания запросов, голосования, просмотра статусов.

**Компоненты**:
- **CreateForm.vue** — форма создания запроса (комментарий, список согласующих, файл).
- **RequestCard.vue** — карточка запроса (отображение статуса, итогов голосования).
- **VoteStatus.vue** — детальный статус голосования (списки одобривших/отклонивших).
- **StatusBadge.vue** — значок статуса (зелёный/красный).
- **EventLog.vue** — история событий запроса.
- **FileUploadArea.vue** — загрузка и отображение файлов.

**Pinia stores**:
- `approvalsStore` — запросы и их состояние (myRequests, incomingRequests).
- `apiStore` — HTTP-клиент для backend API.
- `userStore` — информация о текущем пользователе.
- `userSettingsStore` — персональные настройки.
- `appSettingsStore` — конфигурация приложения.
- `pageStore` — состояние страницы.

**Composables**:
- `useApproval()` — операции с запросами (create, list, getById, cancel).
- `useApprovalFiles()` — управление вложениями (add, remove, drag-drop).
- `useBackend()` — инициализация сессии backend.
- `useAppInit()` — инициализация приложения (OAuth, логирование).

**Страницы**:
- `index.client.vue` — основная страница (список "Мои"/"Входящие", форма создания).
- `install.client.vue` — установка приложения (инициализация на портале).

### 2.2 Хранение данных (Bitrix24 Entity Storage)

**Назначение**: долгоживущее хранилище данных приложения (единственный persistence layer).

**Сущности**:

#### `appr_requests`
Метаданные запроса согласования.

| Поле | Тип | Описание |
|------|-----|---------|
| `ID` | string | Уникальный идентификатор |
| `INITIATOR_ID` | string | ID создателя запроса |
| `COMMENT` | text | Описание запроса |
| `APPROVER_IDS` | JSON-string | Массив ID согласующих |
| `THRESHOLD_TYPE` | string | `all` (единогласно) или `majority` (большинство) |
| `STATUS` | string | `collecting` / `approved` / `rejected` / `cancelled` |
| `DIALOG_ID` | string | ID чата (контекст создания) |
| `BOT_MESSAGE_ID` | string | ID последнего сообщения бота |
| `BOT_MESSAGE_IDS` | JSON-string | Все сообщения бота (для поддержки multi-dialog) |
| `BOT_DIALOG_IDS` | JSON-string | Чаты, где был запрос |
| `DISK_FOLDER_ID` | string | Папка на Диске (для вложений) |
| `FILE_IDS` | JSON-string | ID загруженных файлов |
| `FILE_NAMES` | JSON-string | Имена файлов (отображаемые) |
| `CREATED_AT` | string | ISO timestamp создания |
| `UPDATED_AT` | string | ISO timestamp обновления |

#### `approval_votes`
Решения отдельных согласующих.

| Поле | Тип | Описание |
|------|-----|---------|
| `ID` | string | Уникальный идентификатор |
| `REQUEST_ID` | string | Внешний ключ → `appr_requests.ID` |
| `USER_ID` | string | ID согласующего |
| `DECISION` | string | `APPROVE` или `REJECT` |
| `COMMENT` | text | Опциональный комментарий |
| `VOTED_AT` | string | ISO timestamp голоса |

**Оптимизация**: Bitrix24 Entity Storage нативно поддерживает только `FILTER` и `SORT` (нет индексов). Для часто выполняемых запросов (список по инициатору/согласующему) используется фильтр по полю `INITIATOR_ID` или `APPROVER_IDS`.

### 2.3 Синхронизация данных

**Flow создания запроса**:
1. Frontend отправляет POST `/api/approval/create` с формой (comment, approver_ids, dialog_id, files).
2. Backend валидирует данные.
3. Backend создаёт запись в `appr_requests` (статус `collecting`).
4. Backend загружает файлы в `disk.folder.uploadfile` (если есть).
5. Backend публикует сообщение `imbot.message.add` с кнопками голосования в чат.
6. Backend обновляет `appr_requests.BOT_MESSAGE_ID` и `BOT_DIALOG_IDS`.
7. Frontend закрывает форму создания и обновляет список запросов.

**Flow голосования**:
1. Согласующий нажимает кнопку в сообщении бота.
2. Bitrix24 отправляет webhook `ONIMCOMMANDADD` на backend.
3. Backend извлекает контекст (requestId, userId, decision).
4. Backend создаёт/обновляет запись в `approval_votes`.
5. Backend пересчитывает агрегаты (approvedCount, rejectedCount, pendingCount).
6. Если статус изменился → backend обновляет `imbot.message.update` и `appr_requests.STATUS`.
7. Frontend опционально обновляет список запросов (по WebSocket или polling).

### 2.4 Backend API (Stateless)

**Назначение**: координация между frontend и Bitrix24, обработка бизнес-логики.

**Архитектура**: Полностью stateless (нет собственной БД). Все OAuth-токены хранятся в JWT (от фронта) или webhook-payload (от Bitrix24) и существуют только на время одного HTTP-запроса.

**Endpoints**:

| Метод | URL | Назначение |
|-------|-----|-----------|
| `POST` | `/api/approval/create` | Создание запроса |
| `GET` | `/api/approval/{id}` | Получение деталей |
| `GET` | `/api/approval/list/{role}` | Список (initiator/approver) |
| `POST` | `/api/vote/handle` | Запись голоса |
| `POST` | `/api/install` | Инициализация при установке |

Для полного справочника см. [../ru/API.md](../ru/API.md).

**Ключевые компоненты**:
- `B24AuthContext` — парсинг и валидация JWT/webhook-токенов.
- `ApprovalService` — бизнес-логика (расчёт статусов, валидация).
- `ApprovalB24Client` — wrapper для Bitrix24 REST API.

### 2.5 Интеграция с Bitrix24

**OAuth**:
- Frontend инициализируется через `@bitrix24/b24jssdk` (iframe в Bitrix24).
- Bitrix24 автоматически передаёт OAuth-токены фронту.
- Frontend делегирует backend'у через JWT (HS256, 60 мин).

**API-методы, используемые приложением**:

| Метод | Назначение |
|-------|-----------|
| `placement.bind` | Регистрация встройки в `IM_TEXTAREA` |
| `entity.add` | Создание хранилища (appr_requests, approval_votes) |
| `entity.item.add` | Создание запроса/голоса |
| `entity.item.update` | Обновление запроса/голоса |
| `entity.item.get` | Чтение запроса/голоса |
| `entity.item.list` | Список запросов по фильтру |
| `disk.folder.addsubfolder` | Создание папки для вложений |
| `disk.folder.uploadfile` | Загрузка файла |
| `imbot.register` | Регистрация бота |
| `imbot.message.add` | Публикация сообщения с кнопками |
| `imbot.message.update` | Обновление сообщения (статусы, итоги) |
| `user.get` | Получение информации о пользователе |
| `user.search` | Поиск пользователей для выбора согласующих |

**Webhooks**:
- `ONIMCOMMANDADD` — событие нажатия кнопки в сообщении бота.
- `ONAPPUNINSTALL` — событие удаления приложения (cleanup).

---

## 3. Технологический стек

| Слой | Технология | Версия |
|------|-----------|--------|
| Frontend | Vue 3 + Nuxt 3 | Latest |
| Frontend-UI | B24 UI Kit | Latest (@bitrix24/b24ui-nuxt) |
| Frontend-CSS | Tailwind CSS | v3+ |
| Frontend-State | Pinia | v2+ |
| Backend | Python | 3.11+ |
| Backend-Framework | Django | 4.2+ |
| Backend-SDK | b24pysdk | Latest |
| Storage | Bitrix24 Entity Storage | REST API v1 |
| Files | Bitrix24 Disk | REST API v1 |
| Infrastructure | Docker, Docker Compose | Latest |
| Reverse Proxy (Prod) | Nginx | Latest |

---

## 4. Взаимодействие компонентов

### Сценарий: Создание запроса

```
Пользователь в чате
    ↓
Нажимает иконку приложения (IM_TEXTAREA)
    ↓ (Frontend открывает CreateForm.vue)
Fills form (comment, approvers, file)
    ↓ (useApproval.create())
Frontend отправляет FormData на /api/approval/create
    ↓ (Backend ApprovalService)
Backend валидирует, создаёт appr_requests в entity
    ↓ (Если файл: disk.folder.uploadfile)
Backend публикует imbot.message.add с кнопками
    ↓ (Backend обновляет appr_requests.BOT_MESSAGE_ID)
✅ Запрос создан и виден в чате
```

### Сценарий: Голосование

```
Согласующий в чате видит сообщение бота
    ↓
Нажимает кнопку "Согласовать" или "Отклонить"
    ↓ (Bitrix24 отправляет webhook ONIMCOMMANDADD)
Backend получает webhook
    ↓ (Backend ApprovalService)
Backend валидирует и создаёт/обновляет approval_votes
    ↓ (Backend пересчитывает статус)
Backend обновляет imbot.message.update (новые итоги)
    ↓ (Backend обновляет appr_requests.STATUS если изменился)
✅ Итоги обновлены в сообщении бота
```

---

## 5. Безопасность

- **OAuth 2.0** через Bitrix24 (встроенный механизм портала).
- **JWT** для делегирования токенов backend'у (HS256, 60 мин таймаут).
- **HTTPS обязателен** (требование Bitrix24 API).
- **CSRF-защита** на уровне Bitrix24 (автоматическая).
- **Валидация входных данных** на backend (типы, длины, скоупы).
- **Логирование** всех операций для аудита.

---

## 6. Масштабирование

- **Горизонтальное масштабирование**: Backend stateless, легко добавлять инстансы.
- **Кэширование**: Frontend кэширует список запросов (Pinia store).
- **Bitrix24 Entity Limits**: до 100K записей в одном хранилище (достаточно для MVP).
- **Подробнее**: см. [../ru/ARCHITECTURE.md](../ru/ARCHITECTURE.md) (раздел "Оптимизация и масштабирование").

---

## Ссылки

- **Детальная архитектура**: [../ru/ARCHITECTURE.md](../ru/ARCHITECTURE.md)
- **Frontend документация**: [../ru/FRONTEND.md](../ru/FRONTEND.md)
- **REST API**: [../ru/API.md](../ru/API.md)
- **Bitrix24 интеграция**: [../ru/BITRIX24_INTEGRATION.md](../ru/BITRIX24_INTEGRATION.md)
- **Карта функций**: [feature-map.md](feature-map.md)
