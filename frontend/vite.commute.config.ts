import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { viteSingleFile } from 'vite-plugin-singlefile'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath } from 'node:url'

export default defineConfig({
  root: fileURLToPath(new URL('./src/views/commute', import.meta.url)),
  resolve: {alias:{'@':fileURLToPath(new URL('./src', import.meta.url))}},
  publicDir:false,
  plugins:[tailwindcss(),react(),viteSingleFile()],
  build:{outDir:fileURLToPath(new URL('./dist',import.meta.url)),emptyOutDir:false,
    rolldownOptions:{input:fileURLToPath(new URL('./src/views/commute/day-mcp.html',import.meta.url))}},
})
