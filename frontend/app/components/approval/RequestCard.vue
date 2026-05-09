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
</script>

<template>
  <B24Card
    variant="outline"
    class="cursor-pointer hover:shadow-sm transition-shadow"
    @click="emit('click', request.id)"
  >
    <div class="flex items-start justify-between gap-2">
      <div class="flex-1 min-w-0">
        <p class="text-sm font-medium truncate">{{ request.comment }}</p>
        <p class="text-xs text-b24-base-400 mt-0.5">{{ formattedDate }}</p>
        <p class="text-xs text-b24-base-500 mt-1 truncate">
          {{ t('approval.card.initiator') }}: {{ request.initiator_name || request.initiator_id }}
        </p>
        <p class="text-xs text-b24-base-500 mt-0.5 truncate">
          {{ t('approval.card.approvers') }}: {{ approverNamesText }}
        </p>
      </div>
      <ApprovalStatusBadge :status="request.status" />
    </div>

    <!-- Attached files -->
    <div v-if="fileList.length > 0" class="mt-2 flex flex-wrap gap-1">
      <template v-for="(file, idx) in fileList" :key="idx">
        <a
          v-if="file.url"
          :href="file.url"
          target="_blank"
          rel="noopener noreferrer"
          class="inline-flex items-center gap-1 text-xs text-b24-blue-500 hover:text-b24-blue-700 bg-b24-base-50 rounded px-2 py-0.5 truncate max-w-[180px]"
          :title="file.name"
          @click.stop
        >
          <Attach2Icon class="h-3 w-3 flex-shrink-0" />
          <span class="truncate">{{ file.name }}</span>
        </a>
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

    <div class="mt-3">
      <ApprovalEventLog :request="request" :max-items="3" />
    </div>

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
