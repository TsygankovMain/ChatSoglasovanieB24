# Feature Map (Карта функций → файлы)

Полная карта функций приложения со ссылками на реализующие их файлы, компоненты и функции.

**Назначение**: быстро найти, где реализована та или иная функция, и переходить к коду для доработки.

**Примечание**: все пути относительны к корню репозитория. Номера строк носят ориентировочный характер и могут дрейфовать при обновлениях кода.

---

## 1. Создание запроса согласования

| Фича | Компонент | Файл | Строки | Описание |
|------|-----------|------|--------|---------|
| **Точка входа** | — | `frontend/app/pages/index.client.vue` | 24-31 | Переменная `showCreateForm` и функция переключения формы; `isInChat` проверка контекста. |
| **UI Форма** | CreateForm.vue | `frontend/app/components/approval/CreateForm.vue` | 1-150 | Компонент формы (поля: comment, approverIds, thresholdType). Валидация, обработчик onSubmit. |
| **Выбор согласующих** | EmployeeSelector | `frontend/app/components/approval/CreateForm.vue` | 50-80 | Выпадающий список с поиском (B24 `user.search` интеграция). |
| **Загрузка файлов** | FileUploadArea.vue | `frontend/app/components/FileUploadArea.vue` | 1-100 | Drag-drop зона, управление файлами (add, remove). |
| **Composable (бизнес-логика)** | useApproval() | `frontend/app/composables/useApproval.ts` | 1-40 | Функция `create()`: формирует FormData, вызывает store.create(). |
| **Store операция** | approvalsStore | `frontend/app/stores/approvals.ts` | 60-120 | Функция `create()`: POST на `/api/approval/create`, обновляет myRequests. |
| **HTTP запрос** | apiStore | `frontend/app/stores/api.ts` | 50-100 | Функция `approvalCreate()`: formData → backend. |
| **Backend endpoint** | — | `backends/python/api/approvals/views.py` | 158-204 | Функция `approval_create()`: POST `/api/approval/create`, валидация, вызов service.create(). |
| **Service бизнес-логика** | ApprovalService | `backends/python/api/approvals/services.py` | 244-408 | Метод `create()`: создание запроса, загрузка файлов, публикация бот-сообщений. |
| **Entity операция** | ApprovalB24Client | `backends/python/api/approvals/b24_client.py` | 110-131 | Метод `create_request_item()`: `entity.item.add` в ENTITY_REQUESTS. |
| **Бот публикация** | ApprovalService | `backends/python/api/approvals/services.py` | 316-408 | В методе `create()`: цикл вызовов `publish_bot_message()` к каждому согласующему. |
| **Формирование текста** | — | `backends/python/api/bot/messages.py` | 38-99 | Функция `build_approval_message()`: формирует текст сообщения с деталями запроса. |
| **Формирование клавиатуры** | — | `backends/python/api/bot/keyboard.py` | 4-9 | Функция `build_vote_keyboard()`: создаёт кнопки "Одобрить" / "Отклонить". |
| **Успех** | — | `frontend/app/pages/index.client.vue` | 53-70 | Хук `onCreated`: закрытие формы (closeApplication), обновление списка. |

---

## 2. Список "Мои запросы" / "Входящие"

| Фича | Компонент | Файл | Строки | Описание |
|------|-----------|------|--------|---------|
| **Табы** | — | `frontend/app/pages/index.client.vue` | 24 | `activeTab: ref<'my' \| 'incoming'>('my')` |
| **Загрузка данных** | useDashboard | `frontend/app/pages/index.client.vue` | 17-22 | Composable для управления состоянием загрузки (isLoading, load). |
| **Fetch "Мои"** | useApproval() | `frontend/app/pages/index.client.vue` | 46-51 | `approval.list()` → store.fetchMyRequests(). |
| **Fetch "Входящие"** | useApproval() | `frontend/app/pages/index.client.vue` | 46-51 | `approval.listIncoming()` → store.fetchIncomingRequests(). |
| **Store: Fetch My** | approvalsStore | `frontend/app/stores/approvals.ts` | — | Функция `fetchMyRequests()`: вызывает apiStore для GET `/api/approval/list/initiator`. |
| **Store: Fetch Incoming** | approvalsStore | `frontend/app/stores/approvals.ts` | — | Функция `fetchIncomingRequests()`: вызывает apiStore для GET `/api/approval/list/approver`. |
| **HTTP GET** | apiStore | `frontend/app/stores/api.ts` | — | Функция `approvalList()`: GET `/api/approval/list/{role}` через HTTP-клиент. |
| **Backend endpoint** | — | `backends/python/api/approvals/views.py` | 211-218 | Функция `approval_list()`: GET `/api/approval/list/{role}`, вызывает service.list_requests(). |
| **Service логика списка** | ApprovalService | `backends/python/api/approvals/services.py` | 410-415 | Метод `list_requests()`: филтрует по инициатору или согласующему, возвращает composed запросы. |
| **Entity запрос** | ApprovalB24Client | `backends/python/api/approvals/b24_client.py` | 190-208 | Методы `get_requests_by_initiator()` и `get_requests_as_approver()`: entity.item.get с фильтром. | |
| **Отображение** | RequestCard.vue | `frontend/app/components/approval/RequestCard.vue` | 1-200 | Компонент карточки (статус, инициатор, согласующие, итоги). |
| **Пересчёт размера** | fitWindow() | `frontend/app/pages/index.client.vue` | 37-43 | Вызов `$b24.parent.fitWindow()` для адаптации высоты iframe. |

---

## 3. Голосование / Статусы

| Фича | Компонент | Файл | Строки | Описание |
|------|-----------|------|--------|---------|
| **Кнопки голосования (в форме)** | VoteActionButtons | `frontend/app/components/approval/VoteStatus.vue` | 50-100 | Кнопки "Согласовать" / "Отклонить" / "Запросить уточнение". |
| **Обработчик клика** | — | `frontend/app/components/approval/VoteStatus.vue` | 80-120 | Функция `onVote(decision)`: отправляет POST на `/api/vote/handle`. |
| **Store операция** | approvalsStore | `frontend/app/stores/approvals.ts` | 140-180 | Функция `submitVote(requestId, decision, comment)`: store.submitVote(). |
| **HTTP запрос** | apiStore | `frontend/app/stores/api.ts` | 200-230 | Функция `submitVote()`: POST `/api/vote/handle`. |
| **Backend endpoint** | — | `backends/python/api/approvals/views.py` | 262-344 | Функция `vote_handle()`: POST (webhook ONIMCOMMANDADD), парсит payload, вызывает service.handle_vote(). |
| **Vote обработка** | ApprovalService | `backends/python/api/approvals/services.py` | 458-630 | Метод `handle_vote()`: валидация, создание/обновление голоса, пересчёт статуса, обновление сообщений. |
| **Пересчёт статуса** | rules (модуль) | `backends/python/api/approvals/rules.py` | — | Функции `compute_new_status()`: логика правил (all/majority), определение нового статуса. |
| **Сохранение голоса** | ApprovalB24Client | `backends/python/api/approvals/b24_client.py` | 212-240 | Методы `add_vote()`, `find_vote()`, `get_votes()`: операции с entity ENTITY_VOTES. |
| **Обновление бот-сообщения** | ApprovalB24Client | `backends/python/api/approvals/b24_client.py` | 302-319 | Метод `update_bot_message()`: `imbot.message.update` с новым текстом и клавиатурой. | |
| **Статус-бэйдж (UI)** | StatusBadge.vue | `frontend/app/components/approval/StatusBadge.vue` | 1-80 | Компонент отображения статуса (цвет, иконка, текст). |
| **Детали голосования** | VoteStatus.vue | `frontend/app/components/approval/VoteStatus.vue` | 1-50 | Отображение списков одобривших/отклонивших с аватарами. |

---

## 4. Отмена запроса

| Фича | Компонент | Файл | Строки | Описание |
|------|-----------|------|--------|---------|
| **Кнопка отмены** | RequestCard.vue | `frontend/app/components/approval/RequestCard.vue` | — | Кнопка "Отменить" видна только для инициатора и только если статус = collecting. |
| **Store функция** | approvalsStore | `frontend/app/stores/approvals.ts` | — | Функция `cancel(id)`: POST `/api/approval/cancel`. |
| **HTTP запрос** | apiStore | `frontend/app/stores/api.ts` | — | Функция `approvalCancel(id)`: POST `/api/approval/cancel`. |
| **Backend endpoint** | — | `backends/python/api/approvals/views.py` | 247-259 | Функция `approval_cancel()`: POST `/api/approval/cancel`, валидация, вызов service.cancel(). |
| **Service отмена** | ApprovalService | `backends/python/api/approvals/services.py` | 632-685 | Метод `cancel()`: проверка прав инициатора, обновление статуса, очистка клавиатур в сообщениях. |
| **Entity обновление** | ApprovalB24Client | `backends/python/api/approvals/b24_client.py` | 133-134 | Метод `update_request_item()`: `entity.item.update` для обновления STATUS. |

---

## 5. Вложения (файлы)

| Фича | Компонент | Файл | Строки | Описание |
|------|-----------|------|--------|---------|
| **Composable управления файлами** | useApprovalFiles() | `frontend/app/composables/useApprovalFiles.ts` | 1-60 | Функции: addFiles(), removeFile(), onDrop(), onDragOver(), clear(). |
| **UI компонент** | FileUploadArea.vue | `frontend/app/components/FileUploadArea.vue` | 1-150 | Drag-drop зона, список выбранных файлов, кнопка удаления. |
| **Отправка файлов** | useApproval() | `frontend/app/composables/useApproval.ts` | 10-25 | Функция `create()`: добавляет files в FormData. |
| **Backend обработка** | — | `backends/python/api/approvals/views.py` | 162-204 | Функция `approval_create()`: извлечение files из request.FILES, передача в service. |
| **Service файлы** | ApprovalService | `backends/python/api/approvals/services.py` | 253-272 | В методе `create()`: создание папки на Disk, загрузка файлов, сохранение FILE_IDS в entity. |
| **Disk сервис** | DiskService | `backends/python/api/disk/service.py` | — | Класс для операций с Disk: `create_folder()`, `upload_file()`, `get_folder_files()`. |
| **Отображение файлов** | RequestCard.vue | `frontend/app/components/approval/RequestCard.vue` | 180-220 | Список файлов в детальном окне запроса (ссылки на Disk). |

---

## 6. История событий (Event Log)

| Фича | Компонент | Файл | Строки | Описание |
|------|-----------|------|--------|---------|
| **UI компонент** | EventLog.vue | `frontend/app/components/approval/EventLog.vue` | 1-200 | Лента событий (создание, голоса, отмена) с временем и участниками. |
| **Получение событий** | — | `frontend/app/pages/index.client.vue` | 140-160 | При открытии деталей запроса: `approval.getById(requestId)`. |
| **Store функция** | approvalsStore | `frontend/app/stores/approvals.ts` | 90-120 | Функция `fetchById(id)`: GET `/api/approval/{id}`. |
| **HTTP запрос** | apiStore | `frontend/app/stores/api.ts` | 100-150 | Функция `approvalGet(id)`: GET `/api/approval/{id}`. |
| **Backend endpoint** | — | `backends/python/api/approvals/views.py` | 225-239 | Функция `approval_detail()`: GET `/api/approval/{id}`, проверка прав, возврат composed запроса. |
| **Service композиция** | ApprovalService | `backends/python/api/approvals/services.py` | 417-421 | Метод `get_request()`: получает запрос, голоса, события, собирает полный payload. |
| **Entity операции** | ApprovalB24Client | `backends/python/api/approvals/b24_client.py` | 136-188, 229-240, 268-273 | Методы `get_request_by_id()`, `get_votes()`, `get_events()`: entity.item.get с фильтром. |
| **Форматирование** | — | `backends/python/api/approvals/services.py` | 208-234 | Метод `_compose_request_payload()`: собирает все данные (votes, events, names, files) в один объект. |

---

## 7. Инициализация и установка

| Фича | Компонент | Файл | Строки | Описание |
|------|-----------|------|--------|---------|
| **Composable инициализации** | useAppInit() | `frontend/app/composables/useAppInit.ts` | 1-100 | Инициализация: OAuth, логирование, проверка контекста. |
| **Страница установки** | install.client.vue | `frontend/app/pages/install.client.vue` | 1-150 | UI для установки (выбор портала, согласие с лицензией). |
| **Точка входа индекса** | — | `frontend/app/pages/index.client.vue` | 1-30 | `onMounted`: вызов `initApp()`, получение контекста B24Frame. |
| **Инициализация фронта** | — | `frontend/app/composables/useAppInit.ts` | — | Composable для инициализации: проверка контекста B24Frame, получение токена. |
| **Страница установки** | — | `frontend/app/pages/install.client.vue` | — | UI для установки: выбор портала, валидация placement.bind, кнопка install. |
| **Backend endpoint** | — | `backends/python/api/main/views.py` | 94-150 | Функция `install()`: POST `/api/install`, координирует инициализацию (entity, bot, 3 placement). |
| **Entity создание** | ApprovalB24Client | `backends/python/api/approvals/b24_client.py` | 535-570 | Метод `create_entity_storages()`: `entity.add` для appr_requests, approval_votes, appr_events. |
| **Регистрация бота** | ApprovalB24Client | `backends/python/api/approvals/b24_client.py` | 403-425 | Метод `register_bot()`: `imbot.register`, регистрация vote-команд, сохранение BOT_ID в app.option. |
| **Привязка placement (метод)** | ApprovalB24Client | `backends/python/api/approvals/b24_client.py` | 491-533 | Метод `bind_placement()`: rebind через `placement.unbind`+`placement.bind`. Для контекстных меню options = context/role/extranet. |
| **Точка входа: панель ввода (десктоп)** | — | `backends/python/api/main/views.py` | ~111 | `IM_TEXTAREA` → handler `/` (открывает основное приложение в чате). |
| **Точка входа: меню сообщения (десктоп)** | — | `backends/python/api/main/views.py` | ~117 | `IM_CONTEXT_MENU` → handler `/handler/placement-im-context-menu`. |
| **Точка входа: меню сообщения (мобильное)** | — | `backends/python/api/main/views.py` | ~137 | `IMMOBILE_CONTEXT_MENU` → тот же handler `/handler/placement-im-context-menu` (мобильный аналог IM_CONTEXT_MENU). |
| **Обработчик контекстного меню (фронт)** | — | `frontend/app/pages/handler/placement-im-context-menu.client.vue` | 1-220 | Универсальная страница desktop+mobile: читает DIALOG_ID/MESSAGE_ID, подгружает текст сообщения (im.dialog.messages.get), открывает форму с prefill. |
| **Манифест placements** | — | `app.json` | 24-78 | Декларация 3 встроек: IM_TEXTAREA, IM_CONTEXT_MENU, IMMOBILE_CONTEXT_MENU. |

---

## 8. API интеграция Bitrix24

| Операция | Метод | Файл | Строки | Описание |
|----------|-------|------|--------|---------|
| **Создание хранилища** | entity.add | `backends/python/api/approvals/b24_client.py` | 535-538 | Инициализация appr_requests, approval_votes, appr_events. |
| **Создание записи** | entity.item.add | `backends/python/api/approvals/b24_client.py` | 110-131, 212-220, 244-266 | Методы `create_request_item()`, `add_vote()`, `add_event()`. |
| **Обновление записи** | entity.item.update | `backends/python/api/approvals/b24_client.py` | 133-134, 222-227 | Методы `update_request_item()`, `update_vote()`. |
| **Чтение записи** | entity.item.get | `backends/python/api/approvals/b24_client.py` | 136-138, 235-240 | Методы `get_request_by_id()`, `find_vote()`. |
| **Список записей** | entity.item.get | `backends/python/api/approvals/b24_client.py` | 190-208, 229-233, 268-273 | Методы `get_requests_by_initiator()`, `get_requests_as_approver()`, `get_votes()`, `get_events()`. |
| **Публикация сообщения** | imbot.message.add | `backends/python/api/approvals/b24_client.py` | 277-300 | Метод `publish_bot_message()`. |
| **Обновление сообщения** | imbot.message.update | `backends/python/api/approvals/b24_client.py` | 302-319 | Метод `update_bot_message()`. |
| **Регистрация бота** | imbot.register | `backends/python/api/approvals/b24_client.py` | 403-425 | Метод `register_bot()` с регистрацией vote-команд. |
| **Загрузка файла** | disk.folder.uploadfile | `backends/python/api/disk/service.py` | — | Метод `upload_file()` в DiskService. |
| **Создание папки** | disk.folder.addsubfolder | `backends/python/api/disk/service.py` | — | Метод `create_folder()` в DiskService. |
| **Поиск пользователей** | user.search | `frontend/app/components/approval/CreateForm.vue` | — | Поиск через B24 SDK в выпадающем списке. |
| **Получение пользователя** | user.get | `backends/python/api/approvals/b24_client.py` | 597-644 | Методы `get_user_name()`, `get_user_names()`. |
| **Привязка встройки** | placement.bind | `backends/python/api/approvals/b24_client.py` | 491-533 | Метод `bind_placement()`. |

---

## 9. Stateless Backend & OAuth

| Компонент | Файл | Строки | Описание |
|-----------|------|--------|---------|
| **B24AuthContext** | — | `backends/python/api/main/b24_auth.py` | 25-100 | Класс для парсинга JWT/webhook-payload, валидация токена, хранение в memory per-request. |
| **JWT + Webhook Auth** | — | `backends/python/api/main/b24_auth.py` | 132-137 | Класс-методы `from_jwt()` и `from_webhook_auth()` для создания контекста из разных источников. |
| **Webhook Processor** | — | `backends/python/api/approvals/views.py` | 262-344 | Функция `vote_handle()`: обработчик ONIMCOMMANDADD, парсит payload, создаёт B24AuthContext. |
| **Payload парсинг** | — | `backends/python/api/approvals/views.py` | 42-128 | Функции `_first_event_command()`, `_inflate_bracket_payload()`, `_parse_command_params()`, `_extract_vote_payload()`. |
| **B24 HTTP-клиент** | B24HttpClient | `backends/python/api/core/b24_entity.py` | — | Низкоуровневый HTTP-клиент для REST API Bitrix24, использует B24AuthContext для OAuth. |

---

## 10. Тестирование и QA

| Компонент | Файл | Описание |
|-----------|------|---------|
| **Unit-тесты компонентов** | `frontend/tests/unit/components/` | Jest + Vue Test Utils |
| **Unit-тесты store** | `frontend/tests/unit/stores/` | Pinia тесты |
| **E2E сценарии** | `frontend/tests/e2e/` | Создание → голосование → завершение |
| **Backend unit-тесты** | `backends/python/api/tests/` | Django TestCase |
| **Backend API тесты** | `backends/python/api/tests/integration/` | Полные сценарии |

---

## 11. Дополнительно

### Composables (Frontend)

| Composable | Файл | Назначение |
|-----------|------|-----------|
| `useAppInit()` | `frontend/app/composables/useAppInit.ts` | Инициализация приложения (OAuth, контекст). |
| `useApproval()` | `frontend/app/composables/useApproval.ts` | Операции с запросами (CRUD). |
| `useApprovalFiles()` | `frontend/app/composables/useApprovalFiles.ts` | Управление файлами (add, remove, drag-drop). |
| `useBackend()` | `frontend/app/composables/useBackend.ts` | Сессия с backend (JWT, переинициализация). |

### Stores (Pinia)

| Store | Файл | Ключевые функции |
|-------|------|-----------------|
| `approvalsStore` | `frontend/app/stores/approvals.ts` | fetchMyRequests(), fetchIncomingRequests(), submitVote(), cancel(), create() |
| `apiStore` | `frontend/app/stores/api.ts` | approvalCreate(), approvalGet(), approvalList(), submitVote(), approvalCancel() |
| `userStore` | `frontend/app/stores/user.ts` | currentUser, permissions |
| `userSettingsStore` | `frontend/app/stores/userSettings.ts` | Персональные предпочтения |
| `appSettingsStore` | `frontend/app/stores/appSettings.ts` | Конфигурация приложения (BOT_ID, API_URL) |
| `pageStore` | `frontend/app/stores/page.ts` | Состояние страницы (activeTab, isLoading) |

---

## Примечания

- Все номера строк указаны ориентировочно. Для точного поиска используйте IDE (Ctrl+G для перехода на строку).
- При добавлении новой фичи обновляйте эту карту.
- Относительные пути относятся к корню репозитория.
- Для детальной информации по функции см. документацию в коде (комментарии, docstrings).
