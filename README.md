# Приложение для согласований в чате Bitrix24

Приложение для Bitrix24, реализующее процесс согласования прямо в чате портала. Инициатор создаёт запрос через размещение `IM_TEXTAREA`, бот публикует сообщение с интерактивными кнопками голосования, согласующие принимают решение, итоговый статус автоматически обновляется в карточке.

## Возможности

- Создание запроса согласования из любого чата (через размещение `IM_TEXTAREA`)
- Бот публикует сообщение с кнопками «Согласовать» / «Отклонить» / «Запросить уточнение»
- Несколько согласующих, опциональное правило «достаточно одного «за»» или «требуется единогласие»
- Прикрепление файлов из Bitrix24.Disk
- Журнал событий по каждому запросу
- Автообновление статуса сообщения бота при поступлении голосов
- Карточка с подробной информацией о запросе и истории голосования

## Технологии

| Слой | Технология |
|------|------------|
| Frontend | Vue 3 + Nuxt 3, Pinia, Tailwind CSS, [@bitrix24/b24ui-nuxt](https://bitrix24.github.io/b24ui/) |
| Backend | Python 3.11 + Django |
| База данных | PostgreSQL 17 + Bitrix24 Entity Storage |
| Инфраструктура | Docker, Docker Compose, Cloudpub (для dev туннелирования) |
| Bitrix24 API | `imbot.*`, `entity.*`, `placement.*`, `disk.*`, `user.get` |

> Альтернативный backend на PHP (Symfony 7) присутствует в `backends/php/` (статус реализации см. в технических заметках).

## Требования

- Docker и Docker Compose
- Портал Bitrix24 с правами администратора для установки приложения
- Зарегистрированное приложение в Bitrix24 (получение `CLIENT_ID` / `CLIENT_SECRET`)
- Скоупы: `im, imbot, entity, disk, placement, user`
- Публичный HTTPS-домен (или Cloudpub-туннель в dev)

## Быстрый старт (dev)

```bash
# 1. Скопировать переменные окружения
cp .env.example .env
# Заполнить: VIRTUAL_HOST, CLIENT_ID, CLIENT_SECRET, SCOPE, CLOUDPUB_TOKEN

# 2. Запустить Python backend + frontend + Cloudpub
make dev-python
# или
COMPOSE_PROFILES=frontend,python,cloudpub docker compose --env-file .env up --build
```

После старта установите приложение на портал Bitrix24, указав публичный URL (`VIRTUAL_HOST`) в качестве handler-URL.

## Структура проекта

```
.
├── backends/
│   ├── python/              # Django backend (основной)
│   └── php/                 # Symfony backend (альтернативный)
├── frontend/                # Vue 3 + Nuxt 3
│   └── app/
│       ├── pages/           # install, index
│       ├── components/      # approval/* — карточки, формы, кнопки
│       ├── stores/          # Pinia
│       └── composables/     # useB24Frame, useApprovalData
├── infrastructure/          # init.sql, конфиги
├── docs/
│   └── ru/                  # Документация (русский)
├── docker-compose.yml
├── Makefile                 # dev-python, prod-python, dev-php и т.д.
└── README.md
```

## Документация

Полная документация — в [docs/ru/INDEX.md](docs/ru/INDEX.md).

Ключевые разделы:
- [Архитектура](docs/ru/ARCHITECTURE.md)
- [REST API](docs/ru/API.md)
- [Frontend](docs/ru/FRONTEND.md)
- [База данных](docs/ru/DATABASE.md)
- [Интеграция Bitrix24](docs/ru/BITRIX24_INTEGRATION.md)
- [Развёртывание](docs/ru/DEPLOYMENT.md)
- [Разработка](docs/ru/DEVELOPMENT.md)
- [Решение проблем](docs/ru/TROUBLESHOOTING.md)

## Лицензия

См. файл `LICENSE` (если присутствует) или уточните у владельца репозитория.
