# Соответствие API Bitrix24

**Дата**: апрель 2026
**Спринт**: 1, задача 1.4
**Источник истины**: MCP-инструменты `bitrix-method-details`, `bitrix-event-details`, `bitrix-app-development-doc-details` + официальная документация `dev.1c-bitrix.ru/rest_help/`.

## Используемые методы

| Метод | Где вызывается | Scope | Замечания |
|-------|----------------|-------|-----------|
| `imbot.register` | `b24_client.register_bot` | `imbot` | Регистрируется при первой инициализации сервиса. |
| `imbot.message.add` | `b24_client.send_bot_message` | `imbot` | Используется при создании запроса. |
| `imbot.message.update` | `b24_client.update_bot_message` | `imbot` | Используется при каждом голосе и cancel. |
| `imbot.command.answer` | `b24_client.answer_command` | `imbot` | Ответ на нажатие кнопки в `vote_handle`. |
| `placement.bind` | `install.client.vue:128, 144` | `placement` | `IM_TEXTAREA` с шириной 400×300. |
| `placement.unbind` | `install.client.vue:121` + `b24_client.bind_placement` (silent) | `placement` | Используется для re-bind. |
| `placement.get` | `install.client.vue:42, 268` | `placement` | Для проверки уже привязанных. |
| `entity.add` | `b24_client._ensure_entity` | `entity` | Идемпотентно (после Sprint 2 — за флагом `app.option`). |
| `entity.item.add` | `b24_client.add_request`, `add_vote` | `entity` | Создание записей. |
| `entity.item.update` | `b24_client.update_request_status` | `entity` | Обновление статуса. |
| `entity.item.get` | `b24_client.get_request`, `get_votes`, `get_request_by_message_id` | `entity` | N+1 в `list_requests` (см. PY-P2-1). |
| `entity.items.get` | (ещё не используется) | `entity` | Должен быть применён в `list_requests` (Sprint 2.2). |
| `disk.folder.addsubfolder` | `disk/service.py` | `disk` | Создаёт `appr_files/<request_id>`. |
| `disk.folder.uploadfile` | `disk/service.py` | `disk` | Загрузка вложений. |
| `user.get` (single) | `b24_client.get_user_name` | `user` | Fallback для одиночного пользователя. |
| `user.get` (batch via `FILTER[ID]`) | `b24_client.get_user_names` | `user` | Sprint 2.1 — батч-вызов. |
| `app.info` | `install.client.vue:265` | (auto) | Информация о приложении. |
| `profile` | `install.client.vue:266` | (auto) | Текущий пользователь. |
| `app.option.get` / `app.option.set` | `b24_client.get_app_option/set_app_option` | (auto) | Кэш-флаг `approval_entities_v1`. |
| `userfieldtype.add/update/list` | `install.client.vue:163, 184, 267` | `userfieldtype` | Реликт шаблона (см. FE-P3-1). |

## События

| Событие | Подписка | Обработчик | Статус |
|---------|----------|-----------|--------|
| `ONIMBOTMESSAGEADD` | автоматически после `imbot.register` | `b24_client.handle_bot_message` | ✅ работает (но не покрыт логикой бизнес-команд — только default reply). |
| `ONIMBOTMESSAGEKEYBOARDBUTTON` / `ONIMCOMMANDADD` | автоматически после `imbot.register` | `views.vote_handle` | ✅ работает; payload парсится из обоих форматов (`_extract_vote_payload`). |
| `ONAPPINSTALL` | ❌ не зарегистрировано (`install.client.vue:63-100` закомментировано) | — | См. FE-P1-1. |
| `ONAPPUNINSTALL` | ❌ не зарегистрировано | — | Требуется для очистки данных. |

## Соответствие scopes в манифесте (`app.json`)

Манифест ещё не оформлен (Sprint 3.7). По коду требуется:

```
im, imbot, entity, disk, placement, user, userfieldtype, app
```

`userfieldtype` — кандидат на удаление, если функция не нужна для бизнеса.

## Замечания по корректности вызовов

### B24-1 ✅ `imbot.message.add` — правильное использование `KEYBOARD`
Кнопки голосования передаются как `KEYBOARD: [{TEXT, COMMAND, COMMAND_PARAMS}]`. См. `bot/keyboard.py` (13 строк) и `bot/messages.py`. **Соответствует** документации `dev.1c-bitrix.ru/rest_help/im/imbot/messages/imbot_message_add.php`.

### B24-2 ✅ `imbot.command.answer` ограниченный список действий
Используется только для коротких подтверждений типа «Ваш голос учтён». **Соответствует** правилу: ответ должен быть быстрым и единичным.

### B24-3 ⚠️ `entity.item.get` — фильтрация по полю
В `b24_client.get_votes` фильтр идёт через `FILTER`. Документация Bitrix24 рекомендует `SORT[ID]: ASC` для стабильной пагинации; в коде сортировки нет — порядок голосов недетерминирован. См. `services.handle_vote` где идёт `same_user_votes.sort(key=lambda v: int(v.ID))` — это компенсация. **Рекомендация**: добавить `SORT` в сам REST-вызов.

### B24-4 ⚠️ Не используется батч `entity.items.get`
В `services.list_requests` есть N+1. Bitrix24 поддерживает `entity.items.get` с фильтром и `SELECT` — должен использоваться. См. PY-P2-1.

### B24-5 ⚠️ `placement.bind` `OPTIONS.width/height`
`install.client.vue:108-116` — `width: 400, height: 300`. До Sprint 0/2 было `100`, что не давало ничего отрисовать. **Исправлено**, соответствует рекомендациям Bitrix24 (минимум 400×300 для IM_TEXTAREA).

### B24-6 ⚠️ Webhook payload — два формата
`views._extract_vote_payload` обрабатывает и `event=ONIMCOMMANDADD` (новый формат), и legacy. Это **корректно**, но желательно подтвердить через MCP (`bitrix-event-details ONIMCOMMANDADD`), что legacy формат всё ещё поддерживается порталами.

### B24-7 ⚠️ `disk.folder.uploadfile` — лимит размера
В коде нет проверки размера файла перед загрузкой. Документация Bitrix24 указывает лимит 100 МБ для `disk.folder.uploadfile`. Превышение приводит к 500.
**Рекомендация**: валидация размера в `serializers.validate_create_form` и в `FileUploadArea.vue`.

## Лимиты Bitrix24 REST (известные)

| Лимит | Текущая работа с ним |
|-------|----------------------|
| 2 запроса в секунду на пользователя | Нет rate-limit, риск при массовых голосованиях. |
| 50 операций в `batch` | `frontend/app/utils/chunkArray.ts` есть — но в коде вызовов batch минимально (`install.client.vue` использует фронтовый batch ≤4). На бэкенде batch не используется вообще. |
| 200 в очереди событий | При активном использовании может теряться часть. |

**Рекомендация**: на бэкенде использовать [batch endpoint](https://dev.1c-bitrix.ru/rest_help/general/lists.php) для `entity.item.update + imbot.message.update` в одном запросе после голоса.

## Действия

| ID | Действие | Спринт |
|----|----------|--------|
| B24-A1 | Зарегистрировать `ONAPPINSTALL`/`ONAPPUNINSTALL` | 2.2 |
| B24-A2 | Использовать `entity.items.get` в `list_requests` | 2.2 |
| B24-A3 | Использовать batch для `vote → update + message.update` | 2.2 |
| B24-A4 | Валидация размера файла | 2.3 |
| B24-A5 | Подтвердить через MCP формат `ONIMCOMMANDADD` | 2.2 |
| B24-A6 | Финализировать список scopes в `app.json` | 3.7 |
