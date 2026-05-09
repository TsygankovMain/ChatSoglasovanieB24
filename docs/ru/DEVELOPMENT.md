# Руководство разработчика

Полное руководство для разработчиков, способствующих проекту.

## Начало работы

### Предварительные требования

- Git
- Node.js 18+
- Python 3.10+
- Docker & Docker Compose
- VS Code или IDE по выбору

### Клонирование

```bash
git clone <repo-url>
cd <repo-directory>
git checkout -b develop
```

### Установка зависимостей

```bash
# Фронтенд
cd frontend
npm install

# Бэкенд
cd backends/python
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Окружение разработки

### Полный стек (Docker)

```bash
# База данных + Python + фронтенд
docker-compose --profile python --profile frontend up -d

# Или через Make
make dev-python
```

### Только фронтенд

```bash
cd frontend
npm run dev
# http://localhost:3000
```

### Только бэкенд

```bash
cd backends/python
source venv/bin/activate
python -m uvicorn api.main:app --reload --port 8000
```

## Стиль кода

### Фронтенд (TypeScript + Vue)

```bash
cd frontend

# Линтинг
npm run lint

# Форматирование
npm run lint -- --fix
npm run format
```

**Правила**:
- PascalCase для компонентов
- camelCase для переменных/функций
- Используйте TypeScript везде
- Composition API вместо Options API

### Бэкенд (Python)

```bash
cd backends/python

# Format
black .

# Sort imports
isort .

# Check
flake8 .

# Type checking
mypy api
```

**Правила**:
- PEP 8 (88 символов макс. благодаря Black)
- Docstrings для всех публичных функций
- Type hints везде

## Git рабочий процесс

### Именование веток

```
main              # Production
├─ develop        # Integration
│  ├─ feature/*   # Новые функции
│  ├─ bugfix/*    # Исправления
│  └─ refactor/*  # Рефакторинг
```

### Формат коммитов

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Типы**:
- `feat`: Новая функция
- `fix`: Исправление баги
- `refactor`: Рефакторинг
- `docs`: Документация
- `test`: Тесты
- `chore`: Build/deps

**Примеры**:
```
feat(approval): добавить поле комментария голосующего
fix(frontend): исправить загрузку в мастере установки
refactor(api): упростить логику создания запроса
```

### Рабочий процесс

```bash
# Создаём ветку
git checkout -b feature/vote-comments

# Делаем изменения
# ... edit files ...

# Коммитим
git add .
git commit -m "feat(approval): добавить комментарий к голосу"

# Пушим
git push origin feature/vote-comments

# PR на develop
```

## Тестирование

### Фронтенд тесты

```bash
cd frontend

npm run test
npm run test -- --watch
npm run test -- --coverage
```

### Бэкенд тесты

```bash
cd backends/python

pytest
pytest -vv
pytest --cov=api
```

## Отладка

### Фронтенд

- DevTools (F12)
- Vue DevTools расширение
- Console логирование

### Бэкенд

```bash
# Debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# VS Code debugging
# .vscode/launch.json с конфигурацией
```

## Добавление функций

### Чеклист

- [ ] Дизайн UI/потока
- [ ] API endpoint
- [ ] Компоненты фронтенда
- [ ] Интеграция
- [ ] Тесты
- [ ] Документация
- [ ] Code review

### Пример: Добавить комментарий к голосу

**1. Бэкенд API**:
```python
@router.post("/vote/comment")
async def add_vote_comment(request_id: str, comment: str):
    """Добавить комментарий к голосу"""
    vote = update_vote_comment(request_id, comment)
    return {"vote_id": vote.id}
```

**2. Компонент**:
```typescript
<VoteCommentForm :request-id="requestId" />
```

**3. Тест**:
```typescript
test("отправить комментарий", async () => {
  const wrapper = mount(VoteCommentForm)
  await wrapper.find("textarea").setValue("Хорошо")
  await wrapper.find("form").trigger("submit")
  expect(wrapper.emitted("comment-added")).toBeTruthy()
})
```

**4. Документация**:
- Обновить API.md
- Обновить ARCHITECTURE.md

## Оптимизация производительности

### Фронтенд

```typescript
// Используйте computed
const filtered = computed(() => requests.filter(...))

// Lazy load компоненты
const Form = defineAsyncComponent(() => import('./Form.vue'))

// Debounce поиск
const search = useDebounceFn(query => {...}, 300)
```

### Бэкенд

```python
# Кэширование
@lru_cache(maxsize=100)
def get_user(user_id: int):
    return ...

# Batch запросы
results = client.call_batch({...})

# Индексы БД
CREATE INDEX idx_status ON requests(status)
```

## Безопасность

### Валидация входов

```typescript
// Фронтенд
if (!comment || comment.length > 1000) {
  return false
}

// Бэкенд
class ApprovalRequest(BaseModel):
    comment: str = Field(..., min_length=1, max_length=1000)
```

### Аутентификация

```python
# Проверка токена на каждый запрос
def get_current_user(request):
    token = extract_token(request)
    user = verify_token(token)
    if not user:
        raise HTTPException(401)
    return user
```

### XSS защита

```vue
<!-- ✅ Автоматически экранируется -->
<p>{{ userInput }}</p>

<!-- ❌ Не используйте -->
<p v-html="userInput"></p>
```

## Частые задачи

### Обновление зависимостей

```bash
# Фронтенд
npm outdated
npm update

# Бэкенд
pip list --outdated
pip install -U -r requirements.txt
```

### Добавление переменной окружения

1. Добавить в `.env.example`
2. Документировать в README.md
3. Использовать в коде
4. Обновить DEPLOYMENT.md

### Миграция БД

```bash
alembic revision --autogenerate -m "Добавить поле"
alembic upgrade head
```

---

**Последнее обновление**: Апрель 2026
