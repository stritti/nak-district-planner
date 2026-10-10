import { readFileSync } from "node:fs";
import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import tailwindcss from "@tailwindcss/vite";
import { VitePWA } from "vite-plugin-pwa";

// Shown in the footer; release-please bumps package.json with every release.
const { version } = JSON.parse(
  readFileSync(new URL("./package.json", import.meta.url), "utf-8"),
) as { version: string };

export default defineConfig({
  define: {
    __APP_VERSION__: JSON.stringify(version),
  },
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
        // Direct API/ICS navigations must reach the backend, not the app shell (#539).
        navigateFallbackDenylist: [/^\/api(?:\/|$)/, /^\/health(?:\?|$)/],
        runtimeCaching: [
          {
            urlPattern: ({ url }) => url.pathname.startsWith("/api"),
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
