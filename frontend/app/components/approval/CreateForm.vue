<script setup lang="ts">
import type { B24Frame } from '@bitrix24/b24jssdk'

const props = defineProps<{
  dialogId: string
}>()

const emit = defineEmits<{
  (e: 'created' | 'cancel'): void
}>()

const { t } = useI18n()
const { $initializeB24Frame } = useNuxtApp()
const approval = useApproval()
const { files, addFiles, removeFile, clear: clearFiles } = useApprovalFiles()

type PortalUser = {
  id: string
  fio: string
  workPosition: string
}

type B24SearchUser = {
  id?: string | number
  name?: string
  first_name?: string
  last_name?: string
  work_position?: string
}

type B24SearchPayload = {
  result?: B24SearchUser[]
}

let $b24: B24Frame | null = null
let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null
let searchSeq = 0

const comment = ref('')
const approverIds = ref<string[]>([])
const thresholdType = ref<'all' | 'majority'>('all')
const isSubmitting = ref(false)
const errorMsg = ref('')
const approverInputValue = ref('')
const isApproverSearchLoading = ref(false)
const approverSearchError = ref('')
const approverOptions = ref<PortalUser[]>([])
const approverById = ref(new Map<string, PortalUser>())

const thresholdOptions = computed(() => [
  { value: 'all', label: t('approval.threshold.all') },
  { value: 'majority', label: t('approval.threshold.majority') },
])

function normalizeUser(user: B24SearchUser): PortalUser | null {
  // Пропускаем ботов и неактивных пользователей
  if (user.name?.includes('[bot]') || user.name?.includes('[BOT]')) {
    return null
  }

  const idRaw = user.id
  const id = String(idRaw ?? '').trim()
  if (!id) {
    return null
  }

  let fio = String(user.name ?? '').trim()
  if (!fio) {
    const firstName = String(user.first_name ?? '').trim()
    const lastName = String(user.last_name ?? '').trim()
    fio = `${firstName} ${lastName}`.trim()
  }
  fio = fio || id

  return {
    id,
    fio,
    workPosition: String(user.work_position ?? '').trim(),
  }
}

async function ensureB24Frame(): Promise<B24Frame> {
  if ($b24) {
    return $b24
  }
  $b24 = await $initializeB24Frame()
  return $b24
}

function addApprover(user: PortalUser) {
  if (!approverIds.value.includes(user.id)) {
    approverIds.value.push(user.id)
    approverById.value.set(user.id, user)
  }
  approverInputValue.value = ''
  approverOptions.value = []
  approverSearchError.value = ''
}

function addFirstApprover() {
  const first = approverOptions.value[0]
  if (first) {
    addApprover(first)
  }
}

function removeApprover(id: string) {
  approverIds.value = approverIds.value.filter(a => a !== id)
}

async function openUserSelectionDialog() {
  try {
    // Проверяем, доступен ли глобальный BX24 объект
    const globalBX24 = (window as unknown as { BX24?: { selectUsers?: (callback: (users: Array<{ id: number | string; name: string }>) => void) => void } }).BX24
    if (globalBX24?.selectUsers) {
      globalBX24.selectUsers((users: Array<{ id: number | string; name: string }>) => {
        if (Array.isArray(users)) {
          users.forEach((user) => {
            const normalizedUser: PortalUser = {
              id: String(user.id),
              fio: user.name,
              workPosition: '',
            }
            addApprover(normalizedUser)
          })
        }
      })
    } else {
      console.warn('BX24.selectUsers not available, using search interface')
    }
  } catch (error) {
    console.error('Error opening user selection dialog:', error)
  }
}

function addApprover(user: PortalUser) {
  if (!approverIds.value.includes(user.id)) {
    approverIds.value.push(user.id)
    approverById.value.set(user.id, user)
  }
  approverInputValue.value = ''
  approverOptions.value = []
  approverSearchError.value = ''
}
  const term = query.trim()
  if (term.length < 3) {
    approverOptions.value = []
    approverSearchError.value = ''
    isApproverSearchLoading.value = false
    return
  }

  const seq = ++searchSeq
  isApproverSearchLoading.value = true
  approverSearchError.value = ''

  try {
    const b24 = await ensureB24Frame()
    const response = await b24.callMethod('user.search', {
      FIND: term,
      SORT: 'ID',
      ORDER: 'asc',
      start: 0,
    })

    const payloadRaw = (typeof response === 'object' && response !== null && 'getData' in response && typeof (response as { getData?: () => unknown }).getData === 'function')
      ? (response as { getData: () => unknown }).getData()
      : response
    const payload = (typeof payloadRaw === 'object' && payloadRaw !== null)
      ? payloadRaw as B24SearchPayload
      : {}
    // user.search может возвращать результаты напрямую как массив или в поле result
    const usersRaw = Array.isArray(payload.result)
      ? payload.result
      : Array.isArray(payload as unknown[])
        ? payload as unknown[]
        : []

    console.debug('User search response:', { response, payload, usersRaw, term })

    if (seq !== searchSeq) {
      return
    }

    const users = usersRaw
      .map(normalizeUser)
      .filter((user): user is PortalUser => user !== null)

    users.forEach(user => approverById.value.set(user.id, user))
    approverOptions.value = users.filter(user => !approverIds.value.includes(user.id))
  } catch (error) {
    if (seq !== searchSeq) {
      return
    }
    approverOptions.value = []
    approverSearchError.value = t('approval.form.error.user_search_failed')
    console.error('approver search failed', error)
  } finally {
    if (seq === searchSeq) {
      isApproverSearchLoading.value = false
    }
  }
}

watch(approverInputValue, (value: string) => {
  if (searchDebounceTimer) {
    clearTimeout(searchDebounceTimer)
  }
  searchDebounceTimer = setTimeout(() => {
    searchApprovers(value)
  }, 250)
})

onUnmounted(() => {
  if (searchDebounceTimer) {
    clearTimeout(searchDebounceTimer)
  }
})

async function submit() {
  errorMsg.value = ''
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
  try {
    await approval.create({
      comment: comment.value,
      approverIds: approverIds.value,
      thresholdType: thresholdType.value,
      dialogId: props.dialogId,
      files: files.value,
    })
    clearFiles()
    emit('created')
  } catch (error: unknown) {
    const appError = (typeof error === 'object' && error !== null)
      ? error as { data?: { error?: string }, message?: string }
      : {}
    errorMsg.value = appError.data?.error ?? appError.message ?? t('approval.form.error.generic')
  } finally {
    isSubmitting.value = false
  }
}
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
      <div class="space-y-1">
        <div class="flex gap-2">
          <B24Input
            v-model="approverInputValue"
            :placeholder="t('approval.form.approver_id_placeholder')"
            class="flex-1"
            @keydown.enter.prevent="addFirstApprover"
          />
          <B24Button
            size="sm"
            color="secondary"
            variant="outline"
            label="Выбрать"
            @click="openUserSelectionDialog"
          />
        </div>
        <div
          v-if="approverOptions.length > 0"
          class="relative z-10 mt-1 w-full max-h-40 overflow-auto border border-b24-base-200 rounded bg-white"
        >
          <button
            v-for="user in approverOptions"
            :key="user.id"
            type="button"
            class="w-full text-left px-2 py-1.5 hover:bg-b24-base-50"
            @click="addApprover(user)"
          >
            <div class="text-xs font-medium text-b24-base-700 truncate">{{ user.fio }}</div>
            <div v-if="user.workPosition" class="text-xs text-b24-base-400 truncate">{{ user.workPosition }}</div>
          </button>
        </div>
      </div>
      <p v-if="isApproverSearchLoading" class="text-xs text-b24-base-400 mt-1">{{ t('approval.form.approver_search_loading') }}</p>
      <p v-else-if="approverInputValue.trim().length >= 3 && approverOptions.length === 0 && !approverSearchError" class="text-xs text-b24-base-400 mt-1">
        {{ t('approval.form.approver_search_no_results') }}
      </p>
      <p v-if="approverSearchError" class="text-xs text-b24-red-500 mt-1">{{ approverSearchError }}</p>
      <p class="text-xs text-b24-base-400 mt-1">{{ t('approval.form.approver_search_hint') }}</p>
      <div v-if="approverIds.length > 0" class="flex flex-wrap gap-1 mt-1.5">
        <span
          v-for="id in approverIds"
          :key="id"
          class="inline-flex items-center gap-1 text-xs bg-b24-base-100 rounded px-2 py-0.5"
        >
          {{ approverById.get(id)?.fio ?? id }}
          <button type="button" class="text-b24-base-400 hover:text-b24-red-500" @click="removeApprover(id)">×</button>
        </span>
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
