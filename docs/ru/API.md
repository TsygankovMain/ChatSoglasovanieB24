# Справочник REST API

Полная документация API endpoints приложения для согласований.

## Базовый URL

```
Разработка:   http://localhost:8000
Docker:       http://api-python:8000
Продакшен:    https://ваш-домен.com/api
```

## Основные endpoints

### Создать запрос согласования

```
POST /api/approval/create
```

**Тело запроса**:
```json
{
  "comment": "Пожалуйста, проверьте предложение",
  "approver_ids": [2, 3, 4],
  "threshold_type": "ALL",
  "dialog_id": "chat123",
  "file_ids": ["file_id_1"]
}
```

**Ответ (201 Created)**:
```json
{
  "request_id": "req-1704067200-1",
  "status": "collecting",
  "message_id": "456",
  "created_at": "2026-04-24T10:00:00Z",
  "initiator_id": "1",
  "total_approvers": 3,
  "approved_count": 0,
  "rejected_count": 0,
  "pending_count": 3
}
```

### Получить запрос

```
GET /api/approval/{request_id}
```

**Ответ (200 OK)**:
```json
{
  "id": "req-1704067200-1",
  "initiator_id": "1",
  "comment": "Пожалуйста, проверьте предложение",
  "status": "collecting",
  "approver_ids": [2, 3, 4],
  "votes": [
    {
      "user_id": 2,
      "decision": "APPROVE",
      "voted_at": "2026-04-24T10:05:00Z"
    }
  ],
  "aggregates": {
    "total_approvers": 3,
    "approved_count": 1,
    "rejected_count": 0,
    "pending_count": 2
  }
}
```

### Список запросов

```
GET /api/approval/list?status=collecting&page=1&limit=20
```

**Параметры**:
- `status`: collecting, approved, rejected
- `page`: Номер страницы
- `limit`: Элементов на странице

**Ответ**:
```json
{
  "data": [
    {
      "id": "req-1704067200-1",
      "comment": "Проверка предложения",
      "status": "collecting",
      "created_at": "2026-04-24T10:00:00Z",
      "aggregates": {
        "total_approvers": 3,
        "approved_count": 1
      }
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 42,
    "pages": 3
  }
}
```

### Запросы где пользователь согласующий

```
GET /api/approval/as-approver
```

Возвращает список запросов, где текущий пользователь указан как согласующий.

### Отправить голос

```
POST /api/vote/handle
```

**Тело запроса**:
```json
{
  "request_id": "req-1704067200-1",
  "decision": "APPROVE",
  "comment": "Одобрено финансовым отделом"
}
```

**Ответ (200 OK)**:
```json
{
  "vote_id": "vote-req-1704067200-1-2",
  "request_id": "req-1704067200-1",
  "user_id": "2",
  "decision": "APPROVE",
  "voted_at": "2026-04-24T10:05:00Z",
  "request_status": "collecting",
  "aggregates": {
    "total_approvers": 3,
    "approved_count": 1,
    "rejected_count": 0,
    "pending_count": 2
  }
}
```

### Получить голоса для запроса

```
GET /api/vote/{request_id}
```

**Ответ (200 OK)**:
```json
{
  "request_id": "req-1704067200-1",
  "votes": [
    {
      "user_id": "2",
      "user_name": "Алиса Смирнова",
      "decision": "APPROVE",
      "comment": "Выглядит хорошо",
      "voted_at": "2026-04-24T10:05:00Z"
    },
    {
      "user_id": "3",
      "user_name": "Боб Петров",
      "decision": "REJECT",
      "comment": "Нужна доработка",
      "voted_at": "2026-04-24T10:07:00Z"
    }
  ]
}
```

### Установка приложения

```
POST /api/install
```

**Тело запроса**:
```json
{
  "DOMAIN": "portal.bitrix24.ru",
  "AUTH_ID": "access_token_123",
  "REFRESH_ID": "refresh_token_123",
  "user_id": 1,
  "appId": 123,
  "appCode": "approval_app"
}
```

**Ответ (200 OK)**:
```json
{
  "status": "success",
  "steps": {
    "init": "ok",
    "placement": "ok",
    "entity_storages": "ok"
  },
  "bot_id": "123",
  "folder_id": "folder_456"
}
```

## Коды ответов

| Код | Значение |
|-----|----------|
| 200 | OK |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 409 | Conflict |
| 500 | Internal Server Error |

## Формат ошибок

```json
{
  "error": "INVALID_PARAMS",
  "message": "approver_ids не может быть пустым"
}
```

## Примеры использования

### Создание запроса с помощью curl

```bash
curl -X POST http://localhost:8000/api/approval/create \
  -H "Authorization: Bearer token_123" \
  -H "Content-Type: application/json" \
  -d '{
    "comment": "Проверьте квартальный бюджет",
    "approver_ids": [2, 3],
    "threshold_type": "ALL",
    "dialog_id": "chat123"
  }'
```

### Голосование

```bash
curl -X POST http://localhost:8000/api/vote/handle \
  -H "Authorization: Bearer token_123" \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "req-1704067200-1",
    "decision": "APPROVE",
    "comment": "Одобрено"
  }'
```

### Получение списка

```bash
curl -X GET "http://localhost:8000/api/approval/list?status=collecting&limit=10" \
  -H "Authorization: Bearer token_123"
```

---

**Последнее обновление**: Апрель 2026
