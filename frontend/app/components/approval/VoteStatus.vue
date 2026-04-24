<script setup lang="ts">
import type { ApprovalRequest } from '~/stores/api'

const props = defineProps<{
  request: ApprovalRequest
}>()

const { t } = useI18n()

const votes = computed(() => props.request.votes ?? [])
const total = computed(() => props.request.approver_ids.length)
const approveCount = computed(() => votes.value.filter(v => v.decision === 'approve').length)
const rejectCount = computed(() => votes.value.filter(v => v.decision === 'reject').length)
const pendingCount = computed(() => total.value - votes.value.length)

const approvePercent = computed(() => total.value ? Math.round((approveCount.value / total.value) * 100) : 0)
const rejectPercent = computed(() => total.value ? Math.round((rejectCount.value / total.value) * 100) : 0)
</script>

<template>
  <div class="space-y-1">
    <div class="flex items-center justify-between text-xs text-b24-base-400">
      <span>{{ t('approval.vote.approve') }}: {{ approveCount }}</span>
      <span>{{ t('approval.vote.reject') }}: {{ rejectCount }}</span>
      <span>{{ t('approval.vote.pending') }}: {{ pendingCount }}</span>
    </div>
    <div class="flex h-1.5 rounded-full overflow-hidden bg-b24-base-100">
      <div
        v-if="approveCount > 0"
        class="bg-b24-green-500 transition-all"
        :style="{ width: `${approvePercent}%` }"
      />
      <div
        v-if="rejectCount > 0"
        class="bg-b24-red-500 transition-all"
        :style="{ width: `${rejectPercent}%` }"
      />
    </div>
  </div>
</template>
