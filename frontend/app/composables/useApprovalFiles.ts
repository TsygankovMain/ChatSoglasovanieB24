export const useApprovalFiles = () => {
  const files = ref<File[]>([])
  const isDragging = ref(false)

  function addFiles(newFiles: FileList | File[]) {
    const list = Array.from(newFiles)
    for (const f of list) {
      if (!files.value.find(existing => existing.name === f.name && existing.size === f.size)) {
        files.value.push(f)
      }
    }
  }

  function removeFile(index: number) {
    files.value.splice(index, 1)
  }

  function clear() {
    files.value = []
  }

  function onDrop(event: DragEvent) {
    isDragging.value = false
    if (event.dataTransfer?.files) {
      addFiles(event.dataTransfer.files)
    }
  }

  function onDragOver() {
    isDragging.value = true
  }

  function onDragLeave() {
    isDragging.value = false
  }

  function formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return {
    files,
    isDragging,
    addFiles,
    removeFile,
    clear,
    onDrop,
    onDragOver,
    onDragLeave,
    formatSize,
  }
}
