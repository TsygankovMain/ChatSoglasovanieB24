import type { B24Frame } from '@bitrix24/b24jssdk'
import { withoutTrailingSlash } from 'ufo'

export interface ApprovalVote {
  id: string
  user_id: string
  user_name?: string
  decision: 'approve' | 'reject'
  comment: string
  voted_at: string
}

export interface ApprovalEvent {
  id: string
  request_id: string
  type: string
  user_id: string
  user_name?: string
  decision: string
  status_before: string
  status_after: string
  message: string
  meta?: Record<string, unknown>
  created_at: string
}

export interface ApprovalRequest {
  id: string
  initiator_id: string
  initiator_name?: string
  comment: string
  approver_ids: string[]
  approver_names?: Record<string, string>
  threshold_type: 'all' | 'majority'
  status: 'collecting' | 'approved' | 'rejected' | 'cancelled'
  dialog_id: string
  bot_message_id: string
  bot_message_ids?: string[]
  bot_issue?: string
  bot_dialog_id?: string
  bot_dialog_ids?: string[]
  file_ids: string[]
  file_names?: string[]
  files?: Array<{ id: string; name: string; url: string }>
  created_at: string
  votes?: ApprovalVote[]
  events?: ApprovalEvent[]
}

export const useApiStore = defineStore(
  'api',
  () => {
    let $b24: null | B24Frame = null
    const config = useRuntimeConfig()
    const apiUrlRaw = String(config.public.apiUrl ?? '').trim()
    const apiUrl = (apiUrlRaw && apiUrlRaw !== '/')
      ? withoutTrailingSlash(apiUrlRaw)
      : ''
    const makeApiUrl = (path: string) => (apiUrl ? `${apiUrl}${path}` : path)

    const tokenJWT = ref('')

    const createTraceId = () => `approval-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`

    const parseFetchError = (error: unknown) => {
      if (typeof error !== 'object' || error === null) {
        return { message: String(error) }
      }
      const e = error as {
        message?: string
        status?: number
        statusText?: string
        data?: unknown
        response?: { status?: number, statusText?: string, _data?: unknown }
      }
      return {
        message: e.message ?? 'Unknown error',
        status: e.status ?? e.response?.status,
        statusText: e.statusText ?? e.response?.statusText,
        data: e.data ?? e.response?._data,
      }
    }

    const $api = $fetch.create({
      baseURL: apiUrl,
      headers: {
        'Content-Type': 'application/json'
      }
    })

    // Health check
    const checkHealth = async (): Promise<{
      status: string
      backend: string
      timestamp: number
    }> => {
      try {
        return await $api('/api/health', {
          headers: {
            Authorization: `Bearer ${tokenJWT.value}`
          }
        })
      } catch {
        throw new Error('Backend health check failed')
      }
    }

    // API
    const getEnum = async (): Promise<string[]> => {
      return await $api('/api/enum', {
        headers: {
          Authorization: `Bearer ${tokenJWT.value}`
        }
      })
    }

    const getList = async (): Promise<string[]> => {
      return await $api('/api/list', {
        headers: {
          Authorization: `Bearer ${tokenJWT.value}`
        }
      })
    }

    const postInstall = async (data: Record<string, unknown>): Promise<Record<string, unknown>> => {
      return await $api('/api/install', {
        method: 'POST',
        body: JSON.stringify(data),
      })
    }

    const getToken = async (data: Record<string, unknown>): Promise<{ token: string }> => {
      return await $api('/api/getToken', {
        method: 'POST',
        body: JSON.stringify(data),
      })
    }

    const approvalCreate = async (formData: FormData): Promise<ApprovalRequest> => {
      const traceId = createTraceId()
      const files = formData.getAll('files')
      const approversRaw = String(formData.get('approver_ids') ?? '[]')
      let approversCount = 0
      try {
        const parsed = JSON.parse(approversRaw)
        approversCount = Array.isArray(parsed) ? parsed.length : 0
      } catch {
        approversCount = 0
      }

      if (import.meta.dev) {
        console.groupCollapsed(`[approval][create][${traceId}] request`)
        console.log('dialog_id', String(formData.get('dialog_id') ?? ''))
        console.log('threshold_type', String(formData.get('threshold_type') ?? ''))
        console.log('approvers_count', approversCount)
        console.log('comment_length', String(formData.get('comment') ?? '').length)
        console.log('files_count', files.length)
        console.groupEnd()
      }

      try {
        const response = await $fetch<ApprovalRequest>(makeApiUrl('/api/approval/create'), {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${tokenJWT.value}`,
            'X-Approval-Trace-Id': traceId,
          },
          body: formData,
        })

        if (import.meta.dev) {
          console.groupCollapsed(`[approval][create][${traceId}] response`)
          console.log('raw', response)
          console.log('request_id', response.id)
          console.log('status', response.status)
          console.log('bot_message_id', response.bot_message_id ?? '')
          console.log('bot_message_ids', response.bot_message_ids ?? [])
          console.log('bot_dialog_id', response.bot_dialog_id ?? '')
          console.log('bot_dialog_ids', response.bot_dialog_ids ?? [])
          if (response.bot_issue) {
            console.warn('bot_issue', response.bot_issue)
          }
          if (!response.bot_message_id) {
            console.warn('[approval][create] request created but bot message was not posted')
          }
          console.groupEnd()
        }
        console.info(
          `[approval][create][${traceId}] summary request_id=${response.id} status=${response.status} source_dialog_id=${String(formData.get('dialog_id') ?? '')} bot_dialog_ids_count=${(response.bot_dialog_ids ?? []).length} bot_message_ids_count=${(response.bot_message_ids ?? []).length} bot_issue=${response.bot_issue ?? ''}`
        )
        return response
      } catch (error) {
        const details = parseFetchError(error)
        if (import.meta.dev) {
          console.groupCollapsed(`[approval][create][${traceId}] error`)
          console.error(details)
          console.groupEnd()
        }
        throw error
      }
    }

    const approvalList = async (role: 'initiator' | 'approver'): Promise<{ items: ApprovalRequest[] }> => {
      return await $api('/api/approval/list', {
        headers: { Authorization: `Bearer ${tokenJWT.value}` },
        params: { role },
      })
    }

    const approvalGet = async (id: string): Promise<ApprovalRequest> => {
      return await $api(`/api/approval/${id}`, {
        headers: { Authorization: `Bearer ${tokenJWT.value}` },
      })
    }

    const approvalCancel = async (requestId: string): Promise<ApprovalRequest> => {
      return await $api('/api/approval/cancel', {
        method: 'POST',
        headers: { Authorization: `Bearer ${tokenJWT.value}` },
        body: JSON.stringify({ request_id: requestId }),
      })
    }

    const init = async (b24: B24Frame) => {
      $b24 = b24
      await reinitToken()
    }

    const reinitToken = async () => {
      if ($b24 === null) {
        console.error('B24 non init. Use api.init()')
        return
      }

      const authData = $b24.auth.getAuthData()

      if(authData === false) {
        throw new Error('Some problem with auth. See App logic')
      }

      const user = useUserStore()
      const appSettings = useAppSettingsStore()

      const response = await getToken({
        DOMAIN: withoutTrailingSlash(authData.domain).replace('https://', '').replace('http://', ''),
        PROTOCOL: authData.domain.includes('https://') ? 1 : 0,
        LANG: $b24.getLang(),
        APP_SID: $b24.getAppSid(),
        AUTH_ID: authData.access_token,
        AUTH_EXPIRES: authData.expires_in,
        REFRESH_ID: authData.refresh_token,
        REFRESH_TOKEN: authData.refresh_token,
        member_id: authData.member_id,
        user_id: user.id,
        status: appSettings.status
      })

      tokenJWT.value = response.token
    }

    return {
      checkHealth,
      init,
      getEnum,
      getList,
      postInstall,
      approvalCreate,
      approvalList,
      approvalGet,
      approvalCancel,
    }
  }
)
