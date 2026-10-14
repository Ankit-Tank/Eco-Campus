import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// In development (and `vite preview`), requests to /api and /uploads are forwarded to the FastAPI
// backend, so the frontend can call "/api/auth/..." and never runs into CORS errors.
// The target comes from VITE_BACKEND_URL in frontend/.env (default http://127.0.0.1:8000).
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backend = { target: env.VITE_BACKEND_URL || 'http://127.0.0.1:8000', changeOrigin: true }
  const proxy = {
    '/api': backend,
    '/uploads': backend, // complaint photos saved in backend/uploads/complaints
  }

  return {
    plugins: [react()],
    server: { port: 5173, proxy },
    preview: { port: 4173, proxy },
    build: {
      rollupOptions: {
        output: {
          // Keep the big chart library out of the main bundle
          manualChunks: { recharts: ['recharts'], react: ['react', 'react-dom', 'react-router-dom'] },
        },
      },
    },
  }
})
