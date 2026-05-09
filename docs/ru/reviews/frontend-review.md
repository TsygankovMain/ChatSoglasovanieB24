# Код-ревью фронтенда

**Дата**: апрель 2026
**Спринт**: 1, задача 1.3
**Объём**: `frontend/app/pages/install.client.vue`, `pages/index.client.vue`, `components/approval/*`, `composables/useApproval*`, `stores/approvals.ts`, `stores/api.ts`

## Сводка

| Severity | Кол-во |
|----------|--------|
| P0 | 0 |
| P1 | 3 |
| P2 | 7 |
| P3 | 5 |

## P1 — серьёзные

### FE-P1-1 ⚠️ В установке не регистрируются `ONAPPINSTALL` / `ONAPPUNINSTALL`
- **Файл**: `pages/install.client.vue:63-100` — закомментировано.
- **Риск**: при удалении приложения портал не уведомляет бэкенд → нет очистки токенов и сущностей. На каждом портале остаются "висящие" `appr_requests`, привязанные к удалённой инсталляции.
- **Действие**: либо реализовать обработку на бэкенде и раскомментировать, либо оставить осознанно с пометкой в `ARCHITECTURE.md`. Рекомендуется реализовать (Sprint 2.2).

### FE-P1-2 ⚠️ В `CreateForm` загрузка пользователей через `app.option` не имеет защиты от гонок
- **Файл**: `components/approval/CreateForm.vue:74-147`
- **Симптом**: если два пользователя одновременно открывают форму при истёкшем кэше, оба вызывают `user.get` через `callListMethod` (потенциально страничный список) и оба пишут в `app.option.set`. Победит последний.
- **Риск**: при 1k пользователей `callListMethod('user.get')` выполняется десятки секунд. Дублирующиеся запросы блокируют UI.
- **Действие**: на бэкенде иметь endpoint `/api/users/list?cache=1` с серверным кэшем, фронтенд бьёт в один источник.

### FE-P1-3 ⚠️ Отсутствие обработки `bot_issue` в UI
- **Файл**: `components/approval/CreateForm.vue:189-193`
- **Симптом**: `console.warn(bot_issue)` при пустом `bot_message_id` — пользователь не видит проблему. Если бот не зарегистрирован или нет прав `imbot`, запрос «успешно создан», но в чате ничего не появилось.
- **Действие**: показывать toast/alert «Запрос создан, но не опубликован в чате. Причина: ...».

## P2 — оптимизации

### FE-P2-1 Отсутствует cleanup в `composables/useApproval.ts`
- **Файл**: 38 строк, фасад над `stores/approvals`. Сами по себе нет проблем, но нет `onBeforeUnmount` для отмены in-flight запросов → memory leaks при быстром переходе между страницами.

### FE-P2-2 `console.log` / `console.debug` в проде
- **Файл**: `CreateForm.vue:95, 101, 122, 167-172, 183-194, 203`
- **Действие**: завернуть в `if (import.meta.dev)` или использовать `$logger` из `useAppInit`.

### FE-P2-3 Жёстко закодированный `5 * 60 * 1000` для TTL кэша
- **Файл**: `CreateForm.vue:91-92`
- **Действие**: вынести в `app.config.ts` или env.

### FE-P2-4 `appUrl` через `withoutTrailingSlash` — но handler `${appUrl}/`
- **Файл**: `pages/install.client.vue:106` — `handler: \`${appUrl}/\``
- **Замечание**: после `withoutTrailingSlash` принудительно добавляется `/`. На разных порталах это может дать разные `placement.handler` (если у одного `appUrl` уже без, у другого с `/` вообще). На текущем коде работает, но неочевидно.
- **Действие**: явный комментарий + тест.

### FE-P2-5 Нет fallback при `usersLoadError`
- **Файл**: `CreateForm.vue:248-251`
- **Симптом**: если `user.get` падает и кэша нет — пользователь видит «нет доступных пользователей», но не может ввести ID вручную или повторить попытку.
- **Действие**: кнопка «Попробовать снова», текст ошибки с retry.

### FE-P2-6 Pinia `stores/approvals.ts` — нет инвалидации после `cancel`
- **Файл**: `stores/approvals.ts` (109 строк)
- **Действие**: после успешного cancel — обновить элемент в `state.items` или дёрнуть `list()`.

### FE-P2-7 `index.client.vue` загружает запросы без пагинации
- **Файл**: `pages/index.client.vue` (209 строк)
- **Действие**: добавить пагинацию или infinite scroll, сейчас при росте >100 запросов сильно тормозит первый рендер.

## P3 — стилевые

| ID | Файл | Замечание |
|----|------|-----------|
| FE-P3-1 | `install.client.vue:159` | `userfieldtype` создаётся всегда, даже если функция не используется. Реликт шаблона. |
| FE-P3-2 | `CreateForm.vue:24-33` | Тип `B24User` дублирует поля в snake/camel. Завести нормализатор. |
| FE-P3-3 | `CreateForm.vue:115` | Fallback `User ${id}` — без локализации. Должно идти через i18n. |
| FE-P3-4 | глобально | Нет skeleton loaders, везде только текст «Загрузка…». |
| FE-P3-5 | `app.vue` | Не проверял; отдельно — но ожидаю отсутствие глобального error boundary. |

## Соответствие документации

`docs/ru/FRONTEND.md` упоминает компоненты `Form`, `Card`, `Buttons`. По факту в `components/approval/`:
- `CreateForm.vue` ✅
- `RequestCard.vue` ✅
- `EventLog.vue` ✅ (в доке отсутствует)
- `StatusBadge.vue` ✅ (в доке отсутствует)
- `VoteStatus.vue` ✅ (в доке отсутствует)
- Кнопки голосования — нет отдельного компонента (логика в `RequestCard.vue`)

**Рекомендация**: обновить `FRONTEND.md` под фактический набор компонентов.

## Хорошее

- ✅ Composition API везде, нет Options API.
- ✅ Type-safe `defineProps` / `defineEmits`.
- ✅ Pinia вместо локального state в страницах.
- ✅ i18n работает (`t()` всюду в текстах).
- ✅ `useAppInit` — единая точка инициализации `$logger`, `initLang`.

## Действия

| ID | Действие | Спринт |
|----|----------|--------|
| FE-A1 | Реализовать `ONAPPINSTALL/ONAPPUNINSTALL` | 2.2 |
| FE-A2 | Endpoint `/api/users/list` на бэкенде + клиентский кэш | 2.2 |
| FE-A3 | UI для `bot_issue` | 2.1+ |
| FE-A4 | Vitest + тесты для `CreateForm`, `RequestCard` | 2.2 |
| FE-A5 | Cleanup console.log в проде | 2.3 |
| FE-A6 | Skeleton loaders | 2.3 |
| FE-A7 | Пагинация в `index.client.vue` | 2.3 |
