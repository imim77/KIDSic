import react, { reactCompilerPreset } from '@vitejs/plugin-react'
import babel from '@rolldown/plugin-babel'
import { defineConfig } from 'vite'
import { fileURLToPath } from 'node:url'

// https://vite.dev/config/
export default defineConfig({
  root: 'src/views',
  envDir: fileURLToPath(new URL('.', import.meta.url)),
  publicDir: '../../public',
  server: { proxy: { '/api': process.env.KIDSIC_API_TARGET ?? 'http://127.0.0.1:8000' } },
  build: { outDir: fileURLToPath(new URL('./dist', import.meta.url)), emptyOutDir: true },
  plugins: [
    react(),
    babel({ presets: [reactCompilerPreset()] })
  ],
})
