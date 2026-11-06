import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { viteSingleFile } from 'vite-plugin-singlefile'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath } from 'node:url'

// The MCP host reads one HTML resource without a separate asset server.
export default defineConfig({
  root: fileURLToPath(new URL('./src/pages', import.meta.url)),
  resolve: { alias: {
    '@': fileURLToPath(new URL('./src', import.meta.url)),
    // Pages sit beside, not above, the screens they load.
    '/mvvm': fileURLToPath(new URL('./src/mvvm', import.meta.url)),
  } },
  envDir: fileURLToPath(new URL('.', import.meta.url)),
  publicDir: false,
  plugins: [tailwindcss(), react(), viteSingleFile()],
  build: {
    outDir: fileURLToPath(new URL('./dist', import.meta.url)),
    emptyOutDir: false,
    rolldownOptions: {
      input: fileURLToPath(new URL('./src/pages/mcp.html', import.meta.url)),
    },
  },
})
