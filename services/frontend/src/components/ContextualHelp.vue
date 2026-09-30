<template>
  <section v-if="enabled && entries.length && helpStore.identity" role="region" aria-label="Kontextuelle Hilfe" class="mb-5 space-y-2" data-testid="contextual-help">
    <div v-for="entry in visibleEntries" :key="entry.help_id" class="rounded-lg border border-blue-200 bg-blue-50/70 dark:border-blue-900 dark:bg-blue-950/30 px-3 py-2 text-sm">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <h2 class="font-medium text-blue-900 dark:text-blue-100">{{ entry.title }}</h2>
        <div class="flex items-center gap-3">
          <button type="button" class="text-blue-700 dark:text-blue-300 underline underline-offset-2" :aria-expanded="expanded[entry.help_id] ?? false" @click="toggle(entry.help_id)">{{ expanded[entry.help_id] ? 'Einklappen' : 'Anzeigen' }}</button>
          <button type="button" class="text-gray-600 dark:text-gray-300 underline underline-offset-2" :aria-label="`${entry.title} ausblenden`" @click="helpStore.hide(entry.help_id, context)">Ausblenden</button>
        </div>
      </div>
      <div v-if="expanded[entry.help_id]" class="mt-2 text-gray-700 dark:text-gray-200">
        <p>{{ entry.description }}</p>
        <ol class="list-decimal pl-5 mt-2 space-y-1"><li v-for="step in entry.steps" :key="step">{{ step }}</li></ol>
        <RouterLink v-for="link in entry.links" :key="link.to" :to="link.to" class="inline-block mt-2 mr-3 text-blue-700 dark:text-blue-300 underline">{{ link.label }}</RouterLink>
      </div>
    </div>
    <button v-if="hiddenCount > 0" type="button" class="text-xs text-blue-700 dark:text-blue-300 underline underline-offset-2" @click="helpStore.restore(context)">Ausgeblendete Hilfe wiederherstellen</button>
  </section>
</template>

<script setup lang="ts">
import { computed, reactive } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useHelpStore } from '../stores/help'
import { resolveHelp, type HelpContext } from '../help/catalog'

const props = defineProps<{ context: HelpContext }>()
const auth = useAuthStore()
const helpStore = useHelpStore()
const expanded = reactive<Record<string, boolean>>({})
const enabled = import.meta.env.VITE_CONTEXTUAL_HELP_ENABLED !== 'false'
const entries = computed(() => resolveHelp(props.context, {
  authenticated: auth.isAuthenticated,
  memberships: auth.memberships,
  isSuperadmin: auth.isSuperadmin,
  accessStatus: auth.accessStatus,
}))
const visibleEntries = computed(() => entries.value.filter((entry) => !helpStore.isHidden(entry.help_id, props.context)))
const hiddenCount = computed(() => entries.value.length - visibleEntries.value.length)
function toggle(helpId: string) { expanded[helpId] = !expanded[helpId] }
</script>
