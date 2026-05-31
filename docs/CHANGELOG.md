# Changelog (Технический лог изменений)

Все значимые изменения в проекте документируются в этом файле по формату [Keep a Changelog](https://keepachangelog.com/).

Для пользовательских релизов см. [RELEASES.md](RELEASES.md).

---

## [Unreleased]

### Планируется
- Улучшение UI/UX (анимации, dark mode).
- Интеграция с Business Process (бизнес-процессы Bitrix24).
- Отчёты и экспорт истории согласований.

---

## Sprint 3 (2026-04-26)

### Added
- **Маркетинговые материалы для Bitrix24 Маркетплейс** в `docs/ru/marketplace/`:
  - `requirements-checklist.md` — полный чек-лист требований модерации.
  - `positioning.md` — ICP, value proposition, конкурентный анализ.
  - `copy.md` — название, слоган, описание, ключевые слова, инструкции.
  - `visuals-brief.md` — бриф для дизайнера (иконки 108×66, скриншоты, видео).
  - `pricing.md` — модель монетизации (подписка Bitrix24 Маркетплейс).
  - `manifest-guide.md` — пояснения к `app.json`.
  - `support.md` — каналы поддержки, FAQ, регламент.
  - `submission-checklist.md` — финальный чек-лист перед сабмитом.
  - `legal/` — EULA, Privacy Policy, согласие на ПДн.
- Документация структурирована под публикацию в маркетплейс.

---

## Sprint 2.3 (2026-04-24)

### Fixed
- **Критическое**: Исправлена ошибка `Argument 'iconName' is null or empty` при установке приложения.
  - В метод `placement.bind` для `IM_TEXTAREA` добавлен обязательный параметр `iconName: 'chat-compose'`.
  - Приложение успешно устанавливается в Bitrix24.

### Changed
- Актуализирован внутренний файл `docs/internal-technical-notes.md` (убрано упоминание Python-бэкенда, скорректирована нумерация разделов).

### Removed
- Удалён файл `FIX_PLAN.md` (задача успешно выполнена).
- Удалена устаревшая спецификация `2026-04-17-approval-workflow-design.md` (описывала Python/Django бэкенд, неактуальна).
- Удалена нерелевантная инструкция `instructions/PHP_CODE_REVIEW_INSTRUCTION.md` для ИИ-агента.

---

## Sprint 2.2 (2026-04-20)

### Added
- **Architeture Refactoring: Stateless Backend**
  - Отказ от собственной PostgreSQL БД в бэкенде.
  - Переход на полностью stateless-архитектуру (только Bitrix24 Entity Storage).
  - Все OAuth-токены хранятся только в JWT (фронт→бэк) или webhook-payload'е Bitrix24→бэк.
  - `B24AuthContext` (in-memory, без БД).

### Changed
- Обновлена архитектурная диаграмма в `docs/ru/ARCHITECTURE.md`:
  - Убрана зависимость от собственного backend-сервера для persistence.
  - Bitrix24 Entity Storage теперь единственный долгоживущий стор данных.

### Fixed
- Исправлены проблемы с concurrency при одновременном голосовании.
- Добавлена обработка конфликтов при обновлении статусов.

### Removed
- Удалена ORM-модель `Bitrix24Account` и `ApplicationInstallation` из бэкенда.
- Удалена зависимость от миграций PostgreSQL.

---

## Sprint 2.1 (2026-04-10)

### Added
- **P0 Bug Fixes**:
  - Фиксирована ошибка авторизации при webhook-событиях ONIMCOMMANDADD.
  - Фиксирована ошибка десериализации payload'а от Bitrix24.
  - Добавлена поддержка обоих форматов webhook-кнопок (legacy keyboard, современные event).

### Fixed
- Исправлены ошибки 500 при создании запроса без файла.
- Исправлена ошибка валидации голосующих (acceptor_ids → approver_ids).
- Улучшена обработка ошибок сетевого типа на фронтенде.

### Changed
- Обновлены логи ошибок для лучшей диагностики.

---

## Sprint 1 (разработка MVP)

### Added
- **Полная функциональность MVP**:
  - Создание запроса согласования из чата (`IM_TEXTAREA` placement).
  - Выбор списка согласующих (Bitrix24 `user.search` + `imbot.message.add` с кнопками голосования).
  - Голосование за/против (`APPROVE` / `REJECT`).
  - Правило согласования: все обязательно (`all`) или достаточно одного (`majority`).
  - Вложения файлов через Bitrix24.Disk.
  - Автообновление статуса сообщения бота при поступлении голосов.
  - Журнал событий и история голосования.

- **Frontend (Vue 3 + Nuxt 3 + TypeScript)**:
  - Компоненты:
    - `CreateForm.vue` — форма создания запроса.
    - `RequestCard.vue` — карточка запроса.
    - `VoteStatus.vue` — отображение статусов голосования.
    - `StatusBadge.vue` — значок статуса.
    - `EventLog.vue` — история событий.
    - `FileUploadArea.vue` — загрузка файлов.
  - Pinia stores: `approvalsStore`, `apiStore`, `userStore`, `userSettingsStore`, `appSettingsStore`, `pageStore`.
  - Composables: `useApproval()`, `useApprovalFiles()`, `useBackend()`, `useAppInit()`.
  - Страницы: `index.client.vue` (основная), `install.client.vue` (установка).

- **Backend (Python 3.11 + Django)**:
  - REST API endpoints:
    - `POST /api/approval/create` — создание запроса.
    - `GET /api/approval/{id}` — получение запроса.
    - `GET /api/approval/list/{role}` — список (initiator/approver).
    - `POST /api/vote/handle` — запись голоса.
    - `POST /api/install` — инициализация при установке.
  - Слой интеграции Bitrix24:
    - Регистрация бота (imbot.register).
    - Публикация и обновление сообщений (imbot.message.add/update).
    - Хранилище сущностей (entity.item.add/update/get).
    - Загрузка файлов (disk.folder.uploadfile).
    - Получение информации о пользователях (user.get, user.search).
  - Webhook-обработчик ONIMCOMMANDADD для событий голосования.
  - Обработка ошибок и валидация данных.

- **Инфраструктура**:
  - Docker и Docker Compose для dev/prod.
  - Поддержка Cloudpub-туннелирования (dev).
  - PostgreSQL (опционально для логирования).
  - Nginx reverse proxy (prod).
  - Makefile с командами `make dev-python`, `make prod-python`.

- **Документация (на русском)**:
  - `docs/ru/INDEX.md` — главный индекс.
  - `docs/ru/ARCHITECTURE.md` — архитектура системы.
  - `docs/ru/API.md` — REST API справочник.
  - `docs/ru/FRONTEND.md` — архитектура фронтенда.
  - `docs/ru/DATABASE.md` — схема хранилища.
  - `docs/ru/BITRIX24_INTEGRATION.md` — интеграция.
  - `docs/ru/DEPLOYMENT.md` — развертывание.
  - `docs/ru/DEVELOPMENT.md` — руководство разработчикам.
  - `docs/ru/TROUBLESHOOTING.md` — решение проблем.
  - `docs/specification.md` — спецификация приложения.
  - `docs/internal-technical-notes.md` — внутренние заметки.

- **Тестирование и QA**:
  - Основной набор unit-тестов для компонентов (Jest + Vue Test Utils).
  - E2E-сценарии для основного flow (создание → голосование → завершение).
  - Fixture-данные для мотестирования.

- **Code Review и Аудит**:
  - Sprint 1 Code Review: 42 находки (баги, оптимизации, безопасность).
  - Архитектурный аудит и соответствие документации.
  - Security Audit по OWASP и 152-ФЗ.

### Changed
- Инициализация приложения через Nuxt 3 composables вместо прямого Vue 2-стиля.
- Отказ от GraphQL в пользу REST API (проще для serverless-модели Bitrix24).

### Fixed
- Исправлены ошибки типизации TypeScript в composables и stores.
- Исправлены проблемы с CORS при запросах к Bitrix24 API.

---

## Легенда версий

- **Sprint N** — итерация разработки, охватывает новые фичи и исправления за период.
- **[X.Y.Z]** — семантическая версия (для будущих релизов на маркетплейс).
- **[Unreleased]** — текущая разработка, еще не в продакшене.

Для соответствия версий спринтов и релизов см. [RELEASES.md](RELEASES.md).
