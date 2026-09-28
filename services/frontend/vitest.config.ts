import { defineConfig } from "vitest/config";
import vue from "@vitejs/plugin-vue";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: {
      "@": "/src",
    },
  },
  test: {
    environment: "happy-dom",
    include: ["src/**/*.test.ts"],
    coverage: {
      provider: "v8",
      include: [
        "src/composables/jwt.ts",
        "src/composables/oidcToken.ts",
        "src/composables/oidcRefresh.ts",
        "src/composables/useOIDC.ts",
        "src/api/leaderUnavailabilities.ts",
        "src/stores/leaderUnavailabilities.ts",
        "src/components/LeaderUnavailabilityForm.vue",
        "src/components/LeaderUnavailabilityList.vue",
      ],
      thresholds: {
        perFile: true,
        statements: 80,
        branches: 80,
        functions: 80,
        lines: 80,
      },
    },
  },
});
