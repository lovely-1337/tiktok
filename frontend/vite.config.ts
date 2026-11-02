import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/register': 'http://127.0.0.1:8000',
      '/login': 'http://127.0.0.1:8000',
      '/users': 'http://127.0.0.1:8000',
      '/templates': 'http://127.0.0.1:8000',
      '/launches': 'http://127.0.0.1:8000',
    },
  },
})
