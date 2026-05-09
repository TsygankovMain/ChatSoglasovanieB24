<script setup lang="ts">
import type { ApprovalRequest } from '~/stores/api'

const props = defineProps<{
  request: ApprovalRequest
  maxItems?: number
}>()

const { t, locale } = useI18n()

const maxItems = computed(() => props.maxItems ?? 5)

const sortedEvents = computed(() =>
  [...(props.request.events ?? [])]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, maxItems.value)
)

// Маппинг кода locale-а из i18n в BCP-47, который понимает Intl.DateTimeFormat.
// nuxt-i18n использует короткие коды ('br', 'sc', ...), а Intl ждёт 'pt-BR', 'zh-Hans' и т.п.
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

const formatDateTime = (raw: string) => {
  if (!raw) return '—'
  const date = new Date(raw)
  if (Number.isNaN(date.getTime())) return raw
  const bcp47 = I18N_TO_BCP47[locale.value] || locale.value
  return new Intl.DateTimeFormat(bcp47, {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

const typeLabel = (type: string) => {
  const key = `approval.event.type.${type}`
  // Если перевод не найден — t() возвращает сам ключ, fallback на 'unknown'
  const translated = t(key)
  return translated === key ? t('approval.event.type.unknown') : translated
}
</script>

<template>
  <div class="space-y-1.5">
    <p class="text-xs font-medium text-b24-base-500">{{ t('approval.event.log_title') }}</p>
    <div v-if="sortedEvents.length === 0" class="text-xs text-b24-base-400">
      {{ t('approval.event.empty') }}
    </div>
    <div v-else class="space-y-1">
      <div
        v-for="event in sortedEvents"
        :key="event.id"
        class="border border-b24-base-200 rounded px-2 py-1"
      >
        <div class="flex items-center justify-between gap-2">
          <p class="text-xs font-medium text-b24-base-700 truncate">
            {{ typeLabel(event.type) }}<span v-if="event.user_name">: {{ event.user_name }}</span>
          </p>
          <p class="text-[11px] text-b24-base-400 whitespace-nowrap">{{ formatDateTime(event.created_at) }}</p>
        </div>
        <p v-if="event.message" class="text-xs text-b24-base-500 mt-0.5 break-words">{{ event.message }}</p>
      </div>
    </div>
  </div>
</template>
