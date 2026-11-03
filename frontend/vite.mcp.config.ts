import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { viteSingleFile } from 'vite-plugin-singlefile'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath } from 'node:url'

// The MCP host reads one HTML resource without a separate asset server.
export default defineConfig({
  root: fileURLToPath(new URL('./src/views/mcp', import.meta.url)),
  envDir: fileURLToPath(new URL('.', import.meta.url)),
  publicDir: false,
  plugins: [tailwindcss(), react(), viteSingleFile()],
  build: {
    outDir: fileURLToPath(new URL('./dist', import.meta.url)),
    emptyOutDir: false,
    rolldownOptions: {
      input: fileURLToPath(new URL('./src/views/mcp/mcp.html', import.meta.url)),
    },
  },
})
