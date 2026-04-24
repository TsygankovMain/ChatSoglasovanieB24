<script setup lang="ts">
import type { B24Frame } from '@bitrix24/b24jssdk'
import { ref, onMounted, onUnmounted } from 'vue'
import { useDashboard } from '@bitrix24/b24ui-nuxt/utils/dashboard'
import PlusLIcon from '@bitrix24/b24icons-vue/outline/PlusLIcon'

definePageMeta({ layout: 'placement' })

const { t, locales: localesI18n, setLocale } = useI18n()

const { $logger, initApp, b24Helper, destroyB24Helper, processErrorGlobal } = useAppInit('crm_deal_detail_tab')
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
const showCreateForm = ref(false)
const dialogId = ref('')
const activeTab = ref<'my' | 'incoming'>('my')

const currentList = computed(() =>
  activeTab.value === 'my' ? approval.myRequests.value : approval.incomingRequests.value
)

async function loadTab() {
  if (activeTab.value === 'my') {
    await approval.list()
  } else {
    await approval.listIncoming()
  }
}

async function onCreated() {
  showCreateForm.value = false
  await approval.list()
  activeTab.value = 'my'
  await $b24?.parent.fitWindow()
}

async function onCancel(id: string) {
  await approval.cancel(id)
}

onMounted(async () => {
  try {
    isLoading.value = true
    $b24 = await $initializeB24Frame()
    await initApp($b24, localesI18n, setLocale)

    await $b24?.parent.fitWindow()

    const opts = $b24?.placement?.options ?? {}
    dialogId.value = opts?.dialogId ?? opts?.DIALOG_ID ?? ''

    isInit.value = true
    await loadTab()
  } catch (error) {
    processErrorGlobal(error, { homePageIsHide: true, isShowClearError: true })
  } finally {
    isLoading.value = false
  }
})

onUnmounted(() => {
  if (b24Helper.value) destroyB24Helper()
})

watch(activeTab, async () => {
  await loadTab()
  await $b24?.parent.fitWindow()
})
</script>

<template>
  <div>
    <div v-if="isInit">
      <div class="flex items-center justify-between gap-3 mb-3">
        <div class="flex gap-1">
          <B24Button
            size="sm"
            :label="t('approval.tab.my')"
            :color="activeTab === 'my' ? 'primary' : 'secondary'"
            variant="ghost"
            @click="activeTab = 'my'"
          />
          <B24Button
            size="sm"
            :label="t('approval.tab.incoming')"
            :color="activeTab === 'incoming' ? 'primary' : 'secondary'"
            variant="ghost"
            @click="activeTab = 'incoming'"
          />
        </div>
        <B24Button
          v-if="!showCreateForm"
          size="sm"
          color="air-primary"
          :icon="PlusLIcon"
          :label="t('approval.action.create')"
          loading-auto
          @click="showCreateForm = true"
        />
      </div>

      <B24Card v-if="showCreateForm" variant="outline" class="mb-3">
        <template #header>
          <ProseH2>{{ t('approval.form.title') }}</ProseH2>
        </template>
        <ApprovalCreateForm
          :dialog-id="dialogId"
          @created="onCreated"
          @cancel="showCreateForm = false"
        />
      </B24Card>

      <div v-if="approval.isLoading.value" class="flex justify-center py-6">
        <B24Progress animation="carousel" />
      </div>

      <div v-else-if="currentList.length === 0" class="text-center py-6 text-b24-base-400 text-sm">
        {{ t('approval.empty') }}
      </div>

      <div v-else class="space-y-2">
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
