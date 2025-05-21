import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import API_BASE_URL from "./src/components/config";

export default defineConfig({
  server: {
    host: "0.0.0.0",
    port: 3300,
    proxy: {
      '/api': `${API_BASE_URL}`,
    },
    historyApiFallback: true,
  },
  plugins: [react()],
});
