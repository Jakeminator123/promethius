import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/docs': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  },
  build: {
    // Lägg till denna del
    rollupOptions: {
      // Detta är "inofficiellt" men brukar hjälpa i praktiken!
      maxParallelFileOps: 10 // Testa gärna 10, 20 eller 30 (börja lågt)
    }
  }
})