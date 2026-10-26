import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Skill Analysis Backend (port 8000)
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      // CCTV Analytics Backend (port 8001)
      '/cctv-api': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/cctv-api/, ''),
      },
      // CCTV Exported MP4 Video artifacts
      '/exports': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
    },
  },
});
