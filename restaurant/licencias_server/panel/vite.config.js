import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// En desarrollo el panel corre en :5173 y llama a la API en :8010.
// En producción Django sirve `dist/` ya compilado. Los assets se emiten bajo
// `/static/panel/` porque el entrypoint copia el build a `staticfiles/panel`
// y así WhiteNoise los sirve sin pasar por Django.
export default defineConfig({
  plugins: [react()],
  base: '/static/panel/',
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8010',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})