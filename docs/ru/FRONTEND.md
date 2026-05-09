# Архитектура фронтенда

Руководство по архитектуре Vue 3 + Nuxt фронтенда.

## Структура проекта

```
frontend/
├── app/
│   ├── pages/              # Автоматически маршрутизируемые страницы
│   │   ├── index.client.vue      # Главная страница
│   │   └── install.client.vue    # Мастер установки
│   ├── components/         # Переиспользуемые компоненты
│   │   ├── ApprovalForm.vue      # Форма создания запроса
│   │   ├── ApprovalCard.vue      # Отображение запроса
│   │   ├── VoteButtons.vue       # Кнопки голосования
│   │   └── StatusBadge.vue       # Индикатор статуса
│   ├── composables/        # Composition API хуки
│   │   ├── useB24Frame.ts        # Интеграция Bitrix24
│   │   ├── useApprovalData.ts    # Управление данными
│   │   └── useAuth.ts            # Аутентификация
│   ├── stores/             # Pinia хранилища
│   │   ├── api.ts          # API клиент
│   │   ├── auth.ts         # Аутентификация
│   │   └── approvals.ts    # Запросы согласования
│   ├── utils/              # Утилиты
│   │   ├── validators.ts   # Валидация форм
│   │   └── formatters.ts   # Форматирование данных
│   └── app.vue             # Корневой компонент
├── locales/                # i18n файлы перевода
├── assets/css/             # Стили
├── nuxt.config.ts          # Конфигурация
├── tailwind.config.ts      # Tailwind CSS
└── package.json
```

## Установка и запуск

```bash
# Установка зависимостей
cd frontend
npm install

# Разработка
npm run dev
# http://localhost:3000

# Продакшен
npm run build
npm run preview
```

## Основные компоненты

### ApprovalForm
Форма для создания новых запросов согласования.

**Функциональность**:
- Ввод комментария
- Выбор согласующих
- Загрузка файла
- Валидация формы

```typescript
<ApprovalForm @request-created="onCreated" />
```

### ApprovalCard
Отображение карточки запроса с деталями.

```typescript
<ApprovalCard 
  :request="approval"
  :is-approver="userIsApprover"
  show-actions
/>
```

### VoteButtons
Кнопки для голосования.

```typescript
<VoteButtons 
  :request-id="requestId"
  :user-vote="userVote"
  @vote="handleVote"
/>
```

## Pinia хранилища

### API Store
Взаимодействие с бэкенд API.

```typescript
const apiStore = useApiStore()

// Создать запрос
await apiStore.postApproval(data)

// Получить запросы
const requests = await apiStore.getApprovalList()

// Отправить голос
await apiStore.postVote(requestId, decision)
```

### Auth Store
Управление аутентификацией.

```typescript
const authStore = useAuthStore()

// Текущий пользователь
console.log(authStore.user)

// Инициализация
await authStore.initialize()
```

### Approvals Store
Управление данными запросов.

```typescript
const approvalsStore = useApprovalsStore()

// Загрузить запросы
await approvalsStore.loadRequests()

// Текущий запрос
approvalsStore.currentRequest
```

## Composables

### useB24Frame
Интеграция с Bitrix24 фреймом.

```typescript
const { $b24, isReady } = useB24Frame()

if (isReady.value) {
  const userId = $b24.value.getContext().USER_ID
}
```

### useApprovalData
Бизнес-логика согласований.

```typescript
const { createApproval, submitVote } = useApprovalData()

// Создать запрос
await createApproval(formData)

// Отправить голос
await submitVote(requestId, 'APPROVE')
```

## Страницы

### index.client.vue
Главная страница с списком запросов.

**Показывает**:
- Запросы текущего пользователя (как инициатор)
- Запросы где пользователь согласующий
- Форма для создания нового запроса

### install.client.vue
Мастер установки приложения.

**Этапы установки**:
1. Init - инициализация
2. Demo - демо
3. Placement - привязка размещения
4. UserFields - регистрация полей
5. ServerSide - настройка бэкенда
6. Finish - завершение

```typescript
const steps = ref({
  init: { caption: 'Инициализация...', action: makeInit },
  placement: { caption: 'Настройка...', action: makePlacement },
  // ...
})

onMounted(async () => {
  for (const [key, step] of Object.entries(steps.value)) {
    await step.action()
  }
})
```

## Стилизация

### Tailwind CSS
Используется для всех стилей.

```vue
<div class="mx-auto max-w-2xl p-6">
  <h1 class="text-3xl font-bold text-gray-900 mb-4">
    Запросы согласования
  </h1>
</div>
```

### CSS переменные
```css
:root {
  --color-primary: #007bff;
  --color-success: #28a745;
  --color-danger: #dc3545;
}
```

## i18n Локализация

### Файлы переводов
```
locales/
├── en.json
└── ru.json
```

**Использование**:
```typescript
const { t } = useI18n()
```

```vue
<label>{{ t('form.approval.comment') }}</label>
```

## Тестирование

```bash
# Запуск тестов
npm run test

# Watch режим
npm run test -- --watch

# Coverage
npm run test -- --coverage
```

**Пример теста**:
```typescript
import { mount } from '@vue/test-utils'
import VoteButtons from '@/components/VoteButtons.vue'

test('отправляет голос при клике', async () => {
  const wrapper = mount(VoteButtons, {
    props: { requestId: '123' }
  })
  
  await wrapper.find('[data-testid="approve-btn"]').trigger('click')
  expect(wrapper.emitted('vote')).toBeTruthy()
})
```

## Обработка ошибок

```typescript
try {
  await apiStore.postApproval(formData)
  successMessage.value = 'Успешно создано'
} catch (error) {
  errorMessage.value = error.message
}
```

## Лучшие практики

1. **TypeScript**: Используйте везде
2. **Composition API**: Вместо Options API
3. **Computed properties**: Для дорогостоящих вычислений
4. **Lazy loading**: Загружайте компоненты по требованию
5. **Accessibility**: Используйте ARIA атрибуты

---

**Последнее обновление**: Апрель 2026
