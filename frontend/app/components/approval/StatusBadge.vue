<script setup lang="ts">
import type { ApprovalRequest } from '~/stores/api'

const props = defineProps<{
  status: ApprovalRequest['status']
}>()

const { t } = useI18n()

const colorMap: Record<ApprovalRequest['status'], string> = {
  collecting: 'text-b24-orange-400 bg-b24-orange-50',
  approved: 'text-b24-green-500 bg-b24-green-50',
  rejected: 'text-b24-red-500 bg-b24-red-50',
  cancelled: 'text-b24-base-400 bg-b24-base-100',
}
</script>

<template>
  <span
    class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
    :class="colorMap[status]"
  >
    {{ t(`approval.status.${status}`) }}
  </span>
</template>
