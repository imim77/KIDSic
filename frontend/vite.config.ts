import react, { reactCompilerPreset } from '@vitejs/plugin-react'
import babel from '@rolldown/plugin-babel'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'
import { fileURLToPath } from 'node:url'


export default defineConfig({
  root: 'src/pages',
  resolve: { alias: {
    '@': fileURLToPath(new URL('./src', import.meta.url)),

    '/mvvm': fileURLToPath(new URL('./src/mvvm', import.meta.url)),
  } },
  envDir: fileURLToPath(new URL('.', import.meta.url)),
  publicDir: '../../public',
  server: { proxy: { '/api': process.env.KIDSIC_API_TARGET ?? 'http://127.0.0.1:8000' } },
  build: {
    outDir: fileURLToPath(new URL('./dist', import.meta.url)),
    emptyOutDir: true,
    rolldownOptions: {
      input: {
        index: fileURLToPath(new URL('./src/pages/index.html', import.meta.url)),
      },
    },
  },
  plugins: [
    tailwindcss(),
    react(),
    babel({ presets: [reactCompilerPreset()] })
  ],
})
