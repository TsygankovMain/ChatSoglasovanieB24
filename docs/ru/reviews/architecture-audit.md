# Аудит архитектуры

**Дата**: апрель 2026
**Спринт**: 1, задача 1.1
**Сверка**: `docs/ru/ARCHITECTURE.md` ↔ реальный код

## Резюме

Архитектурная документация в целом соответствует коду, но в нескольких местах ранее присутствовала формулировка «FastAPI» вместо реального стека. В рамках Sprint 0 это исправлено: `docs/ru/ARCHITECTURE.md:39` и `docs/ru/INDEX.md` содержат корректное упоминание Django. Текущий Python-бэкенд — Django (Django views + декораторы, без DRF), см. `backends/python/api/approvals/views.py:6-9` (импорты `django.http`, `django.views.decorators.csrf`).

## Состояние стека (по факту)

| Слой | Что заявлено в `ARCHITECTURE.md` | Что реально |
|------|----------------------------------|-------------|
| Backend | Python Django | Django 4.x, обычные `def view(request)` с декораторами. **Соответствует.** |
| Frontend | Vue 3 + Nuxt | Nuxt 3, Vue 3, Pinia (`stores/`), `@bitrix24/b24ui-nuxt` UI kit. **Соответствует.** |
| БД | PostgreSQL | `backends/python/api/settings.py:69-78` — `postgresql_psycopg2`. **Соответствует.** |
| Хранилище запросов | Bitrix24 entity storage | `b24_client.py` — `entity.add`, `entity.item.add/update/get`. **Соответствует.** |
| Бот | imbot | `b24_client.py:imbot.register/message.add/update`. **Соответствует.** |
| Размещение | IM_TEXTAREA | `frontend/app/pages/install.client.vue:104-116` — `placement.bind` с `IM_TEXTAREA` и `width:400, height:300`. **Соответствует** (после фикса размеров в Sprint 0/2). |

## Расхождения и устаревшие места

### A1. ⚠️ Документация в `ARCHITECTURE.md` упоминает диаграммы Bitrix24 (placeholder)

В `ARCHITECTURE.md:7-44` есть схема, но она не отражает наличие отдельных слоёв:
- `frontend/app/composables/useApproval.ts` (фасад над API)
- `frontend/app/stores/approvals.ts` (Pinia, кэш списков)
- `backends/python/api/approvals/services.py:ApprovalService` (бизнес-логика)
- `backends/python/api/approvals/rules.py` (доменные правила голосования)

**Рекомендация (P3)**: дополнить схему слоями фронтенд-приложения и слоями `service`/`rules` на бэкенде.

### A2. Раздел «Хранилище сущностей» неточен по полям

`ARCHITECTURE.md:50-74` описывает поля `appr_requests` и `approval_votes`. По факту фактические property name в коде:
- В `appr_requests`: `INITIATOR_ID`, `COMMENT`, `APPROVER_IDS` (JSON), `THRESHOLD_TYPE`, `STATUS`, `DIALOG_ID`, `BOT_MESSAGE_ID`, `BOT_MESSAGE_IDS` (JSON), `BOT_DIALOG_IDS` (JSON), `DISK_FOLDER_ID`, `FILE_IDS` (JSON), `CREATED_AT`, `LAST_ACTION_TEXT` — см. `b24_client.py:_ensure_entity_properties` и `services.py`.
- Документация упоминает только одиночный `BOT_MESSAGE_ID`, но реально код использует множественные `BOT_MESSAGE_IDS` (для рассылки в нескольких чатах) и `LAST_ACTION_TEXT` для аудита.

**Рекомендация (P2)**: обновить таблицу полей в `ARCHITECTURE.md` и `DATABASE.md`.

### A3. Поток данных «Голосование» не отражает race-protection

`ARCHITECTURE.md:124-147` описывает поток без упоминания идемпотентности. После Sprint 2 в `services.py:handle_vote` добавлена пост-проверка дубликатов голосов.

**Рекомендация (P2)**: добавить шаг «Проверка на дубликат голоса (race-protection)».

### A4. Отсутствует раздел про кэш `app.option`

После Sprint 2 кэширование инициализации сущностей через `app.option` (`approval_entities_v1`) — критичное архитектурное решение для производительности. В документации не описано.

**Рекомендация (P1)**: добавить подраздел «Кэш инициализации» в `ARCHITECTURE.md` и `BITRIX24_INTEGRATION.md`.

### A5. Жизненный цикл запроса упоминает `EXPIRED`, но логика таймаута не реализована

`ARCHITECTURE.md:99` указывает переход «(таймаут) → EXPIRED». В `rules.compute_new_status` (`rules.py:31-66`) такого перехода нет: терминальные статусы — `approved`, `rejected`, `cancelled` (см. `rules.is_terminal:69-70`). Таймаут не реализован ни в коде, ни в cron.

**Рекомендация (P2)**: либо удалить из документации, либо реализовать (Sprint 2.3 / Sprint 3 backlog).

## Выводы

- ✅ Архитектура соответствует общей модели «Bitrix24 entity storage + Django + Nuxt».
- ✅ FastAPI-упоминание устранено.
- ⚠️ Документация отстаёт от кода на 1 спринт: новые поля и идемпотентность не отражены.
- ❌ Функция «таймаут запроса» — фантом (документирована, но не реализована).

## Действия для следующих спринтов

| ID | Действие | Куда | Приоритет |
|----|----------|------|-----------|
| ARCH-1 | Обновить таблицу полей entity | `ARCHITECTURE.md`, `DATABASE.md` | P2 |
| ARCH-2 | Добавить раздел про кэш `app.option` | `ARCHITECTURE.md` | P1 |
| ARCH-3 | Удалить или реализовать `EXPIRED` | `ARCHITECTURE.md` + код | P2 |
| ARCH-4 | Обновить поток «Голосование» с race-protection | `ARCHITECTURE.md` | P2 |
