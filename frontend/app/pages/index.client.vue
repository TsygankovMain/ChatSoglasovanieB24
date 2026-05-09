<script setup lang="ts">
import type { B24Frame } from '@bitrix24/b24jssdk'
import { onMounted } from 'vue'
import { useDashboard } from '@bitrix24/b24ui-nuxt/utils/dashboard'
import PlusLIcon from '@bitrix24/b24icons-vue/outline/PlusLIcon'

const { t, locales: localesI18n, setLocale } = useI18n()

useHead({ title: t('page.index.seo.title') })

const { $logger, initApp, processErrorGlobal } = useAppInit('IndexPage')
const { $initializeB24Frame } = useNuxtApp()
let $b24: null | B24Frame = null

const approval = useApproval()
const userStore = useUserStore()

const { contextId, isLoading: isLoadingState, load } = useDashboard({ isLoading: ref(false), load: () => {} })
const isLoading = computed({
  get: () => isLoadingState?.value === true,
  set: (value: boolean) => { load?.(value, contextId) },
})

const isInit = ref(false)
const activeTab = ref<'my' | 'incoming'>('my')
const showCreateForm = ref(false)
const dialogId = ref('')
const placementOptions = ref<Record<string, unknown>>({})
const isBackendUnavailable = ref(false)

const isContextMissing = computed(() => dialogId.value.trim().length === 0)
const isInChat = computed(() => !isContextMissing.value)
const shouldShowCreateForm = computed(() => isInChat.value || showCreateForm.value)
const isDev = import.meta.dev
const contextMeta = computed(() => ({
  dialogId: dialogId.value,
  placementOptions: placementOptions.value,
}))

const currentList = computed(() =>
  activeTab.value === 'my' ? approval.myRequests.value : approval.incomingRequests.value
)

async function fitWindow() {
  try {
    await $b24?.parent.fitWindow()
  } catch (error) {
    $logger.warn('fitWindow failed', error)
  }
}

async function loadTab() {
  if (activeTab.value === 'my') {
    await approval.list()
  } else {
    await approval.listIncoming()
  }
}

async function onCreated() {
  if (isInChat.value) {
    try {
      await $b24?.parent.closeApplication()
      return
    } catch (error) {
      $logger.warn('closeApplication failed', error)
    }
  }

  showCreateForm.value = false
  if (!isBackendUnavailable.value) {
    await approval.list()
    activeTab.value = 'my'
  }
  await fitWindow()
}

async function onCancel(id: string) {
  await approval.cancel(id)
}

function onCancelCreate() {
  if (!isInChat.value) {
    showCreateForm.value = false
  }
}

onMounted(async () => {
  try {
    isLoading.value = true
    $b24 = await $initializeB24Frame()
    await initApp($b24, localesI18n, setLocale)

    // Эти три вызова не зависят друг от друга — параллелим, чтобы
    // не делать 3 IPC последовательно (≈ -200..400 мс на холодный запуск).
    // setTitle/fitWindow — IPC к Bitrix24-родителю; placement.options — sync.
    const opts = $b24.placement?.options ?? {}
    placementOptions.value = opts
    dialogId.value = opts?.dialogId ?? opts?.DIALOG_ID ?? ''

    isInit.value = true

    // Грузим список параллельно с заголовком/подгонкой окна. Если backend
    // недоступен, ошибка вылетит из approval.list и мы её отметим — тогда
    // отдельный /api/health round-trip не нужен.
    const titleP = $b24.parent.setTitle(t('page.index.seo.title'))
                       .catch(error => $logger.warn('setTitle failed', error))
    const fitP = fitWindow()
    const dataP = (!isInChat.value)
      ? loadTab().catch(error => {
          isBackendUnavailable.value = true
          $logger.error('Initial list load failed — assuming backend unavailable', error)
        })
      : Promise.resolve()

    await Promise.all([titleP, fitP, dataP])
  } catch (error) {
    processErrorGlobal(error)
  } finally {
    isLoading.value = false
  }
})

watch(activeTab, async () => {
  if (isInChat.value || isBackendUnavailable.value) {
    return
  }
  await loadTab()
  await fitWindow()
})

watch(showCreateForm, async () => {
  await fitWindow()
})
</script>

<template>
  <div class="mx-auto w-full max-w-[1080px] px-3 py-4">
    <div v-if="isInit" class="space-y-4">
      <B24Card
        v-if="isContextMissing"
        variant="soft"
        class="border border-b24-red-200 bg-b24-red-50/60"
      >
        <div class="flex flex-col gap-2">
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <p class="text-sm font-semibold text-b24-red-700">
                {{ t('approval.context.missing_title') }}
              </p>
              <p class="text-xs text-b24-base-700 mt-1">
                {{ t('approval.context.missing_description') }}
              </p>
            </div>
            <span class="shrink-0 rounded-md border border-b24-red-200 bg-white px-2 py-1 text-[11px] font-semibold tracking-wide text-b24-red-600">
              IM_TEXTAREA
            </span>
          </div>

          <details
            v-if="isDev"
            class="rounded-lg border border-b24-base-200 bg-white px-2 py-1.5"
          >
            <summary class="cursor-pointer text-xs text-b24-base-500">Debug payload</summary>
            <ProsePre class="mt-2 !text-xs">
              {{ contextMeta }}
            </ProsePre>
          </details>
        </div>
      </B24Card>

      <B24Alert
        v-if="isBackendUnavailable"
        :title="t('approval.backend.unavailable_title')"
        :description="t('approval.backend.unavailable_description')"
        color="air-primary-alert"
        size="sm"
      />

      <B24Card
        v-if="!isInChat"
        variant="outline"
        class="border border-b24-base-200"
      >
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div class="flex gap-2">
            <B24Button
              :label="t('approval.tab.my')"
              :color="activeTab === 'my' ? 'primary' : 'secondary'"
              variant="ghost"
              @click="activeTab = 'my'"
            />
            <B24Button
              :label="t('approval.tab.incoming')"
              :color="activeTab === 'incoming' ? 'primary' : 'secondary'"
              variant="ghost"
              @click="activeTab = 'incoming'"
            />
          </div>
          <B24Button
            v-if="!showCreateForm"
            :icon="PlusLIcon"
            :label="t('approval.action.create')"
            color="air-primary"
            :disabled="isContextMissing"
            @click="showCreateForm = true"
          />
        </div>
      </B24Card>

      <!-- LazyApprovalCreateForm: компонент с тяжёлыми зависимостями
           (B24Select multi-filter, B24Textarea, callListMethod user.get).
           Без Lazy он попадает в основной чанк и замедляет первый рендер. -->
      <B24Card
        v-if="shouldShowCreateForm"
        variant="outline"
        class="border border-b24-base-200 shadow-xs"
      >
        <template v-if="!isInChat" #header>
          <ProseH2 class="mb-0">{{ t('approval.form.title') }}</ProseH2>
        </template>
        <LazyApprovalCreateForm
          :dialog-id="dialogId"
          @created="onCreated"
          @cancel="onCancelCreate"
        />
      </B24Card>

      <div
        v-if="!isInChat && !isBackendUnavailable && approval.isLoading.value"
        class="flex justify-center py-10"
      >
        <B24Progress animation="carousel" />
      </div>

      <B24Card
        v-else-if="!isInChat && !isBackendUnavailable && currentList.length === 0"
        variant="soft"
        class="border border-b24-base-200"
      >
        <div class="py-8 text-center text-sm text-b24-base-500">
          {{ t('approval.empty') }}
        </div>
      </B24Card>

      <div
        v-else-if="!isInChat && !isBackendUnavailable"
        class="grid grid-cols-1 gap-3"
      >
        <ApprovalRequestCard
          v-for="req in currentList"
          :key="req.id"
          :request="req"
          :current-user-id="String(userStore.id)"
          @click="approval.getById($event)"
          @cancel="onCancel"
        />
      </div>
    </div>
  </div>
</template>
