import type { ApprovalRequest } from './api'

export const useApprovalsStore = defineStore('approvals', () => {
  const myRequests = ref<ApprovalRequest[]>([])
  const incomingRequests = ref<ApprovalRequest[]>([])
  const currentRequest = ref<ApprovalRequest | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  const api = useApiStore()

  const getErrorMessage = (errorValue: unknown, fallback: string): string => {
    if (typeof errorValue === 'object' && errorValue !== null && 'message' in errorValue) {
      const message = (errorValue as { message?: unknown }).message
      if (typeof message === 'string' && message.length > 0) {
        return message
      }
    }
    return fallback
  }

  async function fetchMyRequests() {
    isLoading.value = true
    error.value = null
    try {
      const res = await api.approvalList('initiator')
      myRequests.value = res.items
    } catch (e: unknown) {
      error.value = getErrorMessage(e, 'Ошибка загрузки')
    } finally {
      isLoading.value = false
    }
  }

  async function fetchIncomingRequests() {
    isLoading.value = true
    error.value = null
    try {
      const res = await api.approvalList('approver')
      incomingRequests.value = res.items
    } catch (e: unknown) {
      error.value = getErrorMessage(e, 'Ошибка загрузки')
    } finally {
      isLoading.value = false
    }
  }

  async function fetchById(id: string) {
    isLoading.value = true
    error.value = null
    try {
      currentRequest.value = await api.approvalGet(id)
    } catch (e: unknown) {
      error.value = getErrorMessage(e, 'Ошибка загрузки')
    } finally {
      isLoading.value = false
    }
  }

  async function create(formData: FormData): Promise<ApprovalRequest> {
    isLoading.value = true
    error.value = null
    try {
      const result = await api.approvalCreate(formData)
      await fetchMyRequests()
      return result
    } catch (e: unknown) {
      console.groupCollapsed('[approval][store] create failed')
      console.error(e)
      console.groupEnd()
      error.value = getErrorMessage(e, 'Ошибка создания')
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function cancel(id: string): Promise<void> {
    const result = await api.approvalCancel(id)
    const updateList = (list: ApprovalRequest[]) => {
      const idx = list.findIndex(r => r.id === id)
      if (idx !== -1) list[idx] = result
    }
    updateList(myRequests.value)
    updateList(incomingRequests.value)
    if (currentRequest.value?.id === id) currentRequest.value = result
  }

  function clear() {
    myRequests.value = []
    incomingRequests.value = []
    currentRequest.value = null
    error.value = null
  }

  return {
    myRequests,
    incomingRequests,
    currentRequest,
    isLoading,
    error,
    fetchMyRequests,
    fetchIncomingRequests,
    fetchById,
    create,
    cancel,
    clear,
  }
})
