# Схема базы данных

Документация по структуре данных и схеме базы данных.

## Хранилище сущностей Bitrix24

### appr_requests

Хранит данные запросов согласования.

| Поле | Тип | Описание |
|------|-----|---------|
| INITIATOR_ID | String | ID пользователя создателя |
| COMMENT | String | Описание запроса |
| APPROVER_IDS | String | JSON массив ID согласующих |
| THRESHOLD_TYPE | String | ALL / MAJORITY |
| STATUS | String | collecting / approved / rejected / expired / cancelled |
| DIALOG_ID | String | ID чата |
| BOT_MESSAGE_ID | String | ID сообщения бота |
| DISK_FOLDER_ID | String | ID папки на диске |
| FILE_IDS | String | JSON массив ID файлов |
| CREATED_AT | String | ISO timestamp |

**Пример**:
```json
{
  "ID": "req-1704067200-1",
  "PROPERTY_VALUES": {
    "INITIATOR_ID": "1",
    "COMMENT": "Проверка Q2 бюджета",
    "APPROVER_IDS": "[2, 3, 4]",
    "STATUS": "collecting",
    "DIALOG_ID": "chat123"
  }
}
```

### approval_votes

Хранит решения голосующих.

| Поле | Тип | Описание |
|------|-----|---------|
| REQUEST_ID | String | ID запроса |
| USER_ID | String | ID голосующего |
| DECISION | String | APPROVE / REJECT |
| COMMENT | String | Комментарий голосующего |
| VOTED_AT | String | ISO timestamp |

**Пример**:
```json
{
  "ID": "vote-req-1704067200-1-2",
  "PROPERTY_VALUES": {
    "REQUEST_ID": "req-1704067200-1",
    "USER_ID": "2",
    "DECISION": "APPROVE",
    "VOTED_AT": "2026-04-24T10:05:00Z"
  }
}
```

## PostgreSQL (Опционально)

### requests таблица

```sql
CREATE TABLE requests (
  id VARCHAR(100) PRIMARY KEY,
  initiator_id INTEGER,
  comment TEXT,
  approver_ids TEXT,  -- JSON
  status VARCHAR(20),
  created_at TIMESTAMP,
  
  INDEX idx_status(status),
  INDEX idx_initiator(initiator_id)
);
```

### votes таблица

```sql
CREATE TABLE votes (
  id VARCHAR(100) PRIMARY KEY,
  request_id VARCHAR(100),
  user_id INTEGER,
  decision VARCHAR(20),
  voted_at TIMESTAMP,
  
  UNIQUE KEY unique_vote(request_id, user_id),
  INDEX idx_request(request_id)
);
```

### users таблица (кэш)

```sql
CREATE TABLE users (
  id INTEGER PRIMARY KEY,
  domain VARCHAR(100),
  name VARCHAR(255),
  last_name VARCHAR(255),
  fetched_at TIMESTAMP
);
```

### sessions таблица

```sql
CREATE TABLE sessions (
  id VARCHAR(100) PRIMARY KEY,
  domain VARCHAR(100),
  user_id INTEGER,
  access_token VARCHAR(1000),
  refresh_token VARCHAR(1000),
  token_expires_at TIMESTAMP,
  created_at TIMESTAMP
);
```

## Отношения между сущностями

```
appr_requests (1) ──────── approval_votes (Many)
      ↑
      └─ votes.REQUEST_ID → requests.ID
```

## Жизненный цикл данных

### Создание запроса
1. Фронтенд отправляет данные
2. Бэкенд создаёт item в appr_requests
3. Загружает файл (если есть)
4. Публикует сообщение бота
5. Сохраняет MESSAGE_ID

### Голосование
1. Согласующий нажимает кнопку
2. Создаётся/обновляется vote в approval_votes
3. Пересчитываются агрегаты
4. Обновляется STATUS в appr_requests
5. Обновляется сообщение бота

## Оптимизация и индексы

### Критические индексы

```sql
-- Быстрый поиск по статусу
CREATE INDEX idx_requests_status ON requests(status);

-- Быстрый поиск голосов запроса
CREATE INDEX idx_votes_request ON approval_votes(request_id);

-- Быстрый поиск по инициатору
CREATE INDEX idx_requests_initiator ON requests(initiator_id);
```

### Рекомендации производительности

- Используйте indexed фильтры (status, initiator_id)
- Избегайте полных сканов таблиц
- Для JSON поиска используйте денормализацию
- Кэшируйте часто используемые данные

## Резервное копирование

### Backup команда

```bash
# PostgreSQL
pg_dump -U user database_name > backup.sql

# С сжатием
pg_dump -U user database_name | gzip > backup.sql.gz
```

### Восстановление

```bash
# Restore
psql -U user database_name < backup.sql

# Из сжатого файла
gunzip < backup.sql.gz | psql -U user database_name
```

## Валидация данных

### Ограничения

```
INITIATOR_ID:  Required, valid user ID
COMMENT:       Required, 1-1000 chars
APPROVER_IDS:  Required, min 1 user
STATUS:        One of: collecting, approved, rejected, expired, cancelled
DECISION:      One of: APPROVE, REJECT
```

---

**Последнее обновление**: Апрель 2026
