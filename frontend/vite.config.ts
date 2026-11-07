import path from 'node:path'
import { fileURLToPath } from 'node:url'

import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// https://vite.dev/config/
export default defineConfig({
  cacheDir: path.resolve(__dirname, 'node_modules/.vite'),
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  plugins: [
    react(),
  ],
  build: {
    /* emojiDataRu — отдельный async-чанк ~1.1 MB (emojibase ru); грузится только при открытии пикера. */
    chunkSizeWarningLimit: 1300,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/react-dom') || id.includes('node_modules/react/')) return 'vendor-react'
          if (id.includes('node_modules/react-router')) return 'vendor-router'
          if (id.includes('node_modules/@tanstack/react-query')) return 'vendor-query'
          if (id.includes('node_modules/@tiptap/')) return 'vendor-tiptap'
          if (id.includes('node_modules/@phosphor-icons')) return 'vendor-icons'
        },
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:9062',
        changeOrigin: true,
      },
      '/docs': { target: 'http://127.0.0.1:9062', changeOrigin: true },
      '/redoc': { target: 'http://127.0.0.1:9062', changeOrigin: true },
      '/openapi.json': { target: 'http://127.0.0.1:9062', changeOrigin: true },
    },
  },
})
