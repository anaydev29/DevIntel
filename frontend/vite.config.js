import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// In development the React app runs on :5173 and forwards API calls to FastAPI on :8000.
const API = 'http://127.0.0.1:8000'
const prefixes = ['/rankings', '/technologies', '/categories', '/pipeline', '/health']

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { proxy: Object.fromEntries(prefixes.map((p) => [p, API])) },
})
