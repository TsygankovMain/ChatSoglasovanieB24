<script setup lang="ts">
import type { ApprovalRequest } from '~/stores/api'

const props = defineProps<{
  request: ApprovalRequest
  currentUserId?: string
}>()

const emit = defineEmits<{
  (e: 'click', id: string): void
  (e: 'cancel', id: string): void
}>()

const { t } = useI18n()

const isInitiator = computed(() => props.currentUserId === props.request.initiator_id)
const isTerminal = computed(() => ['approved', 'rejected', 'cancelled'].includes(props.request.status))

const formattedDate = computed(() => {
  return new Date(props.request.created_at).toLocaleDateString('ru-RU', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
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
      </div>
      <ApprovalStatusBadge :status="request.status" />
    </div>

    <div class="mt-3">
      <ApprovalVoteStatus :request="request" />
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
