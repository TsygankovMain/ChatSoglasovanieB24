# Решение проблем

Типичные проблемы и их решения. Документ обновлён по итогам Sprint 2 (апрель 2026) — учтены реальные находки и архитектурные изменения (отказ от БД, переход на JWT-only stateless, добавлен ONAPPUNINSTALL).

> ❗ **Архитектурное напоминание.** Приложение полностью **stateless**: бэкенд не хранит ни OAuth-токены, ни пользовательские данные. Хранилище — только Bitrix24 entity на портале клиента + JWT в браузере фронта. Если в инструкциях ниже встречается команда вида `docker-compose exec database ...` — это устаревший рецепт, актуальный только для старых веток.

---

## 1. Проблемы установки

### Установка не работает

**Признаки**:
- Мастер установки зависает на одном из шагов;
- Ошибка `Failed to bind placement`;
- Бэкенд возвращает не-OK на шаге `serverSide`.

**Решения**:

1. **Проверьте переменные окружения**:
```bash
echo $VIRTUAL_HOST     # Публичный URL приложения (https://...)
echo $CLIENT_ID        # ID приложения из Bitrix24 Marketplace
echo $CLIENT_SECRET    # Секрет приложения
echo $JWT_SECRET       # ≥ 32 байта (HS256). Без него прод не стартует.
echo $SCOPE            # im,imbot,entity,disk,placement,user
```

2. **Проверьте доступность сервера** (с любой машины):
```bash
curl -v https://ваш-домен.com/api/health
# → 200 OK + {"status":"ok"}
```

3. **Просмотрите логи бэкенда**:
```bash
docker-compose logs -f api-python
# или: journalctl -u приложение -f
```

4. **Переустановите приложение**:
   - Bitrix24 → Приложения → ваше приложение → «Удалить».
   - Очистите кеш браузера.
   - Установите заново. Backend, поскольку stateless, готов к переустановке без миграций.

### "Размещение не найдено"

**Ошибка**: `AjaxError 200: Placement not found`.

**Причина**: либо `placement.bind` не отработал, либо handler-URL изменился, а старая привязка осталась.

**Решение**:
- Установите заново: при `install` мастер на фронте делает `placement.unbind` → `placement.bind`. Это перезаписывает старые привязки.
- Если установка не помогла — проверьте, что `VIRTUAL_HOST` точно соответствует домену, на который смотрит Bitrix24 в карточке приложения.

### `dialogId` пуст в форме

**Решение**:

1. Запускайте из правильного места: Чат → значок приложения над текстовым полем (`IM_TEXTAREA`). НЕ запускайте из общего списка приложений — там нет `DIALOG_ID` в контексте placement.
2. Проверьте контекст:
```ts
const $b24 = await $initializeB24Frame()
console.log($b24.placement.options) // должны быть DIALOG_ID/CHAT_ID/USER_ID
```
3. Очистите кеш браузера и повторите.

---

## 2. Проблемы с аутентификацией

### "Invalid Token" / "No Auth"

**Архитектура (с Sprint 2.2)**: бэкенд принимает **JWT** в `Authorization: Bearer <token>`. JWT короткоживущий (60 минут), внутри — OAuth-payload (`access_token`, `refresh_token`, `domain`, `user_id`, `member_id`). Подпись HMAC-SHA256 ключом `JWT_SECRET`.

**Решения**:

1. **Проверьте, что JWT не истёк** (фронт обновляет токен через `/api/auth/get-token` автоматически, но иногда зависает между табами):
```bash
# Декодировать payload без верификации
python3 -c "import jwt; print(jwt.decode('$JWT', options={'verify_signature': False}))"
# Поле "exp" — unix-timestamp окончания
```

2. **Проверьте `JWT_SECRET`**: он должен совпадать в проде и в сервисах, которые выдают/проверяют токены. Длина ≥ 32 байта; иначе PyJWT выдаст предупреждение, в проде — отклонит.

3. **Откройте приложение заново внутри Bitrix24** — фронт получит свежий OAuth-bundle от iframe-SDK и пересоздаст JWT.

### Webhook от Bitrix24 не аутентифицируется

**Симптом**: `BitrixValidationError: Webhook auth payload missing access_token`.

**Причина**: bracket-keys не «развернулись» в dict (например `auth[member_id]` остался строкой) или Bitrix24 прислал событие без `auth`-блока.

**Решение**:
- Проверьте логи на строку `Skipping malformed bracket key in webhook payload` — это отдельный диагностический сигнал из `_inflate_bracket_payload` (добавлен в Sprint 2.3).
- Убедитесь, что `Content-Type: application/x-www-form-urlencoded` (Bitrix24 отправляет именно так — Django Express сам разворачивает в `request.POST`).

### "Forbidden" на `/api/approval/<id>`

**Симптом**: 403 на чтение деталей запроса согласования.

**Причина** (с Sprint 2.2 / SEC-P1-2): доступ ограничен инициатором, согласующими и админом портала. Доступ постороннего юзера портала к чужому запросу теперь блокируется.

**Решение**: убедитесь, что текущий пользователь — initiator, либо в `approver_ids`, либо имеет `is_b24_user_admin: true`.

---

## 3. Проблемы API и бэкенда

### Сообщение бота не публикуется

**Признаки**: запрос создан, фронт получил `request_id`, но в чате сообщения нет; в ответе пришло поле `bot_issue` (или пустое `bot_message_id`).

**Сначала**: посмотрите на `bot_issue`. С Sprint 2.2 фронт показывает его пользователю в виде баннера в `CreateForm` — это первый источник симптомов. Стандартные причины:

1. **Бот не зарегистрирован**:
```python
bot_id = client.get_app_option("bot_id")
if not bot_id:
    # Удалите и установите приложение заново — бот регистрируется на шаге serverSide.
    ...
```

2. **Бот не приглашён в чат** (актуально для приватных чатов), либо `dialog_id` указывает на личный диалог двух пользователей, куда бот не имеет доступа.

3. **Превышен лимит участников в сообщении** (>20 согласующих + длинное описание). Сейчас бэкенд усекает список с пометкой «...ещё N» — если этого не происходит, проверьте версию.

### Голоса не сохраняются

**Архитектура**: голоса хранятся в Bitrix24 entity `approval_votes` через `entity.item.add`. БД у приложения нет.

**Решение**:

1. Проверьте, что entity-storage существует:
```python
properties = entity_item_property_get(client, "approval_votes")
required = ["REQUEST_ID", "USER_ID", "DECISION"]
missing = [p for p in required if p not in {x['PROPERTY'] for x in properties}]
print(missing)  # пустой список = OK
```

2. Хранилища создаются один раз при первой установке (помечается флагом `app.option["storages_ready"]="1"`). Если флаг сбился — переустановите приложение.

3. Если голос «теряется» — это race-condition между ботом и пользователем. С Sprint 2.1 в `handle_vote` есть пост-проверка через `get_votes()`; если она проходит, голос точно записан. Симптом «у пользователя UI говорит «отправлено», а в боте кнопки остались» — обычно браузерный кеш, а не пропавший голос.

### 500 Internal Server Error

**Решение**:

1. Логи: `docker-compose logs --tail=50 api-python`.
2. Если ошибка `BitrixAPIError`: с Sprint 2.2 такая ошибка маппится в **502 Bad Gateway**, а не 500 — это сигнал, что Bitrix24 сам ответил ошибкой (rate-limit, токен отозван, портал недоступен). Текст в `error.message` — оригинал от Bitrix24.
3. `DEBUG` в проде должен быть `False`. Если у вас 500 со стектрейсом в HTML — `DEBUG=True` где-то проскочил, проверьте окружение (с Sprint 2.2: `DEBUG = config.debug`, default `False`).

---

## 4. Проблемы фронтенда

### Мастер установки зависает

**Решение**:

1. Откройте DevTools → Console. Ищите ошибки от `b24jssdk` и `apiStore.postInstall`.
2. Network → найдите запрос на `/api/install`. Если он 4xx/5xx — смотрите тело ответа: backend возвращает `steps: { ... }`-структуру с пометками `OK` / `error`. Фронт сам найдёт первую упавшую ступень и пробросит её сообщением.
3. Если на шаге `events` (регистрация ONAPPUNINSTALL) возникает «conflict» — повторно запустите мастер: первый `event.unbind` чистит залипшую старую регистрацию (флоу появился в Sprint 2.2).

### `console.log` в production-сборке

С Sprint 2.3 все диагностические `console.log/groupCollapsed` в `CreateForm.vue` и `stores/api.ts` обёрнуты `if (import.meta.dev) { ... }`. Если в проде из них что-то протекает — вы запустили dev-сборку (`nuxt dev`) вместо `nuxt build && nuxt preview`.

### `bot_issue` не виден пользователю

С Sprint 2.2 баннер `approval.form.warning.bot_issue` (RU/EN) рендерится в `CreateForm.vue` сразу после успешного создания запроса. Если баннера нет — обновите фронт-сборку (старые ассеты в кеше браузера/CDN); либо проверьте, что в `i18n/locales/{ru,en}.json` присутствует ключ `approval.form.warning.bot_issue`.

---

## 5. Проблемы Bitrix24 API

### "Incorrect keyboard params"

**Решение**:

1. У каждой кнопки есть `TEXT` + одно из `COMMAND` / `ACTION` / `LINK`.
2. `COMMAND_PARAMS` — это **JSON-строка**, не dict:
```python
button["COMMAND_PARAMS"] = json.dumps({...})   # ✅
button["COMMAND_PARAMS"] = {...}               # ❌
```
3. Внутри `b24_client.py` есть fallback: если Bitrix24 ругается на формат `KEYBOARD: dict` — повторяет с `KEYBOARD: list`. Если оба варианта 4xx — проблема в самих кнопках (вероятно, в JSON-payload спецсимвол не экранирован).

### "Entity item not found" сразу после создания

Bitrix24 entity-API «eventually consistent» по чтению. Если делаете `entity.item.add` → сразу `entity.item.get` — иногда промахиваетесь по реплике.

**Решение**:
- Используйте возвращаемый `id` напрямую вместо повторного `get`.
- В крайнем случае — повтор через 100–200 мс.

---

## 6. Развёртывание / окружение

### Прод не стартует с пустым `VIRTUAL_HOST`

С Sprint 2.2 это **намеренный fail-fast**: без `VIRTUAL_HOST` `ALLOWED_HOSTS=['*']` был бы единственным вариантом. Установите ENV-переменную или вернитесь к dev-сборке.

### CORS блокирует фронт

С Sprint 2.2 CORS ограничен regex `^https://[a-z0-9\-]+\.bitrix24\.[a-z]+$`. Если у вас кастомный домен Bitrix24 (CNAME) — допишите его в `CORS_ALLOWED_ORIGIN_REGEXES` в `settings.py`.

---

## 7. Диагностика

### Трассировка полного потока

1. **Фронт → бэкенд**: каждый запрос несёт заголовок `X-Approval-Trace-Id` (см. `CreateForm.vue`). Ищите его в логах backend'а — найдёте полный жизненный цикл запроса:
   ```bash
   docker-compose logs api-python | grep "approval-ui-1714..." 
   ```
2. **Бэкенд → Bitrix24**: оборачивайте подозрительные REST-вызовы декоратором логирования (планируется в 2.3, ID PY-P2-4).
3. **Bitrix24 → бэкенд (webhook)**: смотрите `vote_handle` логи. С Sprint 2.3 неправильные bracket-ключи логируются warning'ом, не падают молча.

### Включить debug

**Фронтенд**: запустите `npm run dev` (там `import.meta.dev === true`).

**Бэкенд**:
```bash
DEBUG=true LOG_LEVEL=DEBUG docker-compose up api-python
```

---

## 8. Что было исправлено в Sprint 2

Если вы видите старые рецепты в задачах/Stack Overflow с этим приложением — вот ключевые исправления, которые могут переписать симптомы:

- **2.1**: убран дубль `create_entity_storages` (флаг `storages_ready`); закрыт race-condition в `handle_vote`; батчинг `user.get` через `FILTER[ID]`.
- **2.2**: убрана БД и `Bitrix24Account`/`ApplicationInstallation`; JWT-only stateless; добавлен ONAPPUNINSTALL endpoint; `approval_detail` отдаёт 403 непричастным; `BitrixAPIError → 502`; CORS-whitelist; кэш `app.option` и `bot_id` per-request; UI для `bot_issue`.
- **2.3**: валидация загружаемых файлов (whitelist расширений, лимит 25 МиБ × 10 файлов); `console.log` под dev-guard; синхронизированы RU/EN i18n; добавлен GitHub Actions CI; почищен лишний `userfieldtype`-шаг установки.

---

**Последнее обновление**: апрель 2026, Sprint 2.3.
