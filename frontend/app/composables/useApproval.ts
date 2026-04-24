import type { ApprovalRequest } from '~/stores/api'

export const useApproval = () => {
  const store = useApprovalsStore()

  async function create(params: {
    comment: string
    approverIds: string[]
    thresholdType: 'all' | 'majority'
    dialogId: string
    files?: File[]
  }): Promise<ApprovalRequest> {
    const formData = new FormData()
    formData.append('comment', params.comment)
    formData.append('approver_ids', JSON.stringify(params.approverIds))
    formData.append('threshold_type', params.thresholdType)
    formData.append('dialog_id', params.dialogId)
    if (params.files) {
      for (const file of params.files) {
        formData.append('files', file)
      }
    }
    return store.create(formData)
  }

  return {
    myRequests: computed(() => store.myRequests),
    incomingRequests: computed(() => store.incomingRequests),
    currentRequest: computed(() => store.currentRequest),
    isLoading: computed(() => store.isLoading),
    error: computed(() => store.error),
    create,
    list: store.fetchMyRequests,
    listIncoming: store.fetchIncomingRequests,
    getById: store.fetchById,
    cancel: store.cancel,
  }
}
