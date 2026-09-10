import path from 'node:path';
import { fileURLToPath } from 'node:url';
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

const rootDir = path.dirname(fileURLToPath(import.meta.url));

// Dentro de docker compose la API es otro contenedor (http://api:8000).
// Fuera de Docker es un proceso local; usamos 127.0.0.1 y no localhost porque
// si Node resuelve ::1 y uvicorn escucha en IPv4, el proxy falla.
const destinoApi = process.env.VITE_PROXY_TARGET ?? 'http://127.0.0.1:8000';

// A traves de un volumen de Docker los eventos del sistema de archivos no
// siempre llegan; con sondeo la recarga en caliente funciona igual.
const sondearCambios = process.env.VITE_USE_POLLING === 'true';

export default defineConfig({
  plugins: [react(), tailwindcss()],

  // El .env unico vive en la raiz del proyecto, no dentro de web/.
  envDir: path.resolve(rootDir, '..'),

  resolve: {
    alias: { '@': path.resolve(rootDir, 'src') },
  },

  server: {
    port: 5173,
    proxy: {
      '/api': { target: destinoApi, changeOrigin: true },
    },
    watch: sondearCambios ? { usePolling: true, interval: 400 } : undefined,
  },

  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: true,
  },
});
