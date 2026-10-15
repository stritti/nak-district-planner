<!-- SPDX-FileCopyrightText: 2026 Stephan Strittmatter
     SPDX-License-Identifier: AGPL-3.0-only -->

<template>
  <InlineEditableCell
    :id="'responsible-' + layout + '-' + event.id"
    as="div"
    :value="event.responsible?.leader_id ?? ''"
    :display-value="event.responsible?.name ?? 'Dienstleiter zuweisen'"
    :choices="choices"
    :revision="event.revision ?? ''"
    :label="'Dienstleiter: ' + event.title"
    :editable="true"
    :coordinator="coordinator"
    :save="save"
    required
  />
</template>

<script setup lang="ts">
import type { EventResponse } from '../api/events'
import type { InlineCellCoordinator } from '../composables/useInlineCellCoordinator'
import InlineEditableCell from './InlineEditableCell.vue'

defineProps<{
  layout: 'mobile' | 'desktop'
  event: EventResponse
  choices: { value: string; label: string }[]
  coordinator: InlineCellCoordinator
  save: (leaderId: string, revision: string) => Promise<void>
}>()
</script>
