<script setup lang="ts">
import type { B24Frame } from '@bitrix24/b24jssdk'

const props = defineProps<{
  dialogId: string
  /** Optional text to pre-fill the comment field (e.g. from IM_CONTEXT_MENU). */
  prefillComment?: string
}>()

const emit = defineEmits<{
  (e: 'created' | 'cancel'): void
}>()

const { t } = useI18n()
const { $initializeB24Frame } = useNuxtApp()
const approval = useApproval()
const userStore = useUserStore()
const { files, addFiles, removeFile, clear: clearFiles } = useApprovalFiles()

type PortalUser = {
  id: string
  fio: string
  workPosition: string
}

type B24User = {
  ID?: string | number
  id?: string | number
  NAME?: string
  name?: string
  LAST_NAME?: string
  last_name?: string
  WORK_POSITION?: string
  work_position?: string
}

let $b24: B24Frame | null = null

const comment = ref(props.prefillComment ?? '')
const approverIds = ref<string[]>([])
const thresholdType = ref<'all' | 'majority'>('all')
const isSubmitting = ref(false)
const errorMsg = ref('')
const botIssueMsg = ref('')

// User loading & caching
const allUsers = ref<PortalUser[]>([])
const isLoadingUsers = ref(false)
const usersLoadError = ref('')

const thresholdOptions = computed(() => [
  { value: 'all', label: t('approval.threshold.all') },
  { value: 'majority', label: t('approval.threshold.majority') },
])

// Селект опции для выбора пользователей
const userSelectOptions = computed(() =>
  allUsers.value
    .filter(user => String(user.id) !== String(userStore.id))
    .map(user => ({
      value: user.id,
      label: user.workPosition ? `${user.fio} (${user.workPosition})` : user.fio,
    }))
)

async function ensureB24Frame(): Promise<B24Frame> {
  if ($b24) {
    return $b24
  }
  $b24 = await $initializeB24Frame()
  return $b24
}

/**
 * Загружает пользователей из Битрикс24 и кэширует их
 */
async function loadAndCacheUsers() {
  if (isLoadingUsers.value) return

  isLoadingUsers.value = true
  usersLoadError.value = ''

  try {
    const b24 = await ensureB24Frame()

    // Сначала пробуем загрузить из кэша (app.option)
    const optionsResponse = await b24.callMethod('app.option.get', {})
    const optionsData = optionsResponse.getData() as Record<string, unknown>
    const cachedUsers = optionsData.portalUsers
    const cacheTime = optionsData.portalUsersTime as number | undefined

    // Проверяем, не устарел ли кэш (обновляем каждые 5 минут)
    const now = Date.now()
    const cacheDuration = 5 * 60 * 1000 // 5 минут
    const isCacheValid = cacheTime && (now - cacheTime) < cacheDuration

    if (isCacheValid && Array.isArray(cachedUsers)) {
      if (import.meta.dev) console.debug('Loading users from cache', { count: cachedUsers.length })
      allUsers.value = cachedUsers as PortalUser[]
      return
    }

    // Загружаем с сервера через callListMethod
    if (import.meta.dev) console.debug('Loading users from Bitrix24...')
    const response = await b24.callListMethod('user.get', {
      FILTER: { USER_TYPE: 'employee', ACTIVE: 'Y' },
      SELECT: ['ID', 'NAME', 'LAST_NAME', 'WORK_POSITION'],
    })

    const usersData = response.getData() as B24User[]
    let users: PortalUser[] = []

    // Нормализуем результаты
    if (Array.isArray(usersData)) {
      users = usersData
        .map((user: B24User) => ({
          id: String(user.ID ?? user.id ?? '').trim(),
          fio: `${String(user.NAME ?? user.name ?? '')} ${String(user.LAST_NAME ?? user.last_name ?? '')}`.trim() || t('approval.user_default', { id: String(user.ID ?? user.id ?? '') }),
          workPosition: String(user.WORK_POSITION ?? user.work_position ?? '').trim(),
        }))
        .filter(user => user.id)
    }

    allUsers.value = users
    if (import.meta.dev) console.debug('Loaded users from Bitrix24', { count: users.length })

    // Сохраняем в кэш в фоне — не блокируем UI ожиданием ack от Bitrix24,
    // селект уже наполнен из allUsers.value. Ошибка записи кэша не критична.
    b24.callMethod('app.option.set', {
      portalUsers: users,
      portalUsersTime: now,
    }).catch(err => {
      if (import.meta.dev) console.warn('app.option.set (users cache) failed:', err)
    })
  } catch (error) {
    usersLoadError.value = t('approval.form.error.user_search_failed')
    if (import.meta.dev) console.error('Failed to load users:', error)
    // Пытаемся хотя бы загрузить из старого кэша при ошибке
    try {
      const b24 = await ensureB24Frame()
      const optionsResponse = await b24.callMethod('app.option.get', {})
      const optionsData = optionsResponse.getData() as Record<string, unknown>
      if (Array.isArray(optionsData.portalUsers)) {
        allUsers.value = optionsData.portalUsers as PortalUser[]
        usersLoadError.value = ''
      }
    } catch (cacheError) {
      if (import.meta.dev) console.error('Failed to load from cache:', cacheError)
    }
  } finally {
    isLoadingUsers.value = false
  }
}

async function submit() {
  errorMsg.value = ''
  approverIds.value = approverIds.value.filter(id => String(id) !== String(userStore.id))
  if (!comment.value.trim()) {
    errorMsg.value = t('approval.form.error.comment_required')
    return
  }
  if (approverIds.value.length === 0) {
    errorMsg.value = t('approval.form.error.approvers_required')
    return
  }
  if (!props.dialogId.trim()) {
    errorMsg.value = t('approval.form.error.dialog_required')
    return
  }

  isSubmitting.value = true
  errorMsg.value = ''
  botIssueMsg.value = ''
  const traceId = `approval-ui-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
  if (import.meta.dev) {
    console.groupCollapsed(`[approval][ui][${traceId}] submit`)
    console.log('dialogId', props.dialogId)
    console.log('thresholdType', thresholdType.value)
    console.log('approverIds', approverIds.value)
    console.log('filesCount', files.value.length)
    console.groupEnd()
  }

  try {
    const created = await approval.create({
      comment: comment.value,
      approverIds: approverIds.value,
      thresholdType: thresholdType.value,
      dialogId: props.dialogId,
      files: files.value,
    })
    if (import.meta.dev) {
      console.groupCollapsed(`[approval][ui][${traceId}] created`)
      console.log('request_id', created.id)
      console.log('status', created.status)
      console.log('bot_message_id', created.bot_message_id ?? '')
      console.log('bot_message_ids', created.bot_message_ids ?? [])
      console.log('bot_dialog_id', created.bot_dialog_id ?? '')
      console.log('bot_dialog_ids', created.bot_dialog_ids ?? [])
    }
    if (created.bot_issue) {
      if (import.meta.dev) console.warn('bot_issue', created.bot_issue)
      // FE-P1-3: surface delivery problems to the initiator instead of
      // silently swallowing them. Request is created in storage; only
      // bot delivery to some/all approvers is degraded.
      botIssueMsg.value = t('approval.form.warning.bot_issue', { details: created.bot_issue })
    }
    if (!created.bot_message_id) {
      if (import.meta.dev) console.warn('[approval][ui] request created, but bot_message_id is empty')
      if (!botIssueMsg.value) {
        botIssueMsg.value = t('approval.form.warning.no_bot_message')
      }
    }
    clearFiles()
    emit('created')
  } catch (error: unknown) {
    const appError = (typeof error === 'object' && error !== null)
      ? error as { data?: { error?: string }, message?: string }
      : {}
    if (import.meta.dev) {
      console.groupCollapsed(`[approval][ui][${traceId}] submit-error`)
      console.error(error)
      console.groupEnd()
    }
    errorMsg.value = appError.data?.error ?? appError.message ?? t('approval.form.error.generic')
  } finally {
    isSubmitting.value = false
  }
}

onMounted(() => {
  // Загружаем пользователей в фоне (не блокируем UI). Ошибки уже обработаны
  // внутри loadAndCacheUsers и проброшены в usersLoadError для UI; здесь —
  // финальный safety-net на случай неотловленной ошибки.
  loadAndCacheUsers().catch(err => {
    if (import.meta.dev) console.error('Failed to load users on mount:', err)
  })
})
</script>

<template>
  <div class="space-y-3">
    <div>
      <label class="block text-xs font-medium text-b24-base-600 mb-0.5">
        {{ t('approval.form.comment') }} <span class="text-b24-red-500">*</span>
      </label>
      <B24Textarea
        v-model="comment"
        :placeholder="t('approval.form.comment_placeholder')"
        :rows="2"
      />
    </div>

    <div>
      <label class="block text-xs font-medium text-b24-base-600 mb-0.5">
        {{ t('approval.form.approvers') }} <span class="text-b24-red-500">*</span>
      </label>
      <div class="relative">
        <div v-if="isLoadingUsers" class="text-xs text-b24-base-400 mb-2">
          {{ t('approval.form.loading_users') }}
        </div>
        <B24Select
          v-model="approverIds"
          :items="userSelectOptions"
          value-key="value"
          label-key="label"
          multiple
          filterable
          :placeholder="t('approval.form.select_approvers_placeholder')"
          :disabled="allUsers.length === 0"
        />
        <p v-if="usersLoadError" class="text-xs text-b24-red-500 mt-1">{{ usersLoadError }}</p>
        <p v-else-if="allUsers.length === 0 && !isLoadingUsers" class="text-xs text-b24-base-400 mt-1">
          {{ t('approval.form.no_users_available') }}
        </p>
      </div>
    </div>

    <div>
      <label class="block text-xs font-medium text-b24-base-600 mb-0.5">
        {{ t('approval.form.threshold') }}
      </label>
      <B24Select
        v-model="thresholdType"
        :items="thresholdOptions"
        value-key="value"
        label-key="label"
      />
    </div>

    <div>
      <label class="block text-xs font-medium text-b24-base-600 mb-0.5">
        {{ t('approval.form.files') }}
      </label>
      <FileUploadArea
        :files="files"
        @add="addFiles"
        @remove="removeFile"
      />
    </div>

    <p v-if="errorMsg" class="text-sm text-b24-red-500">{{ errorMsg }}</p>
    <p
      v-if="botIssueMsg"
      class="text-xs text-b24-amber-700 bg-b24-amber-50 border border-b24-amber-200 rounded px-2 py-1.5"
    >
      {{ botIssueMsg }}
    </p>

    <div class="flex justify-end gap-2 pt-1">
      <B24Button
        :label="t('approval.action.cancel')"
        color="secondary"
        variant="ghost"
        size="sm"
        :disabled="isSubmitting"
        @click="emit('cancel')"
      />
      <B24Button
        :label="t('approval.action.create')"
        color="primary"
        size="sm"
        loading-auto
        :disabled="isSubmitting"
        @click="submit"
      />
    </div>
  </div>
</template>
