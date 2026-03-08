<template>
  <div class="p-6 max-w-4xl">
    <div class="flex items-center justify-between mb-5">
      <h1 class="text-xl font-semibold text-gray-900 dark:text-gray-100">Kalender-Integrationen</h1>
      <button
        class="flex items-center gap-1.5 text-sm bg-blue-600 text-white px-3 py-1.5 rounded hover:bg-blue-700"
        @click="openForm"
      >
        <PlusIcon class="h-4 w-4" />
        Neue Integration
      </button>
    </div>

    <!-- District filter -->
    <div class="mb-5">
      <select
        v-model="filterDistrictId"
        class="border border-gray-300 dark:border-gray-600 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100"
        @change="load"
      >
        <option value="">Alle Bezirke</option>
        <option v-for="d in districtsStore.districts" :key="d.id" :value="d.id">
          {{ d.name }}
        </option>
      </select>
    </div>

    <div v-if="loading" class="text-sm text-gray-500 dark:text-gray-400">Lade…</div>
    <div v-else-if="loadError" class="text-sm text-red-600 dark:text-red-400">{{ loadError }}</div>

    <!-- Integration list -->
    <div v-else-if="integrations.length > 0" class="space-y-3">
      <div
        v-for="item in integrations"
        :key="item.id"
        class="border border-gray-200 dark:border-gray-700 rounded-lg px-4 py-3"
      >
        <div class="flex items-start justify-between gap-4">
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="font-medium text-gray-900 dark:text-gray-100">{{ item.name }}</span>
              <span class="text-xs px-2 py-0.5 rounded-full font-medium" :class="typeBadge(item.type)">
                {{ item.type }}
              </span>
              <span
                class="text-xs px-2 py-0.5 rounded-full font-medium"
                :class="item.is_active ? 'bg-green-100 dark:bg-green-900/20 text-green-700' : 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400'"
              >
                {{ item.is_active ? 'Aktiv' : 'Inaktiv' }}
              </span>
            </div>
            <div class="mt-1 text-xs text-gray-500 dark:text-gray-400 space-y-0.5">
              <div>
                {{ districtName(item.district_id) }}
                <template v-if="item.congregation_id">
                  &nbsp;›&nbsp;{{ congregationName(item.congregation_id) }}
                </template>
              </div>
              <div>
                Sync alle {{ item.sync_interval }} Min. &nbsp;·&nbsp; {{ item.capabilities.join(', ') }}
                <template v-if="item.default_category">
                  &nbsp;·&nbsp;
                  <span class="inline-block px-1.5 py-0.5 rounded bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 text-xs font-medium">
                    Kategorie: {{ item.default_category }}
                  </span>
                </template>
              </div>
              <div v-if="item.last_synced_at">
                Letzter Sync: {{ formatDt(item.last_synced_at) }}
              </div>
              <div v-else class="text-gray-400 dark:text-gray-500">Noch nicht synchronisiert</div>
            </div>
          </div>

          <div class="flex flex-col items-end gap-2 shrink-0">
            <div class="flex items-center gap-1.5">
              <button
                class="flex items-center gap-1 text-xs px-2.5 py-1.5 border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50"
                :disabled="syncingId === item.id"
                title="Jetzt synchronisieren"
                @click="sync(item.id)"
              >
                <ArrowPathIcon class="h-3.5 w-3.5" :class="syncingId === item.id ? 'animate-spin' : ''" />
                <span>{{ syncingId === item.id ? 'Läuft…' : 'Sync' }}</span>
              </button>
              <button
                class="p-1.5 border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-500 dark:text-gray-400 hover:text-gray-800"
                title="Bearbeiten"
                @click="openEdit(item)"
              >
                <PencilSquareIcon class="h-4 w-4" />
              </button>
              <button
                class="p-1.5 border border-red-200 rounded hover:bg-red-50 dark:hover:bg-red-900/20 text-red-500 hover:text-red-700"
                title="Löschen"
                @click="confirmDelete(item)"
              >
                <TrashIcon class="h-4 w-4" />
              </button>
            </div>
            <div v-if="syncResults[item.id]" class="text-xs text-gray-600 dark:text-gray-400 text-right">
              +{{ syncResults[item.id].created }} neu &nbsp;
              ~{{ syncResults[item.id].updated }} aktual. &nbsp;
              ✕{{ syncResults[item.id].cancelled }} abgesagt
            </div>
            <div v-if="syncErrors[item.id]" class="text-xs text-red-600 dark:text-red-400 text-right max-w-[180px]">
              {{ syncErrors[item.id] }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="text-sm text-gray-500 dark:text-gray-400">Noch keine Integrationen angelegt.</div>

    <!-- Feiertage Import -->
    <div class="mt-8 border border-gray-200 dark:border-gray-700 rounded-lg">
      <button
        class="w-full flex items-center justify-between px-4 py-3 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-lg"
        @click="feiertageOpen = !feiertageOpen"
      >
        <span>Deutsche Feiertage importieren</span>
        <span class="text-gray-400 dark:text-gray-500 text-xs">{{ feiertageOpen ? '▲' : '▼' }}</span>
      </button>

      <div v-if="feiertageOpen" class="px-4 pb-4 border-t border-gray-200 dark:border-gray-700 pt-4 space-y-4">
        <p class="text-xs text-gray-500 dark:text-gray-400">
          Importiert Feiertage aus dem öffentlichen Nager.Date-Dienst als Events mit
          <code class="bg-gray-100 dark:bg-gray-700 px-1 rounded">Kategorie: Feiertag</code>.
          Der Import ist idempotent — mehrfaches Ausführen erzeugt keine Duplikate.
        </p>

        <div class="flex flex-wrap gap-3 items-end">
          <!-- District -->
          <div>
            <label class="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Bezirk</label>
            <select
              v-model="feiertageForm.districtId"
              class="border border-gray-300 dark:border-gray-600 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100"
            >
              <option value="">Bitte wählen…</option>
              <option v-for="d in districtsStore.districts" :key="d.id" :value="d.id">
                {{ d.name }}
              </option>
            </select>
          </div>

          <!-- Year -->
          <div>
            <label class="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Jahr</label>
            <input
              v-model.number="feiertageForm.year"
              type="number" min="2020" max="2035"
              class="border border-gray-300 dark:border-gray-600 rounded px-3 py-1.5 text-sm w-24 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100"
            />
          </div>

          <!-- State -->
          <div>
            <label class="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
              Bundesland <span class="text-gray-400 dark:text-gray-500 font-normal">(optional)</span>
            </label>
            <select
              v-model="feiertageForm.stateCode"
              class="border border-gray-300 dark:border-gray-600 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100"
            >
              <option value="">Nur bundesweite Feiertage</option>
              <option v-for="(name, code) in DE_STATES" :key="code" :value="code">
                {{ code }} – {{ name }}
              </option>
            </select>
          </div>

          <button
            class="flex items-center gap-1.5 bg-blue-600 text-white text-sm px-4 py-1.5 rounded hover:bg-blue-700 disabled:opacity-50"
            :disabled="!feiertageForm.districtId || feiertageImporting"
            @click="runFeiertageImport"
          >
            <ArrowDownTrayIcon class="h-4 w-4" />
            {{ feiertageImporting ? 'Importiere…' : 'Importieren' }}
          </button>
        </div>

        <div v-if="feiertageResult" class="text-sm text-green-700 bg-green-50 border border-green-200 rounded px-3 py-2">
          ✓ {{ feiertageResult.created }} neu &nbsp;·&nbsp;
          {{ feiertageResult.updated }} aktualisiert &nbsp;·&nbsp;
          {{ feiertageResult.skipped }} unverändert
        </div>
        <div v-if="feiertageError" class="text-sm text-red-600 dark:text-red-400">{{ feiertageError }}</div>
      </div>
    </div>

    <!-- Delete confirmation modal -->
    <div
      v-if="deleteTarget"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      @click.self="deleteTarget = null"
    >
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-sm p-6">
        <div class="flex items-center justify-between mb-2">
          <h2 class="text-base font-semibold text-gray-900 dark:text-gray-100">Integration löschen?</h2>
          <button class="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 dark:text-gray-500" @click="deleteTarget = null">
            <XMarkIcon class="h-5 w-5" />
          </button>
        </div>
        <p class="text-sm text-gray-600 dark:text-gray-400 mb-1">
          <span class="font-medium">{{ deleteTarget.name }}</span> wird unwiderruflich gelöscht.
        </p>
        <p class="text-sm text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 rounded px-3 py-2 mt-3">
          Alle importierten Ereignisse dieser Integration bleiben erhalten, sind aber nicht mehr mit einem Kalender verknüpft.
        </p>
        <p v-if="deleteError" class="text-sm text-red-600 dark:text-red-400 mt-2">{{ deleteError }}</p>
        <div class="flex justify-end gap-3 mt-5">
          <button
            class="text-sm px-4 py-2 border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-gray-800"
            @click="deleteTarget = null"
          >
            Abbrechen
          </button>
          <button
            class="text-sm px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
            :disabled="deleting"
            @click="executeDelete"
          >
            {{ deleting ? 'Löschen…' : 'Endgültig löschen' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Edit modal -->
    <div
      v-if="editTarget"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      @click.self="editTarget = null"
    >
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-lg p-6 overflow-y-auto max-h-[90vh]">
        <div class="flex items-center justify-between mb-1">
          <h2 class="text-base font-semibold text-gray-900 dark:text-gray-100">Integration bearbeiten</h2>
          <button class="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 dark:text-gray-500" @click="editTarget = null">
            <XMarkIcon class="h-5 w-5" />
          </button>
        </div>
        <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">Typ: <span class="font-medium">{{ editTarget.type }}</span></p>

        <div class="space-y-4">
          <!-- Name -->
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Name</label>
            <input
              v-model="editForm.name"
              type="text"
              class="w-full border border-gray-300 dark:border-gray-600 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100"
            />
          </div>

          <!-- Credentials — ICS -->
          <template v-if="editTarget.type === 'ICS'">
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Kalender-URL (.ics)</label>
              <input
                v-model="editForm.creds.url"
                type="url"
                placeholder="https://example.com/calendar.ics"
                class="w-full border border-gray-300 dark:border-gray-600 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100"
              />
            </div>
          </template>

          <!-- Credentials — CalDAV -->
          <template v-else-if="editTarget.type === 'CALDAV'">
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Server-URL</label>
              <input
                v-model="editForm.creds.url"
                type="url"
                class="w-full border border-gray-300 dark:border-gray-600 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100"
              />
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Benutzername</label>
                <input v-model="editForm.creds.username" type="text"
                  class="w-full border border-gray-300 dark:border-gray-600 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100" />
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Passwort</label>
                <input v-model="editForm.creds.password" type="password"
                  class="w-full border border-gray-300 dark:border-gray-600 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100" />
              </div>
            </div>
          </template>

          <!-- Credentials — Google / Microsoft -->
          <template v-else>
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Zugangsdaten (JSON)</label>
              <textarea
                v-model="editForm.credsJson"
                rows="4"
                placeholder='{"access_token": "...", "refresh_token": "..."}'
                class="w-full border border-gray-300 dark:border-gray-600 rounded px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100"
              />
            </div>
          </template>

          <!-- Sync interval -->
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Sync-Intervall (Minuten)</label>
            <input
              v-model.number="editForm.sync_interval"
              type="number" min="1" max="10080"
              class="w-full border border-gray-300 dark:border-gray-600 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100"
            />
          </div>

          <!-- Default category -->
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Standard-Kategorie <span class="text-gray-400 dark:text-gray-500 font-normal">(optional)</span>
            </label>
            <input
              v-model="editForm.default_category"
              type="text"
              placeholder="z.B. Feiertag"
              class="w-full border border-gray-300 dark:border-gray-600 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100"
            />
          </div>
        </div>

        <p v-if="editError" class="text-sm text-red-600 dark:text-red-400 mt-3">{{ editError }}</p>

        <div class="flex justify-end gap-3 mt-6">
          <button class="text-sm px-4 py-2 border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-gray-800" @click="editTarget = null">
            Abbrechen
          </button>
          <button
            class="text-sm px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            :disabled="editSaving"
            @click="saveEdit"
          >
            {{ editSaving ? 'Speichern…' : 'Speichern' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Create modal -->
    <div
      v-if="formOpen"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      @click.self="closeForm"
    >
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-lg p-6 overflow-y-auto max-h-[90vh]">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-base font-semibold text-gray-900 dark:text-gray-100">Neue Kalender-Integration</h2>
          <button class="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 dark:text-gray-500" @click="closeForm">
            <XMarkIcon class="h-5 w-5" />
          </button>
        </div>

        <div class="space-y-4">
          <!-- District -->
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Bezirk</label>
            <select
              v-model="form.district_id"
              class="w-full border border-gray-300 dark:border-gray-600 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100"
            >
              <option value="">Bitte wählen…</option>
              <option v-for="d in districtsStore.districts" :key="d.id" :value="d.id">
                {{ d.name }}
              </option>
            </select>
          </div>

          <!-- Congregation (optional) -->
          <div v-if="form.district_id">
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Gemeinde <span class="text-gray-400 dark:text-gray-500 font-normal">(optional — leer = Bezirksebene)</span>
            </label>
            <select
              v-model="form.congregation_id"
              class="w-full border border-gray-300 dark:border-gray-600 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100"
            >
              <option value="">Bezirksebene</option>
              <option v-for="c in formCongregations" :key="c.id" :value="c.id">
                {{ c.name }}
              </option>
            </select>
          </div>

          <!-- Name -->
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Name</label>
            <input
              v-model="form.name"
              type="text"
              placeholder="z. B. Gemeinde-Kalender Nord"
              class="w-full border border-gray-300 dark:border-gray-600 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100"
            />
          </div>

          <!-- Type -->
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Typ</label>
            <select
              v-model="form.type"
              class="w-full border border-gray-300 dark:border-gray-600 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100"
            >
              <option value="ICS">ICS (öffentliche URL)</option>
              <option value="CALDAV">CalDAV (mit Anmeldedaten)</option>
              <option value="GOOGLE">Google Calendar</option>
              <option value="MICROSOFT">Microsoft / Outlook</option>
            </select>
          </div>

          <!-- Credentials — ICS -->
          <template v-if="form.type === 'ICS'">
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Kalender-URL (.ics)</label>
              <input
                v-model="form.creds.url"
                type="url"
                placeholder="https://example.com/calendar.ics"
                class="w-full border border-gray-300 dark:border-gray-600 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100"
              />
            </div>
          </template>

          <!-- Credentials — CalDAV -->
          <template v-else-if="form.type === 'CALDAV'">
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Server-URL</label>
              <input
                v-model="form.creds.url"
                type="url"
                placeholder="https://caldav.example.com/calendar/"
                class="w-full border border-gray-300 dark:border-gray-600 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100"
              />
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Benutzername</label>
                <input
                  v-model="form.creds.username"
                  type="text"
                  class="w-full border border-gray-300 dark:border-gray-600 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100"
                />
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Passwort</label>
                <input
                  v-model="form.creds.password"
                  type="password"
                  class="w-full border border-gray-300 dark:border-gray-600 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100"
                />
              </div>
            </div>
          </template>

          <!-- Credentials — Google / Microsoft -->
          <template v-else>
            <div class="rounded bg-amber-50 dark:bg-amber-900/20 border border-amber-200 px-3 py-2 text-xs text-amber-700 dark:text-amber-300">
              OAuth-Flow für {{ form.type === 'GOOGLE' ? 'Google' : 'Microsoft' }} ist noch nicht implementiert.
              Du kannst die Zugangsdaten als JSON hinterlegen (für manuelle Token-Verwaltung).
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Zugangsdaten (JSON)</label>
              <textarea
                v-model="form.credsJson"
                rows="4"
                placeholder='{"access_token": "...", "refresh_token": "..."}'
                class="w-full border border-gray-300 dark:border-gray-600 rounded px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100"
              />
            </div>
          </template>

          <!-- Sync interval -->
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Sync-Intervall (Minuten)
            </label>
            <input
              v-model.number="form.sync_interval"
              type="number"
              min="1"
              max="10080"
              class="w-full border border-gray-300 dark:border-gray-600 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100"
            />
          </div>

          <!-- Capabilities -->
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Fähigkeiten</label>
            <div class="flex gap-4">
              <label v-for="cap in ALL_CAPABILITIES" :key="cap" class="flex items-center gap-1.5 text-sm">
                <input
                  type="checkbox"
                  :value="cap"
                  v-model="form.capabilities"
                  class="rounded border-gray-300 dark:border-gray-600 text-blue-600 focus:ring-blue-500"
                />
                {{ cap }}
              </label>
            </div>
          </div>

          <!-- Default category -->
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Standard-Kategorie <span class="text-gray-400 dark:text-gray-500 font-normal">(optional)</span>
            </label>
            <input
              v-model="form.default_category"
              type="text"
              placeholder="z.B. Feiertag"
              class="w-full border border-gray-300 dark:border-gray-600 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100"
            />
          </div>
        </div>

        <p v-if="formError" class="text-sm text-red-600 dark:text-red-400 mt-3">{{ formError }}</p>

        <div class="flex justify-end gap-3 mt-6">
          <button
            class="text-sm px-4 py-2 border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-gray-800"
            @click="closeForm"
          >
            Abbrechen
          </button>
          <button
            class="text-sm px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            :disabled="!formValid || saving"
            @click="submit"
          >
            {{ saving ? 'Speichern…' : 'Anlegen' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ArrowDownTrayIcon, ArrowPathIcon, PencilSquareIcon, PlusIcon, TrashIcon, XMarkIcon } from '@heroicons/vue/24/outline'
import { useDistrictsStore } from '@/stores/districts'
import {
  importFeiertage,
  listCongregations,
  type CongregationResponse,
  type FeiertageImportResult,
} from '@/api/districts'
import {
  createIntegration,
  deleteIntegration,
  listIntegrations,
  triggerSync,
  updateIntegration,
  type CalendarCapability,
  type CalendarIntegrationResponse,
  type CalendarType,
  type SyncResult,
} from '@/api/calendarIntegrations'

const DE_STATES: Record<string, string> = {
  BB: 'Brandenburg', BE: 'Berlin', BW: 'Baden-Württemberg', BY: 'Bayern',
  HB: 'Bremen', HE: 'Hessen', HH: 'Hamburg', MV: 'Mecklenburg-Vorpommern',
  NI: 'Niedersachsen', NW: 'Nordrhein-Westfalen', RP: 'Rheinland-Pfalz',
  SH: 'Schleswig-Holstein', SL: 'Saarland', SN: 'Sachsen', ST: 'Sachsen-Anhalt',
  TH: 'Thüringen',
}

const districtsStore = useDistrictsStore()

const integrations = ref<CalendarIntegrationResponse[]>([])
const loading = ref(false)
const loadError = ref('')
const filterDistrictId = ref('')

const syncingId = ref<string | null>(null)
const syncResults = reactive<Record<string, SyncResult>>({})
const syncErrors = reactive<Record<string, string>>({})

const ALL_CAPABILITIES: CalendarCapability[] = ['READ', 'WRITE', 'WEBHOOK']

onMounted(async () => {
  if (districtsStore.districts.length === 0) await districtsStore.fetchDistricts()
  const all = await Promise.all(districtsStore.districts.map((d) => listCongregations(d.id)))
  allCongregations.value = all.flat()
  await load()
})

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const res = await listIntegrations(filterDistrictId.value || undefined)
    integrations.value = res.items
  } catch (e) {
    loadError.value = e instanceof Error ? e.message : 'Fehler beim Laden'
  } finally {
    loading.value = false
  }
}

async function sync(id: string) {
  syncingId.value = id
  delete syncErrors[id]
  try {
    syncResults[id] = await triggerSync(id)
    // Refresh last_synced_at
    await load()
  } catch (e) {
    syncErrors[id] = e instanceof Error ? e.message : 'Sync fehlgeschlagen'
  } finally {
    syncingId.value = null
  }
}

function districtName(id: string): string {
  return districtsStore.districts.find((d) => d.id === id)?.name ?? id
}

const allCongregations = ref<CongregationResponse[]>([])

function congregationName(id: string): string {
  return allCongregations.value.find((c) => c.id === id)?.name ?? id
}

function formatDt(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleString('de-DE', { dateStyle: 'short', timeStyle: 'short' })
}

function typeBadge(type: CalendarType): string {
  const map: Record<CalendarType, string> = {
    ICS: 'bg-blue-100 text-blue-700',
    CALDAV: 'bg-purple-100 text-purple-700',
    GOOGLE: 'bg-red-100 text-red-700',
    MICROSOFT: 'bg-sky-100 text-sky-700',
  }
  return map[type]
}

// --- Delete ---
const deleteTarget = ref<CalendarIntegrationResponse | null>(null)
const deleting = ref(false)
const deleteError = ref('')

function confirmDelete(item: CalendarIntegrationResponse) {
  deleteTarget.value = item
  deleteError.value = ''
}

async function executeDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  deleteError.value = ''
  try {
    await deleteIntegration(deleteTarget.value.id)
    integrations.value = integrations.value.filter((i) => i.id !== deleteTarget.value!.id)
    deleteTarget.value = null
  } catch (e) {
    deleteError.value = e instanceof Error ? e.message : 'Fehler beim Löschen'
  } finally {
    deleting.value = false
  }
}

// --- Edit ---
const editTarget = ref<CalendarIntegrationResponse | null>(null)
const editSaving = ref(false)
const editError = ref('')

const editForm = reactive({
  name: '',
  creds: { url: '', username: '', password: '' },
  credsJson: '',
  sync_interval: 60,
  default_category: '',
})

function openEdit(item: CalendarIntegrationResponse) {
  editTarget.value = item
  editError.value = ''
  editForm.name = item.name
  editForm.creds = { url: '', username: '', password: '' }
  editForm.credsJson = ''
  editForm.sync_interval = item.sync_interval
  editForm.default_category = item.default_category ?? ''
}

function buildEditCredentials(): Record<string, string> | undefined {
  if (!editTarget.value) return undefined
  const type = editTarget.value.type
  if (type === 'ICS') return editForm.creds.url.trim() ? { url: editForm.creds.url.trim() } : undefined
  if (type === 'CALDAV') return editForm.creds.url.trim() ? { url: editForm.creds.url.trim(), username: editForm.creds.username.trim(), password: editForm.creds.password } : undefined
  try { return editForm.credsJson.trim() ? JSON.parse(editForm.credsJson) : undefined } catch { return undefined }
}

async function saveEdit() {
  if (!editTarget.value) return
  editSaving.value = true
  editError.value = ''
  try {
    const payload: Parameters<typeof updateIntegration>[1] = {
      name: editForm.name.trim() || undefined,
      sync_interval: editForm.sync_interval,
      default_category: editForm.default_category.trim() || null,
    }
    const creds = buildEditCredentials()
    if (creds) payload.credentials = creds

    const updated = await updateIntegration(editTarget.value.id, payload)
    const idx = integrations.value.findIndex((i) => i.id === updated.id)
    if (idx !== -1) integrations.value[idx] = updated
    editTarget.value = null
  } catch (e) {
    editError.value = e instanceof Error ? e.message : 'Fehler beim Speichern'
  } finally {
    editSaving.value = false
  }
}

// --- Form ---
const formOpen = ref(false)
const saving = ref(false)
const formError = ref('')
const formCongregations = ref<CongregationResponse[]>([])

const form = reactive({
  district_id: '',
  congregation_id: '',
  name: '',
  type: 'ICS' as CalendarType,
  creds: { url: '', username: '', password: '' },
  credsJson: '',
  sync_interval: 60,
  capabilities: ['READ'] as CalendarCapability[],
  default_category: '',
})

watch(() => form.district_id, async (id) => {
  form.congregation_id = ''
  try {
    formCongregations.value = id ? await listCongregations(id) : []
  } catch {
    formCongregations.value = []
  }
})

const formValid = computed(() => {
  if (!form.district_id || !form.name.trim()) return false
  if (form.type === 'ICS') return !!form.creds.url.trim()
  if (form.type === 'CALDAV') return !!form.creds.url.trim() && !!form.creds.username.trim()
  // GOOGLE / MICROSOFT
  try { JSON.parse(form.credsJson); return true } catch { return false }
})

function openForm() {
  form.district_id = filterDistrictId.value
  form.congregation_id = ''
  formCongregations.value = []
  form.name = ''
  form.type = 'ICS'
  form.creds = { url: '', username: '', password: '' }
  form.credsJson = ''
  form.sync_interval = 60
  form.capabilities = ['READ']
  form.default_category = ''
  formError.value = ''
  formOpen.value = true
  // Preload congregations when a filter district is already set
  // (watch won't fire if form.district_id didn't change)
  if (filterDistrictId.value) {
    listCongregations(filterDistrictId.value).then((cs) => {
      formCongregations.value = cs
    }).catch(() => {})
  }
}

function closeForm() {
  formOpen.value = false
}

function buildCredentials(): Record<string, string> {
  if (form.type === 'ICS') return { url: form.creds.url.trim() }
  if (form.type === 'CALDAV') {
    return {
      url: form.creds.url.trim(),
      username: form.creds.username.trim(),
      password: form.creds.password,
    }
  }
  return JSON.parse(form.credsJson)
}

async function submit() {
  saving.value = true
  formError.value = ''
  try {
    const created = await createIntegration({
      district_id: form.district_id,
      congregation_id: form.congregation_id || null,
      name: form.name.trim(),
      type: form.type,
      credentials: buildCredentials(),
      sync_interval: form.sync_interval,
      capabilities: form.capabilities,
      default_category: form.default_category.trim() || null,
    })
    integrations.value.unshift(created)
    closeForm()
  } catch (e) {
    formError.value = e instanceof Error ? e.message : 'Fehler beim Anlegen'
  } finally {
    saving.value = false
  }
}

// --- Feiertage Import ---
const feiertageOpen = ref(false)
const feiertageImporting = ref(false)
const feiertageResult = ref<FeiertageImportResult | null>(null)
const feiertageError = ref('')

const feiertageForm = reactive({
  districtId: '',
  year: new Date().getFullYear(),
  stateCode: '',
})

async function runFeiertageImport() {
  if (!feiertageForm.districtId) return
  feiertageImporting.value = true
  feiertageResult.value = null
  feiertageError.value = ''
  try {
    feiertageResult.value = await importFeiertage(
      feiertageForm.districtId,
      feiertageForm.year,
      feiertageForm.stateCode || null,
    )
  } catch (e) {
    feiertageError.value = e instanceof Error ? e.message : 'Import fehlgeschlagen'
  } finally {
    feiertageImporting.value = false
  }
}
</script>
