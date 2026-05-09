import {computed, type ComputedRef, ref} from "vue";
import { LoggerBrowser, AjaxError, LoadDataType, useB24Helper } from '@bitrix24/b24jssdk'
import type { B24Frame, TypeEnumAppStatus } from '@bitrix24/b24jssdk'
import type { Locale } from 'vue-i18n'
import type { LocaleObject } from '@nuxtjs/i18n'

export interface ProcessErrorData {
  description?: string
  isShowClearError?: boolean
  clearErrorHref?: string
  clearErrorTitle?: string
  homePageIsHide?: boolean
  homePageHref?: string
  homePageTitle?: string
}

const { initB24Helper, getB24Helper, destroyB24Helper: destroyB24HelperOry, usePullClient, useSubscribePullClient, startPullClient } = useB24Helper()
const isInitB24Helper = ref(false)

const moduleId = 'main'

type InitData = {
  appInfo?: {
    data?: {
      version?: number
      status?: TypeEnumAppStatus
    }
  }
  appSettings?: {
    data?: Map<string, unknown>
  }
  userSettings?: {
    data?: Map<string, unknown>
  }
  profileData?: {
    data?: {
      id?: number
      name?: string
      lastName?: string
      isAdmin?: boolean
    }
  }
}

function asRecord(value: unknown): Record<string, unknown> {
  if (typeof value === 'object' && value !== null) {
    return value as Record<string, unknown>
  }
  return {}
}

function asMap(value: unknown): Map<string, unknown> {
  return new Map(Object.entries(asRecord(value)))
}

function toNumber(value: unknown, fallback = 0): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

function isAdminValue(value: unknown): boolean {
  return value === true || value === 1 || value === '1' || value === 'Y' || value === 'y'
}

/**
 * Composable handling application initialization
 * Coordinates data loading via batch request
 */
export const useAppInit = (loggerTitle?: string) => {
  const $logger = LoggerBrowser.build(
    loggerTitle ?? 'App',
    import.meta.dev
  )

  // Stores
  const appSettings = useAppSettingsStore()
  const userSettings = useUserSettingsStore()
  const user = useUserStore()
  const api = useApiStore()

  /**
   * Initialize application data
   * Performs batch request and updates all stores
   */
  async function initApp(
    $b24: B24Frame,
    localesI18n: ComputedRef<LocaleObject[]>,
    setLocale: (locale: Locale) => Promise<void>
  ) {
    $logger.info('InitApp start')
    await initLang($b24, localesI18n, setLocale)

    let data: InitData

    try {
      // Не грузим LoadDataType.UserOptions — userSettings не используется
      // ни на одном функциональном экране (только в демо-обработчиках,
      // которые подгружают свои данные при необходимости). Это экономит
      // один из подзапросов в стартовом batch и ускоряет cold-start.
      await initB24Helper(
        $b24,
        [
          LoadDataType.App,
          LoadDataType.AppOptions,
          LoadDataType.Profile
        ]
      )
      isInitB24Helper.value = true

      const helper = getB24Helper()
      data = {
        appInfo: helper.appInfo as InitData['appInfo'],
        appSettings: helper.appOptions as InitData['appSettings'],
        userSettings: helper.userOptions as InitData['userSettings'],
        profileData: helper.profileInfo as InitData['profileData'],
      }
    } catch (error: unknown) {
      isInitB24Helper.value = false
      $logger.warn('B24Helper partial load failed, fallback to direct batch', error)

      const response = await $b24.callBatch({
        appInfo: { method: 'app.info' },
        appSettings: { method: 'app.option.get' },
        profileData: { method: 'profile' },
      })
      const fallbackData = response.getData() as Record<string, unknown>
      const appInfo = asRecord(fallbackData.appInfo)
      const profileData = asRecord(fallbackData.profileData)
      const appSettingsData = asRecord(fallbackData.appSettings)
      const userSettingsData: Record<string, unknown> = {}

      data = {
        appInfo: {
          data: {
            version: toNumber(appInfo.VERSION ?? appInfo.version, 1),
            status: (appInfo.STATUS ?? appInfo.status) as TypeEnumAppStatus,
          }
        },
        appSettings: {
          data: asMap(appSettingsData)
        },
        userSettings: {
          data: asMap(userSettingsData)
        },
        profileData: {
          data: {
            id: toNumber(profileData.ID ?? profileData.id, 0),
            name: String(profileData.NAME ?? profileData.name ?? ''),
            lastName: String(profileData.LAST_NAME ?? profileData.lastName ?? ''),
            isAdmin: isAdminValue(profileData.ADMIN ?? profileData.isAdmin),
          }
        },
      }
    }

    $logger.log('Init data >>', data)

    /**
     * @memo This can be used instead of `initB24Helper`
     */
    // const commands = {
    //   appInfo: { method: 'app.info' },
    //   appSettings: { method: 'app.option.get' },
    //   userSettings: { method: 'user.option.get' },
    //   profileData: { method: 'profile' }
    // }
    //
    // const response = await $b24.callBatch(commands)
    //
    // const data = response.getData()
    // $logger.log('Init data >>', data)

    // Update stores with received data
    user.initFromBatch({
      id: data.profileData?.data.id ?? undefined,
      name: data.profileData?.data.name ?? undefined,
      lastName: data.profileData?.data.lastName ?? undefined,
      isAdmin: data.profileData?.data.isAdmin
    })

    appSettings.setB24($b24)
    const appSettingsMap = data.appSettings?.data ?? new Map<string, unknown>()
    const userSettingsMap = data.userSettings?.data ?? new Map<string, unknown>()
    const appConfigSettings = appSettingsMap.get('configSettings')
    const userConfigSettings = userSettingsMap.get('configSettings')

    appSettings.initFromBatch({
      version: (data.appInfo?.data?.version ?? 1),
      status: data.appInfo?.data?.status,
      configSettings: (typeof appConfigSettings === 'object' && appConfigSettings !== null)
        ? appConfigSettings as Record<string, unknown>
        : undefined
    })

    userSettings.setB24($b24)
    userSettings.initFromBatch({
      configSettings: (typeof userConfigSettings === 'object' && userConfigSettings !== null)
        ? userConfigSettings as Record<string, unknown>
        : undefined
    })

    await api.init($b24)

    $logger.info('InitApp stop')
  }

  async function initLang(
    $b24: B24Frame,
    localesI18n: ComputedRef<LocaleObject[]>,
    setLocale: (locale: Locale) => Promise<void>
  ) {
    const b24CurrentLang = $b24.getLang()
    if (localesI18n.value.filter(i => i.code === b24CurrentLang).length > 0) {
      await setLocale(b24CurrentLang)
      $logger.log('setLocale >>>', b24CurrentLang)
    } else {
      $logger.warn('not support locale >>>', b24CurrentLang)
    }
  }

  /**
   * Reloads data
   */
  async function reloadData() {
    if (!b24Helper.value) {
      $logger.warn('reloadData skipped, B24Helper is not initialized')
      return
    }

    await b24Helper.value?.loadData([
      LoadDataType.AppOptions,
      LoadDataType.UserOptions
    ])

    const data = {
      appSettings: getB24Helper().appOptions,
      userSettings: getB24Helper().userOptions
    }

    $logger.log('Reload data >>', data)

    // Update stores with received data
    appSettings.initFromBatch({
      configSettings: (data.appSettings?.data ?? new Map()).get('configSettings')
    })

    userSettings.initFromBatch({
      configSettings: (data.userSettings?.data ?? new Map()).get('configSettings')
    })

    $logger.info('reloadData stop')
  }

  const b24Helper = computed(() => {
    if (isInitB24Helper.value) {
      return getB24Helper()
    }

    return null
  })

  const destroyB24Helper = () => {
    isInitB24Helper.value = false
    destroyB24HelperOry()
  }

  function processErrorGlobal(
    error: unknown | string | Error,
    processErrorData?: ProcessErrorData
  ) {
    $logger.error(error)

    let statusMessage = 'Error'
    let message = ''
    let statusCode = 404

    if (error instanceof AjaxError) {
      statusCode = error.status
      statusMessage = error.name
      message = `${error.message}`
    } else if (error instanceof Error) {
      message = error.message
    } else {
      message = error as string
    }

    showError({
      statusCode,
      statusMessage,
      message,
      data: Object.assign({}, (processErrorData ?? {})),
      cause: error,
      fatal: true
    })
  }

  return {
    $logger,
    moduleId,
    initApp,
    initLang,
    reloadData,
    b24Helper,
    usePullClient,
    useSubscribePullClient,
    startPullClient,
    destroyB24Helper,
    processErrorGlobal
  }
}
