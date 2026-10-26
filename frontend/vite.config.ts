/// <reference types="vitest/config" />
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  // In development the Vite server proxies API + uploaded images to FastAPI,
  // so the browser only ever talks to one origin.
  const backend = env.VITE_BACKEND_PROXY_TARGET || 'http://localhost:8000'
  // secure: false lets the proxy reach a backend on https://localhost with the Office dev certificate.
  const to = { target: backend, changeOrigin: true, secure: false }

  return {
    // Public path the app is served under, e.g. '/signature/'. Set at build time.
    base: env.VITE_BASE_PATH || '/',
    plugins: [react(), tailwindcss()],
    server: {
      port: 5173,
      proxy: {
        '/api': to,
        '/uploads': to,
        '/static': to,
        '^/banner/': to,
        '/outlook-addin': to,
      },
    },
    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: ['./src/test/setup.ts'],
      css: false,
    },
  }
})
