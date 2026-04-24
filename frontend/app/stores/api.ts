import type { B24Frame } from '@bitrix24/b24jssdk'
import { withoutTrailingSlash } from 'ufo'

export interface ApprovalVote {
  id: string
  user_id: string
  decision: 'approve' | 'reject'
  comment: string
  voted_at: string
}

export interface ApprovalRequest {
  id: string
  initiator_id: string
  comment: string
  approver_ids: string[]
  threshold_type: 'all' | 'majority'
  status: 'collecting' | 'approved' | 'rejected' | 'cancelled'
  dialog_id: string
  bot_message_id: string
  file_ids: string[]
  created_at: string
  votes?: ApprovalVote[]
}

export const useApiStore = defineStore(
  'api',
  () => {
    let $b24: null | B24Frame = null
    const config = useRuntimeConfig()
    const apiUrl = withoutTrailingSlash(config.public.apiUrl)

    const tokenJWT = ref('')

    const isInitTokenJWT = computed(() => {
      return tokenJWT.value.length > 2
    })

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

    const postInstall = async (data: Record<string, any>): Promise<Record<string, any>> => {
      return await $api('/api/install', {
        method: 'POST',
        body: JSON.stringify(data),
      })
    }

    const getToken = async (data: Record<string, any>): Promise<{ token: string }> => {
      return await $api('/api/getToken', {
        method: 'POST',
        body: JSON.stringify(data),
      })
    }

    const approvalCreate = async (formData: FormData): Promise<ApprovalRequest> => {
      return await $fetch(`${apiUrl}/api/approval/create`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${tokenJWT.value}` },
        body: formData,
      })
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
