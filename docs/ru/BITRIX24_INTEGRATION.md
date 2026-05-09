# Интеграция Bitrix24

Полный справочник по интеграции Bitrix24 REST API.

## OAuth и аутентификация

### OAuth поток

```
1. Пользователь нажимает "Установить приложение"
2. Bitrix24 перенаправляет с временным кодом
3. Приложение обменивает код на токен доступа
4. Токен сохраняется в БД (зашифрован)
5. Все последующие вызовы используют токен
```

### Структура токена

```json
{
  "access_token": "53a34e48fbb3b061...",
  "expires_in": 3600,
  "refresh_token": "d8c7c8c9c0c1...",
  "scope": "im,imbot,entity,disk,placement,user",
  "user_id": 1
}
```

## Необходимые права доступа

| Право | Назначение | Обязательное |
|-------|-----------|------------|
| `im` | Мгновенные сообщения | ✅ Да |
| `imbot` | Управление ботом | ✅ Да |
| `entity` | Хранилище сущностей | ✅ Да |
| `disk` | Загрузка файлов | ✅ Да |
| `placement` | Привязка размещений | ✅ Да |
| `user` | Информация о пользователях | ✅ Да |
| `batch` | Batch операции | ⭕ Опционально |
| `crm` | CRM интеграция | ⭕ Опционально |

```bash
SCOPE=im,imbot,entity,disk,placement,user
```

## Регистрация бота

### Метод: `imbot.register`

```python
result = b24_client.register_bot(
    bot_name="Бот согласований",
    webhook_url="https://ваш-домен.com/webhook"
)
bot_id = result['BOT_ID']
```

**Параметры**:
```python
{
    "CODE": "approval_bot",
    "TYPE": "B",
    "EVENT_MESSAGE_ADD": webhook_url,
    "EVENT_BOT_DELETE": webhook_url,
    "PROPERTIES": {
        "NAME": "Бот согласований",
        "COLOR": "GREEN"
    }
}
```

## Публикация сообщений

### Метод: `imbot.message.add`

```python
result = b24_client.publish_bot_message(
    bot_id="123",
    dialog_id="chat123",
    message="Запрос согласования",
    keyboard=[...]
)
message_id = result['MESSAGE_ID']
```

### Кнопки клавиатуры

#### Тип: Command

```python
{
    "TEXT": "Согласовать",
    "COMMAND": "approval_vote",
    "COMMAND_PARAMS": json.dumps({"decision": "APPROVE"})
}
```

#### Тип: Action

```python
{
    "TEXT": "Открыть",
    "ACTION": "OPEN_SLIDER",
    "ACTION_VALUE": "slider_url"
}
```

#### Тип: Link

```python
{
    "TEXT": "Посмотреть",
    "LINK": "https://example.com"
}
```

## Привязка размещения (Placement)

### Метод: `placement.bind`

```python
b24_client.bind_placement(
    placement="IM_TEXTAREA",
    handler_url="https://ваш-домен.com/",
    title="Запрос согласования"
)
```

**Конфигурация**:
```python
{
    "PLACEMENT": "IM_TEXTAREA",
    "HANDLER": "https://ваш-домен.com/",
    "TITLE": "Запрос согласования",
    "OPTIONS": {
        "iconName": "Approval",
        "context": "ALL",
        "role": "USER",
        "color": "LIGHT_BLUE",
        "width": 400,
        "height": 300
    }
}
```

## Хранилище сущностей (Entity Storage)

### Создание сущности

**Метод**: `entity.add`

```python
entity_add(http_client, "appr_requests")
entity_add(http_client, "approval_votes")
```

### Определение свойств

**Метод**: `entity.item.property.add`

```python
entity_item_property_add(
    http_client,
    "appr_requests",
    "INITIATOR_ID",
    "ID инициатора",
    "S"  # S=String, I=Integer
)
```

### Операции с данными

**Create**:
```python
item_id = entity_item_add(
    http_client,
    "appr_requests",
    {
        "INITIATOR_ID": "1",
        "COMMENT": "Текст запроса",
        "STATUS": "collecting"
    }
)
```

**Read**:
```python
items = entity_item_get(
    http_client,
    "appr_requests",
    filter={"PROPERTY_STATUS": "collecting"}
)
```

**Update**:
```python
entity_item_update(
    http_client,
    "appr_requests",
    item_id,
    {"STATUS": "approved"}
)
```

## Загрузка файлов (Disk)

### Метод: `disk.folder.uploadfile`

```python
result = b24_client.http.call("disk.folder.uploadfile", {
    "FOLDER_ID": folder_id,
    "FILE_CONTENT": file_bytes,
    "FILE_NAME": "document.pdf"
})
file_id = result['FILE_ID']
```

## Получение информации о пользователе

### Метод: `user.get`

```python
result = b24_client.get_user_name("123")
# Возвращает: "John Doe"

# Полная информация
result = b24_client.http.call("user.get", {"ID": "123"})
```

## Webhooks и события

### Привязка события

**Метод**: `event.bind`

```python
b24_client.http.call("event.bind", {
    "event": "ONAPPINSTALL",
    "handler": "https://ваш-домен.com/webhook/install"
})
```

### События приложения

| События | Когда срабатывает |
|---------|------------------|
| `ONAPPINSTALL` | При установке |
| `ONAPPUNINSTALL` | При удалении |
| `ONIMBOTMESSAGEKEYBOARDBUTTON` | При клике на кнопку |

### Пример payload

```json
{
    "event": "ONIMBOTMESSAGEKEYBOARDBUTTON",
    "data": {
        "BOT_ID": "123",
        "DIALOG_ID": "chat123",
        "MESSAGE_ID": "456",
        "USER_ID": "1",
        "BUTTON_CODE": "approval_vote",
        "BUTTON_PARAMS": "{\"decision\": \"APPROVE\"}"
    }
}
```

## Обработка ошибок

### Типичные коды ошибок

| Код | Описание |
|-----|---------|
| `INVALID_TOKEN` | Токен истёк |
| `NO_AUTH` | Нет авторизации |
| `INVALID_PARAMS` | Неверные параметры |
| `INCORRECT_KEYBOARD_PARAMS` | Неверный формат кнопок |
| `SERVER_ERROR` | Ошибка сервера |

### Обработка ошибок клавиатуры

```python
try:
    # Попытка с объектом
    http.call("imbot.message.add", {
        "KEYBOARD": {"BUTTONS": buttons}
    })
except RuntimeError as e:
    if "Incorrect keyboard params" in str(e):
        # Повтор с массивом
        http.call("imbot.message.add", {
            "KEYBOARD": buttons
        })
```

## Ограничения и квоты

**Частота запросов**:
- 2 запроса в секунду per token
- 60 запросов в минуту per token

**Размеры**:
- Размер файла: Max 500 MB
- Текст сообщения: Max 4000 символов
- Кнопок в сообщении: Max 20

## Тестирование

### Sandbox портала

1. Создайте тестовый портал на bitrix24.ru
2. Установите приложение в режиме разработки
3. Используйте API Explorer для тестирования

---

**Последнее обновление**: Апрель 2026
