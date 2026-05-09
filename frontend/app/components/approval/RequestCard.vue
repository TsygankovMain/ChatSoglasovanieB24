<script setup lang="ts">
import type { ApprovalRequest } from '~/stores/api'
import Attach2Icon from '@bitrix24/b24icons-vue/main/Attach2Icon'

const props = defineProps<{
  request: ApprovalRequest
  currentUserId?: string
}>()

const emit = defineEmits<{
  (e: 'click' | 'cancel', id: string): void
}>()

const { t, locale } = useI18n()

/** Resolved file list: prefer `files` (has URLs), fall back to `file_names` (names only). */
const fileList = computed(() => {
  if (props.request.files && props.request.files.length > 0) {
    return props.request.files
  }
  if (props.request.file_names && props.request.file_names.length > 0) {
    return props.request.file_names.map(n => ({ id: '', name: n, url: '' }))
  }
  return []
})

const isInitiator = computed(() => props.currentUserId === props.request.initiator_id)
const isTerminal = computed(() => ['approved', 'rejected', 'cancelled'].includes(props.request.status))

// См. EventLog.vue — те же мапы кодов локалей в BCP-47 для Intl.DateTimeFormat.
const I18N_TO_BCP47: Record<string, string> = {
  br: 'pt-BR',
  sc: 'zh-Hans',
  tc: 'zh-Hant',
  la: 'es',
  ua: 'uk',
  kz: 'kk',
  vn: 'vi',
  ms: 'ms',
}

const formattedDate = computed(() => {
  const bcp47 = I18N_TO_BCP47[locale.value] || locale.value
  return new Intl.DateTimeFormat(bcp47, {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  }).format(new Date(props.request.created_at))
})

const approverNamesText = computed(() => {
  const names = props.request.approver_ids.map(id => props.request.approver_names?.[id] || id)
  return names.join(', ')
})

const eventCount = computed(() => props.request.events?.length ?? 0)

type B24Window = Window & {
  BX24?: {
    openPath?: (path: string, callback?: (result: unknown) => void) => void
  }
}

function toBitrixPath(rawUrl: string): string {
  const value = String(rawUrl || '').trim()
  if (!value) {
    return ''
  }
  if (value.startsWith('/')) {
    return value
  }
  try {
    const parsed = new URL(value)
    return `${parsed.pathname}${parsed.search}${parsed.hash}`
  } catch {
    return ''
  }
}

function openFilePreview(rawUrl: string) {
  const url = String(rawUrl || '').trim()
  if (!url || typeof window === 'undefined') {
    return
  }

  const path = toBitrixPath(url)
  const bx24 = (window as B24Window).BX24
  if (path && bx24?.openPath) {
    bx24.openPath(path)
    return
  }

  window.open(url, '_blank', 'noopener,noreferrer')
}
</script>

<template>
  <B24Card
    variant="outline"
    class="cursor-pointer border border-b24-base-200 bg-white/90 hover:shadow-sm transition-shadow"
    @click="emit('click', request.id)"
  >
    <div class="flex items-start justify-between gap-3">
      <div class="min-w-0 flex-1">
        <p class="text-sm font-semibold leading-5 text-b24-base-800 break-words">{{ request.comment }}</p>
        <div class="mt-1 flex flex-wrap items-center gap-2">
          <span class="inline-flex rounded-md border border-b24-base-200 bg-b24-base-50 px-2 py-0.5 text-[11px] text-b24-base-500">
            {{ formattedDate }}
          </span>
          <span class="inline-flex rounded-md border border-b24-base-200 bg-white px-2 py-0.5 text-[11px] text-b24-base-500">
            {{ t('approval.card.initiator') }}: {{ request.initiator_name || request.initiator_id }}
          </span>
        </div>
        <p class="text-xs text-b24-base-500 mt-2 break-words">
          {{ t('approval.card.approvers') }}: {{ approverNamesText }}
        </p>
      </div>
      <ApprovalStatusBadge :status="request.status" />
    </div>

    <!-- Attached files -->
    <div v-if="fileList.length > 0" class="mt-2 flex flex-wrap gap-1">
      <template v-for="(file, idx) in fileList" :key="idx">
        <button
          v-if="file.url"
          type="button"
          class="inline-flex items-center gap-1 text-xs text-b24-blue-500 hover:text-b24-blue-700 bg-b24-base-50 rounded px-2 py-0.5 truncate max-w-[180px]"
          :title="file.name"
          @click.stop="openFilePreview(file.url)"
        >
          <Attach2Icon class="h-3 w-3 flex-shrink-0" />
          <span class="truncate">{{ file.name }}</span>
        </button>
        <span
          v-else
          class="inline-flex items-center gap-1 text-xs text-b24-base-500 bg-b24-base-50 rounded px-2 py-0.5 truncate max-w-[180px]"
          :title="file.name"
        >
          <Attach2Icon class="h-3 w-3 flex-shrink-0" />
          <span class="truncate">{{ file.name }}</span>
        </span>
      </template>
    </div>

    <div class="mt-3">
      <ApprovalVoteStatus :request="request" />
    </div>

    <details class="mt-3 rounded-lg border border-b24-base-200 bg-b24-base-50/50 px-3 py-2" @click.stop>
      <summary class="cursor-pointer text-xs font-medium text-b24-base-600">
        {{ t('approval.event.log_title') }} <span class="text-b24-base-400">({{ eventCount }})</span>
      </summary>
      <div class="mt-2">
        <ApprovalEventLog :request="request" :max-items="6" />
      </div>
    </details>

    <div v-if="isInitiator && !isTerminal" class="mt-3 flex justify-end">
      <B24Button
        size="xs"
        color="danger"
        variant="ghost"
        :label="t('approval.action.cancel')"
        @click.stop="emit('cancel', request.id)"
      />
    </div>
  </B24Card>
</template>
