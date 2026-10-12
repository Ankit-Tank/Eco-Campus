import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In development, requests to /api and /uploads are forwarded to the FastAPI backend.
// So the frontend can call "/api/auth/..." and we never see CORS errors.
const backend = { target: 'http://localhost:8000', changeOrigin: true }

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': backend,
      '/uploads': backend, // complaint photos saved in backend/uploads/complaints
    },
  },
})
