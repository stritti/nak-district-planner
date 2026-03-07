import pluginVue from 'eslint-plugin-vue'
import tseslint from 'typescript-eslint'

export default tseslint.config(
  // Vue rules — uses vue-eslint-parser as the main parser for .vue files
  ...pluginVue.configs['flat/essential'],
  // Tell vue-eslint-parser to use @typescript-eslint/parser for <script lang="ts"> blocks
  {
    files: ['**/*.vue'],
    languageOptions: {
      parserOptions: {
        parser: tseslint.parser,
      },
    },
  },
  // TypeScript rules scoped to .ts files only (so they don't override the vue parser)
  {
    files: ['**/*.ts'],
    extends: tseslint.configs.recommended,
  },
  {
    ignores: ['dist/**', 'node_modules/**'],
  },
)
