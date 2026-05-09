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
const quotedPreview = computed(() => {
  const text = prefillComment.value.trim()
  if (!text) {
    return ''
  }
  return text.length > 220 ? `${text.slice(0, 220)}…` : text
})

// ── Message text fetch ─────────────────────────────────────────────────────

/**
 * Fetches the text of a specific message using im.dialog.messages.get
 * (scope: im — available to any portal user with chat access).
 *
 * Uses LAST_ID = messageId+1 so the window includes the target message;
 * filters by ID to find it. getData() may return either {messages:[...]}
 * or wrap the result — handled defensively.
 * Degrades gracefully — if anything fails the form opens without pre-fill.
 */
async function fetchMessageText(dId: string, mId: string): Promise<string> {
  const numericId = parseInt(mId, 10)
  if (!dId || !numericId) {
    $logger.warn('ContextMenuPlacementPage: fetchMessageText skipped — dialogId=%s messageId=%s', dId, mId)
    return ''
  }

  try {
    const response = await $b24!.callMethod('im.dialog.messages.get', {
      DIALOG_ID: dId,
      LAST_ID: numericId + 1,
      LIMIT: 5,
    })

    type ImMessage = { id: number | string; text?: string }
    // getData() may return messages at top level or nested under result
    const raw = response.getData() as Record<string, unknown>
    $logger.info('ContextMenuPlacementPage: im.dialog.messages.get raw keys=%o', Object.keys(raw ?? {}))

    const messages: ImMessage[] =
      (raw?.messages as ImMessage[] | undefined) ??
      ((raw?.result as Record<string, unknown> | undefined)?.messages as ImMessage[] | undefined) ??
      []

    const found = messages.find(m => String(m.id) === String(numericId))
    const text = found?.text?.trim() ?? ''
    if (text) {
      $logger.info('ContextMenuPlacementPage: pre-fill text length=%s', text.length)
    } else {
      $logger.warn(
        'ContextMenuPlacementPage: message id=%s not found among %s messages',
        numericId, messages.length,
      )
    }
    return text
  } catch (err) {
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
    // Log full options so we can verify which keys Bitrix24 actually sends.
    $logger.info('ContextMenuPlacementPage: placement options=%o', opts)

    dialogId.value = String(opts.dialogId ?? opts.DIALOG_ID ?? '')
    messageId.value = String(opts.messageId ?? opts.MESSAGE_ID ?? '')
    $logger.info('ContextMenuPlacementPage: dialogId=%s messageId=%s', dialogId.value, messageId.value)

    page.title = t('page.context-menu.seo.title')
    await $b24.parent.setTitle(t('page.context-menu.seo.title'))

    prefillComment.value = await fetchMessageText(dialogId.value, messageId.value)

    isInit.value = true

    // Resize the frame to look like a compact popup-style window.
    await nextTick()
    try {
      await $b24.parent.resizeWindowAuto(680, 560)
    } catch {
      try {
        await $b24.parent.fitWindow()
      } catch {
        // sizing is not critical — ignore if unavailable.
      }
    }
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
  <!-- IM_CONTEXT_MENU always opens inside a Bitrix container.
       This centered card gives a popup feel instead of a heavy full-panel form. -->
  <div class="min-h-screen bg-gradient-to-b from-b24-base-50 to-white p-3 sm:p-4">
    <div v-if="isInit" class="mx-auto w-full max-w-[680px]">
      <B24Card
        variant="outline"
        class="border border-b24-base-200 shadow-sm"
      >
        <template #header>
          <div class="flex items-center justify-between gap-3">
            <div>
              <ProseH3 class="mb-0 text-base font-semibold">
                {{ t('page.context-menu.seo.title') }}
              </ProseH3>
              <p
                v-if="messageId"
                class="mt-1 text-xs text-b24-base-500"
              >
                {{ t('page.context-menu.based_on_message', { id: messageId }) }}
              </p>
            </div>
            <B24Button
              size="xs"
              variant="ghost"
              color="secondary"
              :label="t('approval.action.cancel')"
              @click="onCancel"
            />
          </div>
        </template>

        <div class="space-y-3">
          <div
            v-if="quotedPreview"
            class="rounded-lg border border-b24-base-200 bg-b24-base-50 px-3 py-2"
          >
            <p class="text-[11px] uppercase tracking-wide text-b24-base-400">
              {{ t('page.context-menu.based_on_message', { id: messageId }) }}
            </p>
            <p class="mt-1 text-xs leading-5 text-b24-base-700">
              {{ quotedPreview }}
            </p>
          </div>

          <LazyApprovalCreateForm
            :dialog-id="dialogId"
            :prefill-comment="prefillComment"
            compact
            @created="onCreated"
            @cancel="onCancel"
          />
        </div>
      </B24Card>
    </div>

    <div v-else class="flex min-h-[200px] items-center justify-center">
      <B24Progress animation="carousel" />
    </div>
  </div>
</template>
