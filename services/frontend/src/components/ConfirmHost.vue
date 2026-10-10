<!-- SPDX-FileCopyrightText: 2026 Stephan Strittmatter
     SPDX-License-Identifier: AGPL-3.0-only -->

<template>
  <ConfirmDialog
    v-if="options"
    :open="isRevealed"
    :title="options.title"
    :message="options.message"
    :confirm-text="options.confirmText"
    :cancel-text="options.cancelText"
    :variant="options.variant"
    :dangerous="options.dangerous"
    @confirm="confirm"
    @cancel="cancel"
  />
</template>

<script setup lang="ts">
import ConfirmDialog from './ConfirmDialog.vue'
import { useConfirmHost } from '../composables/useConfirm'

const { options, isRevealed, confirm, cancel } = useConfirmHost()
</script>
