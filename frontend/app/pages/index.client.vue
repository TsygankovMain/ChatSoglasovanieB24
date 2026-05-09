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
  <div class="flex flex-col gap-4 p-4">
    <div v-if="isInit">
      <div v-if="!isInChat" class="flex items-center justify-between mb-4">
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

      <B24Alert
        v-if="isBackendUnavailable"
        :title="t('approval.backend.unavailable_title')"
        :description="t('approval.backend.unavailable_description')"
        color="air-primary-alert"
        size="sm"
      />

      <B24Alert
        v-if="isContextMissing"
        :title="t('approval.context.missing_title')"
        :description="t('approval.context.missing_description')"
        color="air-primary-alert"
        size="sm"
      />

      <ProsePre v-if="isContextMissing" class="mt-2">
        {{ { dialogId, placementOptions } }}
      </ProsePre>

      <!-- LazyApprovalCreateForm: компонент с тяжёлыми зависимостями
           (B24Select multi-filter, B24Textarea, callListMethod user.get).
           Без Lazy он попадает в основной чанк и замедляет первый рендер. -->
      <B24Card v-if="shouldShowCreateForm" :class="isInChat ? 'mb-2' : 'mb-4'">
        <template v-if="!isInChat" #header>
          <ProseH2>{{ t('approval.form.title') }}</ProseH2>
        </template>
        <LazyApprovalCreateForm
          :dialog-id="dialogId"
          @created="onCreated"
          @cancel="onCancelCreate"
        />
      </B24Card>

      <div v-if="!isInChat && !isBackendUnavailable && approval.isLoading.value" class="flex justify-center py-8">
        <B24Progress animation="carousel" />
      </div>

      <div v-else-if="!isInChat && !isBackendUnavailable && currentList.length === 0" class="text-center py-8 text-b24-base-400">
        {{ t('approval.empty') }}
      </div>

      <div v-else-if="!isInChat && !isBackendUnavailable" class="space-y-3">
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
