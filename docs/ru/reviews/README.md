# Отчёты Sprint 1 — Код-ревью

**Спринт**: 1
**Период**: апрель 2026
**Цель**: полный аудит кодовой базы перед итеративной разработкой (Sprint 2).

## Документы спринта

| № | Документ | Описание |
|---|----------|----------|
| 1.1 | [architecture-audit.md](architecture-audit.md) | Сверка `ARCHITECTURE.md` с кодом, расхождения |
| 1.2 | [python-backend-review.md](python-backend-review.md) | Ревью Django backend |
| 1.3 | [frontend-review.md](frontend-review.md) | Ревью Vue 3 / Nuxt 3 frontend |
| 1.4 | [bitrix24-api-compliance.md](bitrix24-api-compliance.md) | Соответствие REST-вызовов спецификации Bitrix24 |
| 1.5 | [user-stories-matrix.md](user-stories-matrix.md) | Покрытие US кодом |
| 1.6 | [bugs-and-optimizations.md](bugs-and-optimizations.md) | Сводный каталог (42 записи) |
| 1.7 | [security-audit.md](security-audit.md) | OWASP + 152-ФЗ |
| 1.8 | (этот файл) | Executive summary |

## Executive Summary

### Что работает хорошо

- ✅ **Архитектура**: чистое разделение `views → services → b24_client → rules`. Доменная логика в `rules.py` изолирована и легко тестируется.
- ✅ **Bitrix24 интеграция**: используются актуальные методы (`imbot.*`, `entity.*`, `placement.*`, `disk.*`); webhook-парсер устойчив к двум форматам payload (event vs legacy).
- ✅ **Frontend**: Composition API + Pinia + i18n; нет Options API, нет хранилищ внутри страниц.
- ✅ **Логирование**: на бэкенде везде `trace_id` — облегчает диагностику.

### Что было критично и закрыто в Sprint 2.1

- ✅ Дублирование `create_entity_storages` на каждом запросе → кэш через `app.option`.
- ✅ Race condition в голосовании → пост-проверка дубликатов.
- ✅ N+1 в `user.get` → батч-вызов через `FILTER[ID]`.
- ✅ Тип-аннотации, логирование тихих exception в `b24_client.py`.

### Что критично и НЕ закрыто (Sprint 2.2 / 4)

| Приоритет | Проблема | Куда |
|-----------|----------|------|
| **P0** | `DEBUG=True` в проде | блокер для Sprint 4 |
| **P1** | OAuth токены не шифруются в БД | Sprint 2.2 |
| **P1** | `approval_detail` без проверки прав | Sprint 2.2 |
| **P1** | `ONAPPUNINSTALL` не зарегистрирован → нет очистки данных | Sprint 2.2 |
| **P1** | Webhook `vote_handle` без проверки подписи | Sprint 2.2 |
| **P1** | `csrf_exempt` на бизнес-endpoints | Sprint 2.2 |
| **P1** | UI игнорирует `bot_issue` | Sprint 2.1+ |
| **P2** | N+1 в `list_requests` | Sprint 2.2 |

### Метрики

| Метрика | Значение |
|---------|----------|
| Файлов проанализировано (backend Python) | 9 ключевых |
| Строк кода (backend Python) | ~1950 |
| Файлов проанализировано (frontend) | 12 ключевых |
| Строк кода (frontend) | ~1320 |
| **Багов и улучшений найдено** | **42** |
| Закрыто в Sprint 2.1 | 3 (P0×2, P1×1) |
| Покрытие User Stories | ~74% (27/38 готов, 6 частично, 5 отсутствует) |
| Тестовое покрытие | **0%** (Sprint 2.2) |

### Распределение находок по компонентам

```
Backend (Python):    16 находок (38%)
Frontend (Vue/Nuxt):  15 находок (36%)
Bitrix24 API:          7 находок (17%)
Архитектура / docs:    4 находки (10%)
```

### Распределение по приоритетам

```
P0:  1 (открыт) + 2 (✅ закрыты)   = 3
P1: 12 (открыты) + 1 (✅ закрыт)   = 13
P2: 17 (открыты)                   = 17
P3: 12 (открыты)                   = 12
                                  ----
                                    42
```

## Рекомендации для Sprint 2

### Iteration 2.2 (приоритет 1)

Сфокусироваться на **безопасности и масштабируемости**:

1. Шифрование OAuth токенов (SEC-P1-1)
2. Проверка прав в `approval_detail` (SEC-P1-2)
3. CSRF на business endpoints (SEC-P1-5)
4. Подпись webhook `vote_handle` (SEC-P2-1)
5. N+1 в `list_requests` через `entity.items.get` (PY-P2-1)
6. `ONAPPUNINSTALL` handler — очистка ПДн (FE-P1-1)
7. UI для `bot_issue` (FE-P1-3)
8. Серверный endpoint `/api/users/list` (FE-P1-2)
9. Pytest setup + 5–10 unit-тестов (rules.py, b24_client.py)
10. Vitest setup + 3–5 тестов (CreateForm, RequestCard)

### Iteration 2.3 (приоритет 2)

UX-полировка и документация:

- UI: skeleton loaders, retry-кнопки, очистка `console.log`
- i18n: убрать хардкод `User ${id}`, проверить полноту RU/EN
- Документация: обновить `ARCHITECTURE.md`, `DATABASE.md` (поля entity, race-protection, `app.option`)
- `EXPIRED`: либо удалить из доки, либо реализовать (cron/scheduler)
- File MIME whitelist (SEC-P2-2)
- GitHub Actions: lint + test на PR

### Sprint 4 (блокеры деплоя)

- `DEBUG=False` через env (SEC-P0-1) — **блокер**
- `CORS_ALLOWED_ORIGINS` whitelist (SEC-P1-3)
- `ALLOWED_HOSTS` валидация (SEC-P1-4)
- Rate limiting (SEC-P2-4)
- HSTS, SECURE cookies (SEC-P3-2/3)

## Готовность к Sprint 2

✅ Каталог багов готов
✅ Приоритизация выполнена
✅ Top-10 для Sprint 2.2 определён
✅ User stories matrix даёт целевую полноту >85% к концу Sprint 2

**Sprint 1 закрыт. Можно стартовать Sprint 2 итерация 2.2.**

---

**Связанные документы**:
- [Sprint 2.1 results](../qa/iteration-2.1-results.md)
- [Plan: 4 sprints](../../../.claude/plans/) (служебный)
