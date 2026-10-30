<!-- SPDX-FileCopyrightText: 2026 Stephan Strittmatter
     SPDX-License-Identifier: AGPL-3.0-only -->

<template>
  <p
    v-if="message"
    role="alert"
    class="text-sm text-red-600 dark:text-red-400"
    data-testid="error-alert"
  >
    {{ message }}
  </p>
</template>

<script setup lang="ts">
/**
 * Error text of a view or dialog, announced to screen readers.
 *
 * Pass the text from `userMessage()` so every view shows the same wording per
 * HTTP status; renders nothing while there is no error.
 */
defineProps<{ message?: string | null }>()
</script>
