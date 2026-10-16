import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['icon.svg'],
      manifest: {
        name: 'MewNook · 你的专注小窝',
        short_name: 'MewNook',
        description: '和猫娘一起专注、休息、听雨声。',
        theme_color: '#131b2d',
        background_color: '#131b2d',
        display: 'standalone',
        start_url: '/',
        icons: [{ src: '/icon.svg', sizes: 'any', type: 'image/svg+xml', purpose: 'any maskable' }]
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,svg,woff2,png,webp}'],
        navigateFallback: '/index.html',
        // Independent runtime tests must not be replaced by the PWA app shell.
        navigateFallbackDenylist: [/^\/inochi2d-test(?:\/|$)/]
      }
    })
  ]
})
