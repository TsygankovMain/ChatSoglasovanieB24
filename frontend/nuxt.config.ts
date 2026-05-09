import tailwindcss from '@tailwindcss/vite'
import { contentLocales } from './i18n/i18n.map'

export default defineNuxtConfig({
  modules: [
    '@bitrix24/b24ui-nuxt',
    '@bitrix24/b24jssdk-nuxt',
    '@nuxt/eslint',
    '@nuxtjs/i18n',
    '@pinia/nuxt'
  ],

  ssr: false,

  devtools: { enabled: false },

  runtimeConfig: {
    /**
     * @memo this will be overwritten from .env or Docker_*
     * @see https://nuxt.com/docs/guide/going-further/runtime-config#example
     */
    public: {
      appUrl: '',
      apiUrl: ''
    }
  },

  compatibilityDate: '2025-07-16',

  app: {
    head: {
      title: 'Starter',
      link: [
        { rel: 'icon', type: 'image/x-icon', href: '/favicon.ico' }
      ],
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' }
      ],
      htmlAttrs: { class: 'light' }
    }
  },

  css: ['~/assets/css/main.css'],

  vite: {
    plugins: [
      tailwindcss()
    ],
    optimizeDeps: {
      include: [
        'vue-i18n',
        '@intlify/shared',
        '@intlify/message-compiler',
        '@intlify/core-base',
        '@intlify/core',
        '@intlify/utils/h3',
        'ufo',
        '@bitrix24/b24jssdk',
      ]
    },
    server: {
      proxy: {
        '/api': { target: process.env.SERVER_HOST || 'http://api-need_set:8000', changeOrigin: true }
      }
    }
  },

  nitro: {
    devProxy: {
      '/api': { target: process.env.SERVER_HOST || 'http://api-need_set:8000', changeOrigin: true }
    },
  },

  i18n: {
    detectBrowserLanguage: false,
    strategy: 'no_prefix',
    langDir: 'locales',
    locales: contentLocales,
    defaultLocale: 'en',
    // Грузить только активную локаль. После iframe-handshake выставляем язык
    // из Bitrix24 (см. useAppInit.initLang). Без lazy все 19 файлов локалей
    // попадают в initial bundle (≈ +100–200 КБ JS) и замедляют cold-start.
    lazy: true
  }
})
