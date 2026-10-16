<!-- SPDX-FileCopyrightText: 2026 Stephan Strittmatter
     SPDX-License-Identifier: AGPL-3.0-only -->

<template>
  <InlineEditableCell
    :id="`leader-${field}-${layout}-${leader.id}`"
    :as="layout === 'mobile' ? 'div' : 'td'"
    :value="config.value"
    :display-value="config.display"
    :choices="config.choices"
    :empty-label="config.emptyLabel"
    :revision="leader.revision ?? ''"
    :label="`${config.label}: ${leader.name}`"
    :editable="editable"
    :coordinator="coordinator"
    :save="(value, revision) => save(field, value, revision)"
    :reload="() => reload(field)"
    :required="config.required"
    :max-length="config.maxLength"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { CongregationResponse } from '../../api/districts'
import { LEADER_RANKS, SPECIAL_ROLES, type LeaderResponse } from '../../api/leaders'
import type { InlineCellCoordinator } from '../../composables/useInlineCellCoordinator'
import InlineEditableCell from '../InlineEditableCell.vue'
import type { InlineLeaderField } from './inlineLeaderFields'

const props = defineProps<{
  leader: LeaderResponse
  field: InlineLeaderField
  layout: 'mobile' | 'desktop'
  editable: boolean
  congregations: CongregationResponse[]
  coordinator: InlineCellCoordinator
  save: (field: InlineLeaderField, value: string, revision: string) => Promise<void>
  reload: (field: InlineLeaderField) => Promise<{ value: string | null; revision: string }>
}>()

interface FieldConfig {
  label: string
  value: string
  display: string
  choices?: { value: string; label: string }[]
  emptyLabel?: string
  required?: boolean
  maxLength?: number
}

const config = computed<FieldConfig>(() => {
  const { leader } = props
  switch (props.field) {
    case 'name':
      return { label: 'Name', value: leader.name, display: leader.name, required: true, maxLength: 255 }
    case 'email':
      return { label: 'E-Mail', value: leader.email ?? '', display: leader.email || '—', maxLength: 255 }
    case 'phone':
      return { label: 'Telefon', value: leader.phone ?? '', display: leader.phone || '—', maxLength: 100 }
    case 'rank':
      return {
        label: 'Grad',
        value: leader.rank ?? '',
        display: leader.rank ?? '—',
        choices: LEADER_RANKS.map((r) => ({ value: r.value, label: r.label })),
        emptyLabel: 'Grad wählen…',
        required: true,
      }
    case 'special_role':
      return {
        label: 'Beauftragung',
        value: leader.special_role ?? '',
        display: leader.special_role ?? '—',
        choices: SPECIAL_ROLES.map((r) => ({ value: r.value, label: r.label })),
        emptyLabel: 'Keine',
      }
    case 'congregation_id':
      return {
        label: 'Heimat-Gemeinde',
        value: leader.congregation_id ?? '',
        display: props.congregations.find((c) => c.id === leader.congregation_id)?.name ?? '—',
        choices: props.congregations.map((c) => ({ value: c.id, label: c.name })),
        emptyLabel: 'Bezirksebene',
      }
    default:
      return {
        label: 'Status',
        value: String(leader.is_active),
        display: leader.is_active ? 'Aktiv' : 'Inaktiv',
        choices: [{ value: 'true', label: 'Aktiv' }, { value: 'false', label: 'Inaktiv' }],
        required: true,
      }
  }
})
</script>
