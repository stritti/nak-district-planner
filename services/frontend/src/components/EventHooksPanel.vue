<template>
  <section class="space-y-4" aria-label="Ereignis-Benachrichtigungen">
    <h2 class="text-lg font-semibold">Ereignis-Benachrichtigungen</h2>
    <p class="text-sm text-gray-500">
      E-Mails, die bei bestimmten Ereignissen im ausgewählten Bezirk versendet werden.
    </p>
    <p v-if="store.error" role="alert" class="text-red-600">{{ store.error }}</p>
    <p v-if="store.loading">Benachrichtigungen werden geladen…</p>
    <p v-else-if="store.items.length === 0">Noch keine Benachrichtigungen angelegt.</p>
    <ul v-else class="space-y-2">
      <li
        v-for="item in store.items"
        :key="item.id"
        class="border rounded p-3 flex justify-between gap-4"
        :data-testid="`event-hook-${item.id}`"
      >
        <div>
          <strong>{{ EVENT_LABELS[item.event_type] }}</strong>
          <p class="text-sm text-gray-500">{{ item.subject_template }} · {{ ROLE_LABELS[item.recipient_role] }}</p>
        </div>
        <div class="flex gap-2 items-center">
          <button type="button" class="btn-secondary" @click="edit(item)">Bearbeiten</button>
          <label class="flex items-center gap-1 text-sm">
            <input type="checkbox" :checked="item.is_active" :disabled="store.saving" @change="toggle(item)" />
            Aktiv
          </label>
        </div>
      </li>
    </ul>

    <form class="space-y-3 border rounded p-3" @submit.prevent="save">
      <h3 class="font-medium">{{ editing ? 'Benachrichtigung bearbeiten' : 'Benachrichtigung hinzufügen' }}</h3>
      <label class="block">Ereignis
        <select v-model="form.event_type" class="form-input" :disabled="editing !== null" name="event_type">
          <option v-for="(label, type) in EVENT_LABELS" :key="type" :value="type">{{ label }}</option>
        </select>
      </label>
      <label class="block">Empfängerrolle
        <select v-model="form.recipient_role" class="form-input" name="recipient_role">
          <option v-for="(label, role) in ROLE_LABELS" :key="role" :value="role">{{ label }}</option>
        </select>
      </label>
      <label class="block">Betreff
        <input v-model="form.subject_template" name="subject" maxlength="500" required class="form-input w-full" />
      </label>
      <label class="block">Nachricht
        <textarea v-model="form.body_template" name="body" maxlength="20000" required class="form-input w-full" />
      </label>
      <p class="text-xs text-gray-500" data-testid="placeholders">
        Platzhalter: {{ placeholderHint }}
      </p>
      <div class="flex gap-2">
        <button type="submit" :disabled="store.saving" class="btn-primary">
          {{ store.saving ? 'Speichert…' : 'Speichern' }}
        </button>
        <button v-if="editing" type="button" class="btn-secondary" @click="reset">Abbrechen</button>
      </div>
    </form>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useEventHooksStore } from '../stores/eventHooks'
import type { EventHook, EventHookCreateInput, EventType } from '../api/eventHooks'
import type { RecipientRole } from '../api/reminderConfigs'

const EVENT_LABELS: Record<EventType, string> = {
  SLOT_UNASSIGNED: 'Unbesetzter Gottesdienst (LÜCKE)',
  EXTERNAL_EVENT_DETECTED: 'Neuer externer Termin zur Prüfung',
  SYNC_ERROR: 'Fehler bei Kalender-Synchronisation',
  REGISTRATION_RECEIVED: 'Registrierung freigegeben',
  ASSIGNMENT_CONFIRMED: 'Dienstzuweisung bestätigt',
  PLAN_FINALIZED: 'Monatsplan freigegeben',
}
const ROLE_LABELS: Record<RecipientRole, string> = {
  DISTRICT_ADMIN: 'Bezirksadministrator',
  PLANNER: 'Planer',
  CONGREGATION_ADMIN: 'Gemeindeadministrator (Bezirkszuordnung)',
  VIEWER: 'Leser',
}

const props = defineProps<{ districtId: string }>()
const store = useEventHooksStore()
const editing = ref<string | null>(null)
const defaults = (): EventHookCreateInput => ({
  event_type: 'EXTERNAL_EVENT_DETECTED',
  recipient_role: 'DISTRICT_ADMIN',
  subject_template: '',
  body_template: '',
  is_active: true,
})
const form = reactive<EventHookCreateInput>(defaults())
const placeholderHint = computed(
  () => store.placeholdersFor(form.event_type).map(name => `{${name}}`).join(', ') || '–',
)

function reset() {
  editing.value = null
  Object.assign(form, defaults())
}

function edit(item: EventHook) {
  editing.value = item.id
  Object.assign(form, {
    event_type: item.event_type,
    recipient_role: item.recipient_role,
    subject_template: item.subject_template,
    body_template: item.body_template,
    is_active: item.is_active,
  })
}

async function save() {
  try {
    if (editing.value) {
      const { event_type: _immutable, ...changes } = form
      await store.update(editing.value, changes)
    } else {
      await store.create({ ...form })
    }
    reset()
  } catch {
    /* The store shows the error; the form keeps the input for correction. */
  }
}

async function toggle(item: EventHook) {
  try {
    if (item.is_active) await store.deactivate(item.id)
    else {
      const { recipient_role, subject_template, body_template } = item
      await store.update(item.id, { recipient_role, subject_template, body_template, is_active: true })
    }
  } catch {
    /* The store shows the error. */
  }
}

watch(() => props.districtId, id => { reset(); void store.load(id) })
onMounted(() => { void store.load(props.districtId) })
</script>
