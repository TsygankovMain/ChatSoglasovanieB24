<script setup lang="ts">
import type { ApprovalRequest } from '~/stores/api'

const props = defineProps<{
  request: ApprovalRequest
}>()

const { t } = useI18n()

const votes = computed(() => {
  const raw = props.request.votes ?? []
  const byUser = new Map<string, typeof raw[number]>()
  for (const vote of raw) {
    byUser.set(vote.user_id, vote)
  }
  return Array.from(byUser.values())
})
const total = computed(() => props.request.approver_ids.length)
const approveCount = computed(() => votes.value.filter(v => v.decision === 'approve').length)
const rejectCount = computed(() => votes.value.filter(v => v.decision === 'reject').length)
const pendingCount = computed(() => total.value - votes.value.length)

const approvePercent = computed(() => total.value ? Math.round((approveCount.value / total.value) * 100) : 0)
const rejectPercent = computed(() => total.value ? Math.round((rejectCount.value / total.value) * 100) : 0)

const approvedNames = computed(() =>
  votes.value
    .filter(v => v.decision === 'approve')
    .map(v => v.user_name || props.request.approver_names?.[v.user_id] || v.user_id)
)

const rejectedNames = computed(() =>
  votes.value
    .filter(v => v.decision === 'reject')
    .map(v => v.user_name || props.request.approver_names?.[v.user_id] || v.user_id)
)

const pendingNames = computed(() => {
  const voted = new Set(votes.value.map(v => v.user_id))
  return props.request.approver_ids
    .filter(id => !voted.has(id))
    .map(id => props.request.approver_names?.[id] || id)
})
</script>

<template>
  <div class="space-y-1.5">
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
    <div class="text-xs text-b24-base-500 space-y-0.5">
      <p><span class="text-b24-green-600">✓</span> {{ approvedNames.length ? approvedNames.join(', ') : '—' }}</p>
      <p><span class="text-b24-red-600">✗</span> {{ rejectedNames.length ? rejectedNames.join(', ') : '—' }}</p>
      <p><span class="text-b24-base-500">…</span> {{ pendingNames.length ? pendingNames.join(', ') : '—' }}</p>
    </div>
  </div>
</template>
