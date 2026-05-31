# Документация — Приложение для согласований в чате Bitrix24

Полный справочник документации проекта **Приложение для согласований в чате Bitrix24** (Chat Approval App). Эта папка содержит технические спецификации, архитектурные материалы, руководства для разработчиков и операторов, а также материалы для маркетплейса.

## Быстрая навигация

### 🌐 Начните отсюда
- **[../README.md](../README.md)** — основной README проекта. Функциональность, требования, быстрый старт.

### 🇷🇺 Полная техническая документация (Русский)
- **[ru/INDEX.md](ru/INDEX.md)** — главный индекс всей документации на русском языке. Карта всех разделов, быстрые ссылки по ролям и функциям, таблица соответствия.

#### Архитектура и дизайн
- **[ru/ARCHITECTURE.md](ru/ARCHITECTURE.md)** — общая архитектура приложения, основные модули, жизненный цикл запроса, потоки данных, паттерны, оптимизация и безопасность.
- **[architecture/overview.md](architecture/overview.md)** — краткая сводка архитектуры (фронт / хранение данных / синхронизация / интеграция Bitrix24).
- **[architecture/feature-map.md](architecture/feature-map.md)** — карта функций: какие файлы реализуют какие фичи (таблица с путями и строками кода).

#### Реализация
- **[ru/API.md](ru/API.md)** — справочник REST API endpoints (создание, получение, голосование).
- **[ru/FRONTEND.md](ru/FRONTEND.md)** — архитектура фронтенда (Vue 3 + Nuxt 3, компоненты, Pinia, composables).
- **[ru/DATABASE.md](ru/DATABASE.md)** — схема Bitrix24 Entity Storage и опциональной PostgreSQL.
- **[ru/BITRIX24_INTEGRATION.md](ru/BITRIX24_INTEGRATION.md)** — интеграция с Bitrix24 (OAuth, скоупы, бот, placement, entity, disk).

#### Развертывание и операции
- **[ru/DEPLOYMENT.md](ru/DEPLOYMENT.md)** — развертывание на продакшене (Docker, SSL, Nginx, мониторинг, откат).
- **[ru/DEVELOPMENT.md](ru/DEVELOPMENT.md)** — руководство для разработчиков (окружение, стиль кода, тестирование, отладка).
- **[ru/TROUBLESHOOTING.md](ru/TROUBLESHOOTING.md)** — типичные проблемы и решения (установка, аутентификация, API, фронтенд, БД).

#### Аудит и QA
- **[ru/reviews/](ru/reviews/)** — результаты Sprint 1 код-ревью (архитектура, бэкенд, фронтенд, API-соответствие, безопасность).
- **[ru/qa/](ru/qa/)** — отчёты итераций Sprint 2 и 3 (критические баги, рефакторинг, маркетинговые материалы).

#### Маркетплейс Bitrix24
- **[ru/marketplace/](ru/marketplace/)** — полный комплект документов для публикации на Bitrix24 Маркетплейс:
  - [requirements-checklist.md](ru/marketplace/requirements-checklist.md) — требования модерации и регламент.
  - [positioning.md](ru/marketplace/positioning.md) — позиционирование, ICP, конкурентный анализ.
  - [copy.md](ru/marketplace/copy.md) — название, описание, ключевые слова, инструкции установки.
  - [visuals-brief.md](ru/marketplace/visuals-brief.md) — бриф для дизайнера (иконки, скриншоты, видео).
  - [pricing.md](ru/marketplace/pricing.md) — модель монетизации.
  - [manifest-guide.md](ru/marketplace/manifest-guide.md) — пояснения к `app.json`.
  - [support.md](ru/marketplace/support.md) — каналы поддержки и FAQ.
  - [submission-checklist.md](ru/marketplace/submission-checklist.md) — финальный чек-лист перед сабмитом.
  - [legal/](ru/marketplace/legal/) — EULA, Privacy Policy, согласие на ПДн.

### 📋 Логи изменений

- **[CHANGELOG.md](CHANGELOG.md)** — технический changelog проекта (Added/Changed/Fixed/Removed в формате Keep a Changelog). Групповано по датам/спринтам.
- **[RELEASES.md](RELEASES.md)** — релизы для пользователей (человеческий язык, что умеет приложение, какие фичи добавлены/исправлены).

### 📚 Другие материалы
- **[specification.md](specification.md)** — спецификация приложения (назначение, контекст, акторы, user flow, детальная логика).
- **[internal-technical-notes.md](internal-technical-notes.md)** — внутренний рабочий документ для навигации по архитектуре и задачам.
- **[superpowers/](superpowers/)** — документация по использованию инструментов разработки (Claude Code skills).

---

## Как вести документацию

Принцип: **НЕ плодить дубли**. Достраиваем недостающее и ссылаемся на существующее.

### 📌 Правила логирования

1. **Каждое технического изменение приложения** логируется в [`CHANGELOG.md`](CHANGELOG.md):
   - Формат: Keep a Changelog (Added/Changed/Fixed/Removed).
   - Уровень: технический (для разработчиков).
   - Примеры: "Исправлена ошибка IM_TEXTAREA placement", "Добавлена статeless-архитектура", "Удален Python backend".

2. **Пользовательские релизы и фичи** логируются в [`RELEASES.md`](RELEASES.md):
   - Формат: семантический (версия X.Y.Z).
   - Уровень: пользовательский (для администраторов Bitrix24).
   - Примеры: "Приложение теперь умеет создавать запросы в чате", "Добавлена поддержка вложений".

3. **Новая фича или компонент** отражается в [`architecture/feature-map.md`](architecture/feature-map.md):
   - Таблица "Фича → файлы:строки".
   - Обновляется одновременно с кодом или сразу после.

### 📖 Структура новой документации

При добавлении нового раздела:

1. Добавь ссылку в [`ru/INDEX.md`](ru/INDEX.md) (раздел «Быстрые ссылки»).
2. Используй **относительные ссылки** (`../../../...`) для кроссреференций.
3. Оживи примерами из реального кода (пути и строки).
4. Ссылайся на внешние источники (Bitrix24 API docs, Vue/Nuxt docs) только по необходимости.

### ✅ Проверка ссылок

Все ссылки в документации должны быть рабочими:
- Перед коммитом проверь, что файлы существуют по указанным путям.
- Используй только относительные пути (от папки `docs/`).
- Относительные пути из подпапок (например, из `docs/architecture/`) тоже должны работать.

---

## Навигация по ролям

| Роль | Начните с | Затем |
|------|-----------|-------|
| **Разработчик (Frontend)** | [../README.md](../README.md) | [ru/DEVELOPMENT.md](ru/DEVELOPMENT.md) → [ru/ARCHITECTURE.md](ru/ARCHITECTURE.md) → [ru/FRONTEND.md](ru/FRONTEND.md) → [architecture/feature-map.md](architecture/feature-map.md) |
| **Разработчик (Backend)** | [../README.md](../README.md) | [ru/DEVELOPMENT.md](ru/DEVELOPMENT.md) → [ru/API.md](ru/API.md) → [ru/BITRIX24_INTEGRATION.md](ru/BITRIX24_INTEGRATION.md) |
| **DevOps / Оператор** | [../README.md](../README.md) | [ru/DEPLOYMENT.md](ru/DEPLOYMENT.md) → [ru/DATABASE.md](ru/DATABASE.md) → [ru/TROUBLESHOOTING.md](ru/TROUBLESHOOTING.md) |
| **Администратор Bitrix24** | [../README.md](../README.md) → [ru/BITRIX24_INTEGRATION.md](ru/BITRIX24_INTEGRATION.md) | [ru/TROUBLESHOOTING.md](ru/TROUBLESHOOTING.md) |
| **Маркетинг / Продакт** | [ru/marketplace/positioning.md](ru/marketplace/positioning.md) | [ru/marketplace/requirements-checklist.md](ru/marketplace/requirements-checklist.md) → [ru/marketplace/copy.md](ru/marketplace/copy.md) → [ru/marketplace/submission-checklist.md](ru/marketplace/submission-checklist.md) |

---

## Версия документации

**Последнее обновление**: май 2026  
**Версия**: 1.1

---

**Не нашли ответ?**
- Проверьте [ru/TROUBLESHOOTING.md](ru/TROUBLESHOOTING.md).
- Посмотрите примеры в [architecture/feature-map.md](architecture/feature-map.md).
- Создайте issue в репозитории.
