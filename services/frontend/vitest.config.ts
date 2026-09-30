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
        "src/composables/base64url.ts",
        "src/composables/pkce.ts",
        "src/composables/oidcToken.ts",
        "src/composables/oidcSession.ts",
        "src/composables/oidcDiscovery.ts",
        "src/composables/oidcAuthorization.ts",
        "src/composables/oidcRefresh.ts",
        "src/composables/refreshScheduler.ts",
        "src/composables/useOIDC.ts",
        "src/api/leaderUnavailabilities.ts",
        "src/stores/leaderUnavailabilities.ts",
        "src/components/LeaderUnavailabilityForm.vue",
        "src/components/LeaderUnavailabilityList.vue",
        "src/components/CopyButton.vue",
        "src/components/EmptyState.vue",
        "src/components/ConfirmHost.vue",
        "src/composables/useConfirm.ts",
        "src/composables/useToast.ts",
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
