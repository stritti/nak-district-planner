import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import tailwindcss from "@tailwindcss/vite";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    vue(),
    tailwindcss(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["icons/*.png", "icons/*.svg"],
      manifest: {
        name: "NAK Bezirksplaner",
        short_name: "Bezirksplaner",
        description: "Veranstaltungsplanung und Dienstplan-Matrix für Neuapostolische Kirche Bezirke",
        theme_color: "#2563eb",
        background_color: "#ffffff",
        display: "standalone",
        orientation: "any",
        lang: "de-DE",
        icons: [
          {
            src: "/icons/pwa-icon-192.png",
            sizes: "192x192",
            type: "image/png",
          },
          {
            src: "/icons/pwa-icon-512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "any maskable",
          },
        ],
      },
      workbox: {
        globPatterns: ["**/*.{js,css,html,ico,png,svg,woff2}"],
        runtimeCaching: [
          {
            urlPattern: /^\/api\/.*/i,
            handler: "NetworkOnly",
          },
        ],
      },
    }),
  ],
  server: {
    proxy: {
      // Dev proxy: forward /api requests to the backend
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
});
