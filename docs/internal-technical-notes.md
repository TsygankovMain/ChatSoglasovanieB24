# Internal Technical Notes

Внутренний рабочий документ для быстрой навигации по архитектуре и задачам.

## 1. Что уже сделано

- Репозиторий starter-кита развернут локально.
- Добавлены проектные документы:
  - `README.md`
  - `docs/specification.md`
  - `docs/internal-technical-notes.md`
  - `CHANGELOG.md`
- Проект очищен от устаревших бэкенд-концепций (Python/Django) и приведен к serverless-модели.
- Успешно исправлен баг с параметром `iconName` при привязке встройки к чату.

## 2. Карта проекта (быстрые ссылки)

| Назначение | Путь |
|---|---|
| Основной frontend entry | `frontend/app/pages/index.client.vue` |
| Layout для placement-страниц | `frontend/app/layouts/placement.vue` |
| Composables | `frontend/app/composables/` |
| Stores | `frontend/app/stores/` |
| Node backend starter | `backends/node/api/server.js` |
| UI Kit guide | `instructions/AI-AGENT-GUIDE-UIKIT.md` |
| JS SDK guide | `instructions/AI-AGENT-GUIDE-JSSDK.md` |

## 3. План модулей приложения

### 3.1 Frontend

- `ApprovalRequestForm`: создание запроса (comment, approvers, file).
- `ApprovalStatusCard`: текущий статус и агрегаты по голосам.
- `VoteActionHandler`: фиксация решения (`APPROVE`/`REJECT`).

### 3.2 Data Layer

- Storage `requests`: карточка запроса.
- Storage `votes`: решения участников.
- Связь: `votes.requestId -> requests.id`.

### 3.3 Bot Layer

- `imbot.message.add`: публикация нового запроса.
- `imbot.message.update`: обновление итогов и статуса.

## 4. REST шпаргалка MVP

| Метод | Для чего |
|---|---|
| `placement.bind` | регистрация входа через `IM_TEXTAREA` |
| `entity.add` | создание storage (первичная инициализация) |
| `entity.item.add` | создание request/vote |
| `entity.item.update` | изменение request/vote |
| `entity.item.get` | чтение request/vote, пересчет агрегатов |
| `disk.folder.uploadfile` | загрузка вложения |
| `imbot.message.add` | отправка сообщения запроса |
| `imbot.message.update` | обновление сообщения после голоса |
| `bizproc.workflow.start` | опциональный post-action после финала |

## 5. Служебные константы

- Status: `DRAFT`, `PUBLISHED`, `COLLECTING`, `APPROVED`, `REJECTED`, `EXPIRED`, `CANCELLED`.
- Decision: `APPROVE`, `REJECT`.
- Placement: `IM_TEXTAREA`.

## 6. Мини-чеклист разработки

1. Поднять форму создания запроса.
2. Подключить валидацию полей формы.
3. Реализовать слой сохранения в `entity.*`.
4. Добавить публикацию bot message.
5. Реализовать обработку голоса и пересчет агрегатов.
6. Обновлять сообщение бота после каждого изменения.

## 7. Мини-чеклист тестов (первые сценарии)

1. Создание запроса без файла.
2. Создание запроса с файлом.
3. Первый же `REJECT` переводит запрос в `REJECTED`.
4. Все `APPROVE` переводят запрос в `APPROVED`.
5. Повторный голос перезаписывает предыдущее решение.
6. Ошибка публикации ботом оставляет request в согласованном техническом состоянии.

## 8. Технические риски

- Нет универсального бота или нет доступа к `imbot`.
- Недостаточные scope (`entity`, `disk`, `placement`, `im`, `imbot`).
- Конкурентные голоса и конфликт обновлений.
- Ограничения режима "без backend" для event-driven расширений.

## 9. Текущие допущения

- Универсальный бот уже существует, `BOT_ID` хранится в настройках приложения.
- MVP использует фиксированный состав согласующих.
- Хранилище `entity.*` покрывает потребности первой версии.
- Основная точка входа пользователя: `IM_TEXTAREA`.

## 10. Troubleshooting

### 10.1 AjaxError 200: Placement not found

1. Проверить конфигурацию хоста в `.env`.
2. Переустановить приложение в Bitrix24 (uninstall -> install), чтобы обновился `placement.bind`.
3. Убедиться, что установка возвращает `steps` без ошибок (`placement`, `bot`, `entity_storages`).

### 10.2 В форме пустой `dialogId`

1. Запускать приложение только из `IM_TEXTAREA` в чате, а не из общего пункта приложений.
2. Проверить debug-блок на странице встройки (`placementOptions`, `dialogId`).
3. Если контекст пустой после обновлений, очистить кеш браузера и повторить установку.

### 10.3 `B24 imbot.message.add: Incorrect keyboard params`

1. Использовать keyboard только с валидными кнопками (`TEXT` + `COMMAND`/`ACTION`/`LINK`).
2. Для `COMMAND` передавать `COMMAND_PARAMS` (минимум `"{}"`).
3. В backend включен fallback отправки: сначала `KEYBOARD: { BUTTONS: [...] }`, при ошибке повтор с `KEYBOARD: [...]`.

### 10.4 `ENTITY` создаётся, но `PROPERTY_VALUES` пустые

1. После `entity.add` нужно создать свойства через `entity.item.property.add`.
2. В `ApprovalB24Client.create_entity_storages()` добавлена автоинициализация схем:
   - `appr_requests`: 10 полей (`INITIATOR_ID`, `APPROVER_IDS`, `STATUS`, и т.д.)
   - `approval_votes`: 5 полей (`REQUEST_ID`, `USER_ID`, `DECISION`, и т.д.)
3. Проверка: `entity.item.property.get` должен возвращать эти коды.
