import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'
import { fileURLToPath } from 'node:url'

export default defineConfig({
  resolve: { alias: {
    '@test-support': fileURLToPath(new URL('./test-support', import.meta.url)),
    '@': fileURLToPath(new URL('./src', import.meta.url)),
  } },
  plugins: [react()],
  test: {
    environment: 'jsdom',

    include: ['src/**/*.test.{ts,tsx}', 'tests/**/*.test.{ts,tsx}'],
    clearMocks: true,
    restoreMocks: true,
    setupFiles: ['test-support/setup.ts'],
  },
})
