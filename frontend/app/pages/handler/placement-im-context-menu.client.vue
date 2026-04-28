<script setup lang="ts">
import type { B24Frame } from '@bitrix24/b24jssdk'
import { usePageStore } from '~/stores/page'

definePageMeta({ layout: false })

const { t, locales: localesI18n, setLocale } = useI18n()
const page = usePageStore()

const { $logger, initApp, processErrorGlobal } = useAppInit('ContextMenuPlacementPage')
const { $initializeB24Frame } = useNuxtApp()
let $b24: null | B24Frame = null

const isInit = ref(false)
const dialogId = ref('')
const messageId = ref('')
const prefillComment = ref('')

// ── Message text fetch ─────────────────────────────────────────────────────

/**
 * Fetches the text of a specific message using im.dialog.messages.get
 * (scope: im — available to any portal user with chat access).
 *
 * Strategy: request messages with LAST_ID = messageId+1 so the window
 * includes exactly the target message; filter by ID to find it.
 * Degrades gracefully — if anything fails the form opens without pre-fill.
 */
async function fetchMessageText(dId: string, mId: string): Promise<string> {
  const numericId = parseInt(mId, 10)
  if (!dId || !numericId) return ''

  try {
    const response = await $b24!.callMethod('im.dialog.messages.get', {
      DIALOG_ID: dId,
      LAST_ID: numericId + 1,
      LIMIT: 5,
    })

    type ImMessage = { id: number | string; text?: string }
    type ImResponse = { messages?: ImMessage[] }
    const data = response.getData() as ImResponse

    const found = (data.messages ?? []).find(
      m => String(m.id) === String(numericId)
    )
    const text = found?.text?.trim() ?? ''
    if (text) {
      $logger.info('ContextMenuPlacementPage: message text fetched, length=%s', text.length)
    }
    return text
  } catch (err) {
    // Non-critical — log at warn so it's visible in dev but doesn't block the form.
    $logger.warn('ContextMenuPlacementPage: failed to fetch message text', err)
    return ''
  }
}

// ── Lifecycle ──────────────────────────────────────────────────────────────

onMounted(async () => {
  try {
    $b24 = await $initializeB24Frame()
    await initApp($b24, localesI18n, setLocale)

    const opts = ($b24.placement?.options ?? {}) as Record<string, unknown>
    dialogId.value = String(opts.dialogId ?? opts.DIALOG_ID ?? '')
    messageId.value = String(opts.messageId ?? opts.MESSAGE_ID ?? '')

    page.title = t('page.context-menu.seo.title')
    await $b24.parent.setTitle(t('page.context-menu.seo.title'))

    // Fetch message text in parallel with title update (non-blocking init).
    prefillComment.value = await fetchMessageText(dialogId.value, messageId.value)

    isInit.value = true
  } catch (error) {
    processErrorGlobal(error)
  }
})

// ── Actions ────────────────────────────────────────────────────────────────

async function onCreated() {
  try {
    await $b24?.parent.closeApplication()
  } catch (error) {
    $logger.warn('closeApplication failed', error)
  }
}

async function onCancel() {
  try {
    await $b24?.parent.closeApplication()
  } catch (error) {
    $logger.warn('closeApplication (cancel) failed', error)
  }
}
</script>

<template>
  <NuxtLayout name="slider">
    <div v-if="isInit">
      <!-- Message attribution badge -->
      <p
        v-if="messageId"
        class="text-xs text-b24-base-400 px-4 pt-3 pb-1"
      >
        {{ t('page.context-menu.based_on_message', { id: messageId }) }}
      </p>

      <div class="px-4 pb-4" :class="messageId ? '' : 'pt-4'">
        <LazyApprovalCreateForm
          :dialog-id="dialogId"
          :prefill-comment="prefillComment"
          @created="onCreated"
          @cancel="onCancel"
        />
      </div>
    </div>

    <div v-else class="flex justify-center p-8">
      <B24Progress animation="carousel" />
    </div>
  </NuxtLayout>
</template>
