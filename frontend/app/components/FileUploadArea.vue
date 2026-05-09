<script setup lang="ts">
import Attach2Icon from '@bitrix24/b24icons-vue/main/Attach2Icon'
import Cross20Icon from '@bitrix24/b24icons-vue/actions/Cross20Icon'

const props = defineProps<{
  files: File[]
}>()

const emit = defineEmits<{
  (e: 'add', files: FileList): void
  (e: 'remove', index: number): void
}>()

const { t } = useI18n()
const { isDragging, onDrop, onDragOver, onDragLeave, formatSize } = useApprovalFiles()

const inputRef = ref<HTMLInputElement | null>(null)

function onInputChange(event: Event) {
  const target = event.target as HTMLInputElement
  if (target.files) emit('add', target.files)
  if (inputRef.value) inputRef.value.value = ''
}

function handleDrop(event: DragEvent) {
  onDrop(event)
  if (event.dataTransfer?.files) emit('add', event.dataTransfer.files)
}
</script>

<template>
  <div class="space-y-2">
    <div
      class="border-2 border-dashed rounded-lg p-4 text-center transition-colors cursor-pointer"
      :class="isDragging ? 'border-b24-blue-500 bg-b24-blue-50' : 'border-b24-base-200 hover:border-b24-base-300'"
      @dragover.prevent="onDragOver"
      @dragleave="onDragLeave"
      @drop.prevent="handleDrop"
      @click="inputRef?.click()"
    >
      <Attach2Icon class="mx-auto h-6 w-6 text-b24-base-300 mb-1" />
      <p class="text-sm text-b24-base-400">{{ t('approval.form.files_hint') }}</p>
      <input ref="inputRef" type="file" multiple class="hidden" @change="onInputChange" />
    </div>

    <div v-if="files.length > 0" class="space-y-1">
      <div
        v-for="(file, idx) in files"
        :key="idx"
        class="flex items-center justify-between text-sm bg-b24-base-50 rounded px-3 py-1.5"
      >
        <span class="truncate flex-1">{{ file.name }}</span>
        <span class="text-xs text-b24-base-400 ml-2">{{ formatSize(file.size) }}</span>
        <B24Button
          class="ml-2"
          variant="ghost"
          color="text"
          size="xs"
          :icon="Cross20Icon"
          square
          :aria-label="t('approval.form.remove_file')"
          @click="emit('remove', idx)"
        />
      </div>
    </div>
  </div>
</template>
