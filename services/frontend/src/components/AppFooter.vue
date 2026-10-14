<!-- SPDX-FileCopyrightText: 2026 Stephan Strittmatter
     SPDX-License-Identifier: AGPL-3.0-only -->

<template>
  <footer
    class="px-4 py-3 text-center text-xs text-gray-500 dark:text-gray-400"
    data-testid="app-footer"
  >
    Frontend {{ format(store.frontendVersion) }} · Backend {{ format(store.backendVersion) }}
  </footer>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useBuildInfoStore } from '../stores/buildInfo'

const store = useBuildInfoStore()

function format(version: string | null): string {
  return version ? `v${version}` : '–'
}

onMounted(() => {
  void store.load()
})
</script>
