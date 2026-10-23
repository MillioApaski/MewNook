import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'


// Keep the canonical experimental route available in dev and production preview.
const standaloneSmokeRoute: Plugin = {
  name: 'standalone-inochi-smoke-route',
  configureServer(server) {
    server.middlewares.use((req, _res, next) => {
      if (req.url?.split('?')[0] === '/inochi2d-test/smoke') req.url = req.url.replace('/smoke', '/smoke.html')
      next()
    })
  },
  configurePreviewServer(server) {
    server.middlewares.use((req, _res, next) => {
      if (req.url?.split('?')[0] === '/inochi2d-test/smoke') req.url = req.url.replace('/smoke', '/smoke.html')
      next()
    })
  }
}

export default defineConfig({
  plugins: [
    standaloneSmokeRoute,
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
        // Install the app shell first; room art and experimental rigs are fetched on demand.
        globIgnores:['inochi2d-test/**','inochi2d/**','assets/rooms/**','assets/companion/**'],
        runtimeCaching:[
          {urlPattern:/\/inochi2d(?:-test)?\/.*\.js(?:\?.*)?$/,handler:'NetworkFirst',options:{cacheName:'mewnook-runtime-v1',expiration:{maxEntries:16,maxAgeSeconds:2592000},cacheableResponse:{statuses:[200]}}},
          {urlPattern:/\/inochi2d(?:-test)?\/.*\.(?:inx|wasm)(?:\?.*)?$/,handler:'CacheFirst',options:{cacheName:'mewnook-rig-v1',expiration:{maxEntries:24,maxAgeSeconds:2592000},cacheableResponse:{statuses:[200]}}},
          {urlPattern:/\/(?:assets\/(?:rooms|companion)|inochi2d)\/.*\.(?:png|webp|svg)(?:\?.*)?$/,handler:'NetworkFirst',options:{cacheName:'mewnook-art-v1',expiration:{maxEntries:32,maxAgeSeconds:2592000},cacheableResponse:{statuses:[200]}}}
        ],
        navigateFallback: '/index.html',
        // Independent runtime tests must not be replaced by the PWA app shell.
        navigateFallbackDenylist: [/^\/inochi2d-test(?:\/|$)/]
      }
    })
  ]
})
