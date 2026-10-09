import { defineConfig } from "vitest/config";
import vue from "@vitejs/plugin-vue";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  define: {
    __APP_VERSION__: JSON.stringify("0.0.0-test"),
  },
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
      include: ["src/**/*.{ts,vue}"],
      exclude: [
        "src/**/*.test.ts",
        "src/**/__tests__/**",
        // Test doubles import Vitest and are not shipped as application code.
        "src/testing/**",
        // Type-only modules have no emitted runtime behavior to cover.
        "src/**/*.d.ts",
        "src/types/**",
        "src/composables/oidcTypes.ts",
        // Bootstrap wiring is exercised by build/E2E checks rather than unit tests.
        "src/main.ts",
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