import react, { reactCompilerPreset } from '@vitejs/plugin-react'
import babel from '@rolldown/plugin-babel'
import { defineConfig } from 'vite'
import { fileURLToPath } from 'node:url'

// https://vite.dev/config/
export default defineConfig({
  root: 'src/views',
  publicDir: '../../public',
  build: { outDir: fileURLToPath(new URL('./dist', import.meta.url)), emptyOutDir: true },
  plugins: [
    react(),
    babel({ presets: [reactCompilerPreset()] })
  ],
})
