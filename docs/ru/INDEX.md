# 📚 Указатель документации на русском

Полный справочник документации приложения для согласований на русском языке.

**Начните отсюда**: [../README.md](../README.md) — верхнеуровневый индекс всей документации с навигацией по ролям.

## Главные документы

### 🎯 [README.md](../../README.md)
**Начните отсюда!**
- Общее описание приложения
- Функциональность и особенности
- Требования и права доступа
- Быстрый старт
- Структура проекта

---

## Архитектура и дизайн

### 🏗️ [ARCHITECTURE.md](ARCHITECTURE.md)
Проектирование системы в целом
- Общая архитектура приложения
- Основные модули и компоненты
- Жизненный цикл запроса
- Потоки данных
- Паттерны проектирования
- Оптимизация и масштабирование
- Безопасность

### 🔌 [BITRIX24_INTEGRATION.md](BITRIX24_INTEGRATION.md)
Интеграция с Bitrix24 API
- OAuth и аутентификация
- Необходимые права доступа
- Регистрация и управление ботом
- Привязка размещений (Placement)
- Хранилище сущностей (Entity Storage)
- Загрузка файлов (Disk)
- Получение информации о пользователях
- Webhooks и события
- Обработка ошибок
- Ограничения и квоты

---

## Реализация

### 🔌 [API.md](API.md)
Справочник REST API endpoints
- Создание запросов согласования
- Получение и список запросов
- Отправка голосов
- Получение результатов голосования
- Установка приложения
- Коды ответов и ошибки
- Примеры использования

### 💻 [FRONTEND.md](FRONTEND.md)
Архитектура фронтенда
- Структура проекта Vue 3 + Nuxt
- Установка и запуск
- Основные компоненты (Form, Card, Buttons)
- Pinia хранилища (API, Auth, Approvals)
- Composables (useB24Frame, useApprovalData)
- Страницы (index, install)
- Стилизация (Tailwind CSS, CSS переменные)
- i18n локализация
- Тестирование
- Обработка ошибок

### 📊 [DATABASE.md](DATABASE.md)
Схема базы данных
- Хранилище сущностей Bitrix24 (appr_requests, approval_votes)
- PostgreSQL таблицы (опционально)
- Отношения между сущностями
- Жизненный цикл данных
- Индексы и оптимизация
- Резервное копирование
- Валидация данных

---

## Развертывание и операции

### 🚀 [DEPLOYMENT.md](DEPLOYMENT.md)
Развертывание на продакшене
- Предварительная проверка
- Требования сервера
- Установка зависимостей
- Переменные окружения
- Docker Compose развертывание
- SSL/HTTPS (Let's Encrypt)
- Nginx конфигурация
- Мониторинг здоровья
- Резервное копирование БД
- Масштабирование
- Откат на предыдущую версию
- Решение проблем

---

## Разработка

### 👨‍💻 [DEVELOPMENT.md](DEVELOPMENT.md)
Руководство для разработчиков
- Начало работы (клонирование, установка)
- Окружение разработки
- Стиль кода (TypeScript, Python)
- Git рабочий процесс
- Тестирование (фронтенд, бэкенд)
- Отладка
- Добавление новых функций
- Оптимизация производительности
- Безопасность
- Частые задачи

---

## Аудит и QA

### 🔍 [reviews/README.md](reviews/README.md)
Sprint 1 — Код-ревью (executive summary)
- [architecture-audit.md](reviews/architecture-audit.md) — сверка документации с кодом
- [python-backend-review.md](reviews/python-backend-review.md) — ревью Django backend
- [frontend-review.md](reviews/frontend-review.md) — ревью Vue 3 / Nuxt 3
- [bitrix24-api-compliance.md](reviews/bitrix24-api-compliance.md) — REST методы и события
- [user-stories-matrix.md](reviews/user-stories-matrix.md) — покрытие US кодом
- [bugs-and-optimizations.md](reviews/bugs-and-optimizations.md) — каталог из 42 находок
- [security-audit.md](reviews/security-audit.md) — OWASP + 152-ФЗ

### ✅ Отчёты Sprint 2 (итерации) и Sprint 3
- [qa/iteration-2.1-results.md](qa/iteration-2.1-results.md) — Sprint 2.1: критические баги (P0)
- [qa/iteration-2.2-results.md](qa/iteration-2.2-results.md) — Sprint 2.2: stateless-рефактор + security + тесты
- [qa/iteration-2.3-results.md](qa/iteration-2.3-results.md) — Sprint 2.3: UX-polish + CI + актуализация доки
- [qa/sprint-3-results.md](qa/sprint-3-results.md) — Sprint 3: маркетинговые материалы для Битрикс24 Маркетплейс

---

## Маркетплейс — материалы для публикации

### 🛒 [marketplace/](marketplace/)
Sprint 3 — комплект для отправки на модерацию
- [requirements-checklist.md](marketplace/requirements-checklist.md) — общие требования и регламент Битрикс24
- [positioning.md](marketplace/positioning.md) — ICP, value proposition, конкурентный анализ
- [copy.md](marketplace/copy.md) — название, слоган, описание, ключевые слова, описание установки
- [visuals-brief.md](marketplace/visuals-brief.md) — бриф для дизайнера: иконки, скриншоты, видео-демо
- [pricing.md](marketplace/pricing.md) — модель монетизации (подписка Битрикс24 Маркетплейс)
- [manifest-guide.md](marketplace/manifest-guide.md) — пояснения к [`/app.json`](../../app.json)
- [support.md](marketplace/support.md) — каналы поддержки, регламент, FAQ
- [submission-checklist.md](marketplace/submission-checklist.md) — финальный чек-лист перед сабмитом
- [legal/](marketplace/legal/) — юридические документы: EULA, Privacy Policy, согласие на ПДн

---

## Проблемы и поддержка

### 🐛 [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
Типичные проблемы и решения
- **Установка**: Не запускается, placement не найден, dialogId пуст
- **Аутентификация**: Invalid token, пользователь не может голосовать
- **API/Бэкенд**: Сообщение не публикуется, голоса не сохраняются, 500 ошибки
- **Фронтенд**: Мастер зависает, валидация не работает
- **Bitrix24**: Ошибки keyboard, entity не найдена
- **БД**: Ошибки подключения, зависшие запросы
- **Диагностика**: Трассировка потока, debug логирование

---

## Быстрые ссылки

### По функциональности

**Установка приложения**
→ [README.md](../../README.md) → Раздел "Быстрый старт"

**Создание запроса согласования**
→ [FRONTEND.md](FRONTEND.md) → ApprovalForm
→ [API.md](API.md) → POST /api/approval/create

**Голосование**
→ [FRONTEND.md](FRONTEND.md) → VoteButtons
→ [API.md](API.md) → POST /api/vote/handle

**Интеграция Bitrix24**
→ [BITRIX24_INTEGRATION.md](BITRIX24_INTEGRATION.md)

**Ошибка при голосовании**
→ [TROUBLESHOOTING.md](TROUBLESHOOTING.md) → "Пользователь не может голосовать"

**Сообщение бота не появляется**
→ [TROUBLESHOOTING.md](TROUBLESHOOTING.md) → "Сообщение бота не публикуется"

### По роли

**Разработчик**:
1. [README.md](../../README.md) - Начало
2. [DEVELOPMENT.md](DEVELOPMENT.md) - Настройка окружения
3. [ARCHITECTURE.md](ARCHITECTURE.md) - Понимание системы
4. [FRONTEND.md](FRONTEND.md) или [API.md](API.md) - Ваша область
5. [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - При проблемах

**DevOps/Оператор**:
1. [README.md](../../README.md) - Начало
2. [DEPLOYMENT.md](DEPLOYMENT.md) - Развертывание
3. [DATABASE.md](DATABASE.md) - Управление БД
4. [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - При проблемах

**Администратор Bitrix24**:
1. [README.md](../../README.md) - Функциональность
2. [BITRIX24_INTEGRATION.md](BITRIX24_INTEGRATION.md) - Интеграция
3. [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Поддержка

**Пользователь**:
1. [README.md](../../README.md) - Разделы "Функциональность" и "Использование"
2. [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - При проблемах

---

## Дополнительные ресурсы

### Официальная документация

- **Bitrix24 REST API**: https://dev.1c-bitrix.ru/rest_help/
- **Bitrix24 Entity Storage**: https://dev.1c-bitrix.ru/rest_help/im/entity/
- **Bitrix24 Bot Platform**: https://dev.1c-bitrix.ru/rest_help/im/imbot/
- **B24 UI Kit**: https://bitrix24.github.io/b24ui/

### Технологии

- **Vue 3**: https://vuejs.org/
- **Nuxt 3**: https://nuxt.com/
- **TypeScript**: https://www.typescriptlang.org/
- **Django**: https://www.djangoproject.com/
- **PostgreSQL**: https://www.postgresql.org/
- **Docker**: https://www.docker.com/

---

## Таблица соответствия

| Раздел | Документ | Для кого |
|--------|----------|----------|
| Начало | README.md | Все |
| Архитектура | ARCHITECTURE.md | Разработчики |
| Интеграция | BITRIX24_INTEGRATION.md | Разработчики, Администраторы |
| REST API | API.md | Разработчики, Backend |
| Фронтенд | FRONTEND.md | Frontend разработчики |
| База данных | DATABASE.md | Backend, DevOps |
| Развертывание | DEPLOYMENT.md | DevOps, Администраторы |
| Разработка | DEVELOPMENT.md | Разработчики |
| Проблемы | TROUBLESHOOTING.md | Все (при проблемах) |

---

## Версия документации

**Последнее обновление**: Апрель 2026  
**Версия**: 1.0

---

**Не нашли ответ?**
- Проверьте [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- Создайте issue в репозитории
- Свяжитесь с командой разработки
