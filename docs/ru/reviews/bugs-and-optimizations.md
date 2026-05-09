# Каталог багов и оптимизаций

**Дата**: апрель 2026
**Спринт**: 1, задача 1.6
**Источник**: агрегация из `python-backend-review.md`, `frontend-review.md`, `bitrix24-api-compliance.md`, `security-audit.md`, `architecture-audit.md`

## Сводка

| Severity | Открыто | Закрыто Sprint 2.1 | Перенесено Sprint 2.2 | Перенесено Sprint 2.3 | Перенесено Sprint 4 |
|----------|---------|--------------------|-----------------------|-----------------------|---------------------|
| P0 | 1 | 2 | 0 | 0 | 1 |
| P1 | 12 | 1 | 7 | 1 | 4 |
| P2 | 17 | 0 | 8 | 5 | 4 |
| P3 | 12 | 0 | 0 | 8 | 4 |
| **Итого** | **42** | **3** | **15** | **14** | **13** |

## Формат записи

```
ID | Severity | Описание | Файл:строка | Решение | Sprint | Estimate (S/M/L)
```

## P0 — критические

| ID | Описание | Файл | Решение | Sprint | Est |
|----|----------|------|---------|--------|-----|
| SEC-P0-1 | `DEBUG=True` в проде | `settings.py:9` | `DEBUG = config.debug` (default False) | 4 | S |
| ~~PY-P0-1~~ | ✅ Дублирование `create_entity_storages` | `services.py` | Кэш-флаг `app.option` | **2.1 ✅** | S |
| ~~PY-P0-2~~ | ✅ Race condition в голосовании | `services.handle_vote` | Пост-проверка `get_votes` | **2.1 ✅** | M |

## P1 — серьёзные

| ID | Описание | Файл | Решение | Sprint | Est |
|----|----------|------|---------|--------|-----|
| FE-P1-1 | `ONAPPINSTALL/UNINSTALL` не зарегистрированы | `install.client.vue:63-100` | Раскомментировать + бэкенд handler | 2.2 | M |
| FE-P1-2 | Race в загрузке пользователей в `CreateForm` | `CreateForm.vue:74-147` | Серверный endpoint `/api/users/list` | 2.2 | M |
| FE-P1-3 | UI игнорирует `bot_issue` | `CreateForm.vue:189-193` | Toast/alert при пустом `bot_message_id` | 2.1 | S |
| PY-P1-1 / SEC-P0-1 | `DEBUG=True` | `settings.py:9` | env-driven | 4 | S |
| PY-P1-2 / SEC-P1-4 | `ALLOWED_HOSTS=["*"]` | `settings.py:10, 24` | Валидация `VIRTUAL_HOST` | 4 | S |
| PY-P1-3 / SEC-P1-3 | `CORS_ALLOW_ALL_ORIGINS=True` | `settings.py:90` | Whitelist | 4 | S |
| ~~PY-P1-4~~ | ✅ N+1 в `user.get` | `b24_client.get_user_names` | Батч `FILTER[ID]` | **2.1 ✅** | M |
| SEC-P1-1 | OAuth токены не шифруются | `main/models.Bitrix24Account` | `cryptography.fernet` | 2.2 / 4 | M |
| SEC-P1-2 | `approval_detail` без проверки прав | `views.approval_detail:223` | `user_id in approver_ids or initiator` | 2.2 | S |
| SEC-P1-5 | `csrf_exempt` на бизнес-endpoints | `views.py:156, 232` | CSRF token + double cookie | 2.2 | M |
| ARCH-2 | Раздел про `app.option` кэш в доке | `ARCHITECTURE.md` | Дописать секцию | 2.3 | S |
| US-7.4 | Возможна утечка токенов в логах | везде | Аудит логов | 2.3 | S |

## P2 — оптимизации

| ID | Описание | Файл | Решение | Sprint | Est |
|----|----------|------|---------|--------|-----|
| PY-P2-1 / B24-A2 | N+1 в `list_requests` | `services.list_requests` | `entity.items.get` + локальная агрегация | 2.2 | M |
| PY-P2-3 | Bot message превышает лимит при >20 согласующих | `bot/messages.py:46-51` | Усечение «...ещё N» | 2.2 | S |
| PY-P2-4 | Нет логирования длительности REST | `b24_client.py` | `@log_duration` | 2.3 | S |
| PY-P2-5 | `_inflate_bracket_payload` молчит | `views.py:51-77` | Лог-предупреждение | 2.3 | XS |
| PY-P2-6 | Нет UI для `bot_issue` | (FE-P1-3) | (см. FE-P1-3) | 2.1 | — |
| PY-P2-2 | Нет индексов для entity (Bitrix24) | архитектура | Документация + read-модель в PG | 2.3 | M |
| FE-P2-1 | Нет cleanup в `useApproval` | `composables/useApproval.ts` | `onBeforeUnmount` | 2.3 | S |
| FE-P2-2 | `console.log` в проде | `CreateForm.vue` etc. | `import.meta.dev` guard | 2.3 | XS |
| FE-P2-3 | Hardcode 5min TTL | `CreateForm.vue:91-92` | `app.config.ts` | 2.3 | XS |
| FE-P2-4 | `appUrl` + `/` нюанс | `install.client.vue:106` | Комментарий + тест | 2.3 | XS |
| FE-P2-5 | Нет fallback при ошибке user.get | `CreateForm.vue:248` | Кнопка retry | 2.3 | S |
| FE-P2-6 | Нет инвалидации после `cancel` | `stores/approvals.ts` | `state.items.find().status='cancelled'` | 2.2 | S |
| FE-P2-7 | Нет пагинации в `index` | `pages/index.client.vue` | Infinite scroll или offset | 2.3 | M |
| B24-3 | Нет SORT в `entity.item.get votes` | `b24_client.get_votes` | `SORT[ID]: ASC` | 2.2 | XS |
| B24-A3 | Нет batch для `vote → update + message.update` | `services.handle_vote` | `batch` REST | 2.2 | M |
| B24-7 / SEC-P2-2 | Нет валидации размера/типа файла | `serializers.py` + `FileUploadArea.vue` | White-list MIME + size limit | 2.3 | S |
| SEC-P2-1 | Webhook без проверки подписи | `views.vote_handle` | Verify `application_token` | 2.2 | M |
| SEC-P2-3 | Возможные утечки в логах | везде | Аудит | 2.3 | S |
| SEC-P2-4 | Нет rate limit | nginx / django-ratelimit | конфиг | 4 | S |
| ARCH-1 | Поля entity в доке устарели | `ARCHITECTURE.md`, `DATABASE.md` | Обновить | 2.3 | S |
| ARCH-3 | `EXPIRED` в доке, но не в коде | `ARCHITECTURE.md` | Удалить или реализовать | 2.3 | S/M |
| ARCH-4 | Поток «Голосование» без race-защиты | `ARCHITECTURE.md` | Обновить | 2.3 | XS |
| FE-P3-1 | `userfieldtype` лишний | `install.client.vue` | Удалить | 2.3 | XS |

## P3 — стилевые

| ID | Описание | Файл | Решение |
|----|----------|------|---------|
| PY-P3-1 | Нет docstrings в `b24_client` | везде | Добавить |
| PY-P3-2 | `except: pass` в `_answer_vote_command` | `views.py:151-152` | `logger.warning` |
| PY-P3-3 | Пустые `AUTH_PASSWORD_VALIDATORS` | `settings.py:80` | Заполнить |
| PY-P3-4 | Нет type hints в `decorators/` | `main/utils/decorators/*.py` | Добавить |
| FE-P3-2 | `B24User` дубль snake/camel | `CreateForm.vue:24-33` | Нормализатор |
| FE-P3-3 | `User ${id}` без i18n | `CreateForm.vue:115` | `t('approval.user_default')` |
| FE-P3-4 | Нет skeleton loaders | везде | UX-полировка |
| FE-P3-5 | Нет error boundary | `app.vue` | `<ClientOnly>` + `<NuxtErrorBoundary>` |
| SEC-P3-1 | Нет ротации SECRET_KEY | `settings.py:8` | runbook |
| SEC-P3-2 | Cookies без SECURE | `settings.py` | `SESSION_COOKIE_SECURE = True` на проде |
| SEC-P3-3 | Нет HSTS | nginx/Django | `SECURE_HSTS_SECONDS = 31536000` |

## Top-10 для Sprint 2.2 (приоритизация)

1. **FE-P1-1** Регистрация `ONAPPINSTALL/UNINSTALL`
2. **SEC-P1-2** Проверка прав в `approval_detail`
3. **PY-P2-1** N+1 в `list_requests`
4. **FE-P1-3** UI для `bot_issue` (если не успели в 2.1)
5. **FE-P1-2** Endpoint `/api/users/list`
6. **SEC-P1-1** Шифрование OAuth токенов
7. **SEC-P2-1** Подпись webhook
8. **SEC-P1-5** CSRF на бизнес-endpoints
9. **PY-P2-3** Усечение списков в bot message
10. **B24-A3** Batch `vote → update + message.update`

## Метрики (после Sprint 2.1)

- ✅ Уменьшено количество REST-вызовов на `create()`: ~−5/запрос (≈80% reduction)
- ✅ Уменьшено количество REST-вызовов на `handle_vote` для имён пользователей: с N до 1 (≈50–60% reduction)
- ✅ Race condition в голосовании закрыт.
- ⏳ N+1 в `list_requests` — остаётся (Sprint 2.2).
- ⏳ Тестовое покрытие — 0% (Sprint 2.2).
