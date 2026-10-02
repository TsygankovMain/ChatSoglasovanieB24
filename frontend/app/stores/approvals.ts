import type { ApprovalRequest } from './api'

export const useApprovalsStore = defineStore('approvals', () => {
  const myRequests = ref<ApprovalRequest[]>([])
  const incomingRequests = ref<ApprovalRequest[]>([])
  const currentRequest = ref<ApprovalRequest | null>(null)
  const hasMoreMy = ref(false)
  const hasMoreIncoming = ref(false)
  const isLoading = ref(false)
  const isLoadingMore = ref(false)
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
      hasMoreMy.value = res.has_more
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
      hasMoreIncoming.value = res.has_more
    } catch (e: unknown) {
      error.value = getErrorMessage(e, 'Ошибка загрузки')
    } finally {
      isLoading.value = false
    }
  }

  async function fetchMore(role: 'initiator' | 'approver') {
    const list = role === 'initiator' ? myRequests : incomingRequests
    const hasMore = role === 'initiator' ? hasMoreMy : hasMoreIncoming
    isLoadingMore.value = true
    error.value = null
    try {
      const res = await api.approvalList(role, list.value.length)
      const known = new Set(list.value.map(r => r.id))
      list.value.push(...res.items.filter(r => !known.has(r.id)))
      hasMore.value = res.has_more
    } catch (e: unknown) {
      error.value = getErrorMessage(e, 'Ошибка загрузки')
    } finally {
      isLoadingMore.value = false
    }
  }

  // Lists come without the event log and file links; the full request replaces
  // its short version in place once it is opened.
  async function fetchById(id: string) {
    error.value = null
    try {
      const full = await api.approvalGet(id)
      currentRequest.value = full
      for (const list of [myRequests.value, incomingRequests.value]) {
        const idx = list.findIndex(r => r.id === id)
        if (idx !== -1) list[idx] = full
      }
    } catch (e: unknown) {
      error.value = getErrorMessage(e, 'Ошибка загрузки')
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
    // The cancel response carries only id and status — keep the rest of the card.
    const updateList = (list: ApprovalRequest[]) => {
      const idx = list.findIndex(r => r.id === id)
      if (idx !== -1) list[idx] = { ...list[idx]!, status: result.status }
    }
    updateList(myRequests.value)
    updateList(incomingRequests.value)
    if (currentRequest.value?.id === id) currentRequest.value = { ...currentRequest.value, status: result.status }
  }

  function clear() {
    myRequests.value = []
    incomingRequests.value = []
    currentRequest.value = null
    hasMoreMy.value = false
    hasMoreIncoming.value = false
    error.value = null
  }

  return {
    myRequests,
    incomingRequests,
    currentRequest,
    hasMoreMy,
    hasMoreIncoming,
    isLoading,
    isLoadingMore,
    error,
    fetchMyRequests,
    fetchIncomingRequests,
    fetchMore,
    fetchById,
    create,
    cancel,
    clear,
  }
})
