import react, { reactCompilerPreset } from '@vitejs/plugin-react'
import babel from '@rolldown/plugin-babel'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'
import { fileURLToPath } from 'node:url'

// https://vite.dev/config/
export default defineConfig({
  root: 'src/views',
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  envDir: fileURLToPath(new URL('.', import.meta.url)),
  publicDir: '../../public',
  server: { proxy: { '/api': process.env.KIDSIC_API_TARGET ?? 'http://127.0.0.1:8000' } },
  build: { outDir: fileURLToPath(new URL('./dist', import.meta.url)), emptyOutDir: true },
  plugins: [
    tailwindcss(),
    react(),
    babel({ presets: [reactCompilerPreset()] })
  ],
})
