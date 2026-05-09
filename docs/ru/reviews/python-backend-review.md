# Код-ревью Python бэкенда

**Дата**: апрель 2026
**Спринт**: 1, задача 1.2
**Объём**: `backends/python/api/approvals/{views,services,b24_client,rules,serializers}.py`, `bot/messages.py`, `core/b24_entity.py`, `settings.py`

## Сводка по приоритетам

| Severity | Открыто | Закрыто в Sprint 2 | Перенесено |
|----------|---------|--------------------|------------|
| P0 | 0 | 2 | 0 |
| P1 | 4 | 3 | 1 |
| P2 | 6 | 1 | 5 |
| P3 | 4 | 0 | 4 |

## P0 — критические (закрыты в Sprint 2)

### PY-P0-1 ✅ Дублирование `create_entity_storages()` на каждый запрос
- **Файл**: `services.py` (исторически, в `__init__` и `create()`)
- **Симптом**: 5+ лишних REST-вызовов к Bitrix24 на каждый POST `/approval/create`.
- **Фикс (Sprint 2.1)**: кэш-флаг `approval_entities_v1` через `app.option.set/get`.

### PY-P0-2 ✅ Race-условие в голосовании
- **Файл**: `services.py:handle_vote`
- **Симптом**: одновременные клики по «Согласовать»/«Отклонить» создают несколько записей `approval_votes` для одного пользователя; `compute_new_status` использует «last vote wins», но история искажена.
- **Фикс (Sprint 2.1)**: пост-проверка `get_votes` и явный отказ при обнаружении более одного голоса того же пользователя.

## P1 — серьёзные

### PY-P1-1 ⚠️ DEBUG=True в продакшене
- **Файл**: `settings.py:9`
- **Цитата**: `DEBUG = True`
- **Риск**: утечка трейсбэков и переменных окружения через 500-страницы.
- **Действие**: вынести `DEBUG = config.debug` (default False).
- **Sprint 4**: обязательно перед деплоем.

### PY-P1-2 ⚠️ `ALLOWED_HOSTS = ["*"]` при пустом `VIRTUAL_HOST`
- **Файл**: `settings.py:10, 22-24`
- **Риск**: HTTP host header injection.
- **Действие**: на проде запретить `["*"]`, требовать `VIRTUAL_HOST`.

### PY-P1-3 ⚠️ `CORS_ALLOW_ALL_ORIGINS = True`
- **Файл**: `settings.py:90`
- **Риск**: любой домен может дёргать API изнутри браузера. Для виджета Bitrix24 это допустимо (происхождение всё равно проверяется через подпись), но лучше явно ограничить.
- **Действие**: `CORS_ALLOWED_ORIGINS = [config.app_base_url, "https://*.bitrix24.ru", ...]`.

### PY-P1-4 ✅ Циклы N+1 в `user.get`
- **Файл**: `b24_client.py:get_user_names`
- **Фикс (Sprint 2.1)**: батч через `FILTER[ID]`.

## P2 — оптимизации

### PY-P2-1 N+1 в `list_requests` / `get_request_by_message_id`
- **Файл**: `services.py:list_requests`, `services.py:get_request_by_message_id`
- **Симптом**: для каждого запроса вызываются `entity.item.get` + `get_votes` по одному. На 50 запросах — ~100+ REST-вызовов.
- **Действие** (Sprint 2.2): один `entity.items.get` с фильтром `INITIATOR_ID` или `APPROVER_IDS`, агрегация голосов локально.

### PY-P2-2 Отсутствие индексации в Bitrix24 entity
- **Симптом**: `entity` от Bitrix24 не имеет управляемых индексов; фильтрация по `STATUS`/`INITIATOR_ID` идёт линейно.
- **Действие**: задокументировать ограничение (Sprint 1.6) и заложить миграцию в свою PostgreSQL-таблицу для read-моделей при росте до >5k запросов на портал.

### PY-P2-3 Бот-сообщение строится re-render полностью при каждом голосе
- **Файл**: `bot/messages.py:build_approval_message`, вызывается из `services.handle_vote`.
- **Симптом**: при каждом голосе бот шлёт `imbot.message.update` с полным текстом — это нормально, но `build_approval_message` собирает строки в Python без использования шаблонизатора. На 20+ согласующих текст переваливает за лимит Bitrix24 (≈ 3000 симв.).
- **Действие**: усечение списков «Одобрили»/«Отклонили»/«Ожидает» при >10 элементов («…ещё N»).

### PY-P2-4 Отсутствует логирование длительности REST-вызовов
- **Файл**: `b24_client.py`
- **Действие**: декоратор `@log_duration` для метрик p50/p95.

### PY-P2-5 `_inflate_bracket_payload` молча игнорирует пустые ключи
- **Файл**: `views.py:51-77`
- **Риск**: при кривом payload теряются данные молча. Минимум — лог-предупреждение.

### PY-P2-6 Отсутствие транзакций
- В Django views нет явного `transaction.atomic`. Для операций, которые пишут одновременно в `appr_requests` и `imbot.message.add` (внешний вызов), это допустимо (внешнюю транзакцию не накатить), но нужен **компенсирующий путь**: если `imbot.message.add` упал — что делать с уже созданным запросом?
- **Текущее поведение**: `services.create` логирует `bot_issue` и возвращает запрос как успех. Это правильно (запрос создан), но фронтенд должен показывать предупреждение.
- **Действие**: убедиться, что фронтенд показывает `bot_issue` пользователю (см. frontend-review).

## P3 — стилевые / документация

| ID | Файл | Замечание |
|----|------|-----------|
| PY-P3-1 | `b24_client.py` | Нет docstrings у публичных методов. |
| PY-P3-2 | `views.py:152` | `except Exception: pass` в `_answer_vote_command` — добавить логирование. |
| PY-P3-3 | `settings.py:80` | `AUTH_PASSWORD_VALIDATORS = []` (для Django admin). На проде — заполнить. |
| PY-P3-4 | везде | Нет type hints у декораторов в `main/utils/decorators/`. |

## Хорошее в коде

- ✅ Чёткое разделение `views` (HTTP) → `services` (use-case) → `b24_client` (REST) → `rules` (доменная логика).
- ✅ Идемпотентный `_inflate_bracket_payload` для разных форматов webhook от Bitrix24 (`event=ONIMCOMMANDADD` vs legacy).
- ✅ Логирование с `trace_id` (`views.approval_create:167`, `views.vote_handle:265`) — облегчает дебаг.
- ✅ `rules.py` изолирована от REST — легко юнит-тестируется.
- ✅ Конфиг через `config` (предположительно `pydantic-settings`) — нет хардкода.

## Действия

| ID | Действие | Спринт |
|----|----------|--------|
| PY-A1 | `DEBUG=False` через env | 4 |
| PY-A2 | `CORS_ALLOWED_ORIGINS` whitelist | 4 |
| PY-A3 | Батчинг `list_requests` | 2.2 |
| PY-A4 | Усечение длинных списков в bot message | 2.2 |
| PY-A5 | Pytest + 5–10 unit-тестов на `rules.py` и `b24_client.py` | 2.2 |
| PY-A6 | Логирование длительности REST | 2.3 / 4 |
| PY-A7 | Docstrings и type hints в `decorators/` | 2.3 |
