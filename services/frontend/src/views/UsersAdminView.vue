<!-- SPDX-FileCopyrightText: 2026 Stephan Strittmatter
     SPDX-License-Identifier: AGPL-3.0-only -->

<template>
  <main class="p-6 max-w-6xl mx-auto space-y-6">
    <header class="space-y-1">
      <h1 class="text-xl font-semibold text-gray-900 dark:text-gray-100">Benutzer</h1>
      <p class="text-sm text-gray-500 dark:text-gray-400">
        Rollen je Bezirk und Gemeinde vergeben. Eine Person kann in mehreren Einheiten
        unterschiedliche Rollen haben.
      </p>
    </header>

    <section
      aria-labelledby="own-access"
      class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4"
    >
      <h2 id="own-access" class="text-sm font-semibold text-gray-900 dark:text-gray-100">Deine Zugänge</h2>
      <p v-if="auth.isSuperadmin" class="mt-2 text-sm text-amber-700">
        Superadmin: Zugriff auf alle Bezirke und Gemeinden.
      </p>
      <ul v-if="auth.memberships.length" class="mt-2 flex flex-wrap gap-2">
        <li
          v-for="m in auth.memberships"
          :key="`${m.scope_type}:${m.scope_id}`"
          class="rounded-full bg-gray-100 dark:bg-gray-800 px-3 py-1 text-xs text-gray-700 dark:text-gray-300"
        >
          {{ roleLabel(m.role) }} · {{ unitName(m.scope_type, m.scope_id) }}
        </li>
      </ul>
      <p v-else-if="!auth.isSuperadmin" class="mt-2 text-sm text-gray-500 dark:text-gray-400">
        Keine Zuordnungen.
      </p>
    </section>

    <p v-if="loading" class="text-sm text-gray-500 dark:text-gray-400">Lade Benutzer…</p>
    <p v-else-if="loadError" role="alert" class="text-sm text-red-600">{{ loadError }}</p>

    <template v-else>
      <label class="block max-w-sm text-sm text-gray-700 dark:text-gray-300">
        Suche
        <input
          v-model="query"
          type="search"
          class="form-input mt-1 w-full"
          placeholder="Name oder E-Mail"
        >
      </label>

      <p v-if="filteredUsers.length === 0" class="text-sm text-gray-500 dark:text-gray-400">
        Keine Benutzer gefunden.
      </p>

      <ul v-else class="space-y-3">
        <li
          v-for="user in filteredUsers"
          :key="user.sub"
          class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 space-y-3"
          :data-testid="`user-${user.sub}`"
        >
          <div class="flex flex-wrap items-start justify-between gap-2">
            <div>
              <p class="font-medium text-gray-900 dark:text-gray-100">
                {{ user.name || user.username }}
                <span
                  v-if="user.is_superadmin"
                  class="ml-2 inline-flex items-center rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-amber-700"
                >
                  Superadmin
                </span>
              </p>
              <p class="text-sm text-gray-500 dark:text-gray-400">{{ user.email }}</p>
            </div>
            <button
              v-if="user.is_superadmin !== null && auth.isSuperadmin"
              type="button"
              class="text-sm px-3 py-1.5 rounded-md border"
              :class="user.is_superadmin
                ? 'border-red-300 text-red-700 hover:bg-red-50'
                : 'border-amber-300 text-amber-700 hover:bg-amber-50'"
              :disabled="busy === user.sub"
              @click="toggleSuperadmin(user)"
            >
              {{ user.is_superadmin ? 'Superadmin entziehen' : 'Zum Superadmin ernennen' }}
            </button>
          </div>

          <ul v-if="user.memberships.length" class="flex flex-wrap gap-2">
            <li
              v-for="m in user.memberships"
              :key="m.id"
              class="inline-flex items-center gap-1 rounded-full bg-blue-50 dark:bg-blue-900/30 pl-3 pr-1 py-0.5 text-xs text-blue-800 dark:text-blue-200"
            >
              {{ roleLabel(m.role) }} · {{ m.scope_name ?? unitName(m.scope_type, m.scope_id) }}
              <button
                v-if="canRemove(m)"
                type="button"
                class="ml-1 rounded-full px-1.5 hover:bg-blue-100 dark:hover:bg-blue-800"
                :aria-label="`${roleLabel(m.role)} in ${m.scope_name ?? 'Einheit'} entfernen`"
                :disabled="busy === user.sub"
                @click="remove(user, m)"
              >
                ×
              </button>
            </li>
          </ul>
          <p v-else class="text-sm text-gray-500 dark:text-gray-400">Keine Zuordnungen in deinen Einheiten.</p>

          <form
            v-if="units.length"
            class="flex flex-wrap items-end gap-2"
            @submit.prevent="assign(user)"
          >
            <label class="text-xs text-gray-600 dark:text-gray-400">
              Einheit
              <select
                v-model="draft(user.sub).unitKey"
                class="form-input mt-1 block"
                :aria-label="`Einheit für ${user.email}`"
                @change="dropUnfitRole(user.sub)"
              >
                <option value="" disabled>Einheit wählen</option>
                <option v-for="unit in units" :key="unit.key" :value="unit.key">{{ unit.label }}</option>
              </select>
            </label>
            <label class="text-xs text-gray-600 dark:text-gray-400">
              Rolle
              <select
                v-model="draft(user.sub).role"
                class="form-input mt-1 block"
                :aria-label="`Rolle für ${user.email}`"
                :disabled="!draftUnit(user.sub)"
              >
                <option value="" disabled>Rolle wählen</option>
                <option v-for="role in draftRoles(user.sub)" :key="role" :value="role">{{ roleLabel(role) }}</option>
              </select>
            </label>
            <button
              type="submit"
              class="btn-primary text-sm"
              :disabled="busy === user.sub || !draftUnit(user.sub) || !draftRole(user.sub)"
            >
              Zuordnen
            </button>
          </form>
        </li>
      </ul>
    </template>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { listCongregations, listDistricts } from '../api/districts'
import { ApiError, userMessage } from '../api/errors'
import {
  assignMembership,
  listUsers,
  removeMembership,
  setSuperadmin,
  type AdminMembership,
  type AdminUser,
  type MembershipRole,
  type ScopeType,
} from '../api/users'
import { useConfirm } from '../composables/useConfirm'
import { useAuthStore } from '../stores/auth'
import { useToastStore } from '../stores/toast'
import {
  ROLE_LABELS,
  assignableRoles,
  managementLevel,
  mayManage,
  type Unit,
} from '../utils/membershipPolicy'

interface UnitOption extends Unit {
  key: string
  label: string
  name: string
  level: MembershipRole
}

interface Draft {
  unitKey: string
  role: MembershipRole | ''
}

const auth = useAuthStore()
const toast = useToastStore()
const confirm = useConfirm()

const users = ref<AdminUser[]>([])
const units = ref<UnitOption[]>([])
const names = ref(new Map<string, string>())
const loading = ref(true)
const loadError = ref<string | null>(null)
const busy = ref<string | null>(null)
const query = ref('')
const drafts = reactive<Record<string, Draft>>({})

const filteredUsers = computed(() => {
  const needle = query.value.trim().toLowerCase()
  if (!needle) return users.value
  return users.value.filter((user) =>
    [user.name, user.username, user.email].some((value) => value?.toLowerCase().includes(needle)),
  )
})

function unitKey(scopeType: ScopeType, scopeId: string): string {
  return `${scopeType}:${scopeId}`
}

function roleLabel(role: string): string {
  return ROLE_LABELS[role as MembershipRole] ?? role
}

function unitName(scopeType: ScopeType, scopeId: string): string {
  return names.value.get(unitKey(scopeType, scopeId)) ?? (scopeType === 'DISTRICT' ? 'Bezirk' : 'Gemeinde')
}

function draft(sub: string): Draft {
  drafts[sub] ??= { unitKey: '', role: '' }
  return drafts[sub]
}

function draftUnit(sub: string): UnitOption | undefined {
  return units.value.find((unit) => unit.key === draft(sub).unitKey)
}

function draftRoles(sub: string): MembershipRole[] {
  const unit = draftUnit(sub)
  return unit ? assignableRoles(unit.level, unit.scopeType) : []
}

/** The drafted role, provided it still fits the drafted unit. */
function draftRole(sub: string): MembershipRole | '' {
  const role = draft(sub).role
  return role && draftRoles(sub).includes(role) ? role : ''
}

function dropUnfitRole(sub: string) {
  draft(sub).role = draftRole(sub)
}

function levelFor(m: AdminMembership): MembershipRole | null {
  return managementLevel(auth.memberships, auth.isSuperadmin, {
    scopeType: m.scope_type,
    scopeId: m.scope_id,
    districtId: m.district_id,
  })
}

function canRemove(m: AdminMembership): boolean {
  return mayManage(levelFor(m), m.role)
}

function replaceUser(updated: AdminUser) {
  users.value = users.value.map((user) => (user.sub === updated.sub ? updated : user))
}

function unitOption(unit: Unit, name: string): UnitOption | null {
  const level = managementLevel(auth.memberships, auth.isSuperadmin, unit)
  if (!level) return null
  const kind = unit.scopeType === 'DISTRICT' ? 'Bezirk' : 'Gemeinde'
  return { ...unit, key: unitKey(unit.scopeType, unit.scopeId), name, label: `${kind} ${name}`, level }
}

/**
 * Units the caller manages. The district listing only covers district-scoped
 * access, so congregations managed directly are taken from the memberships
 * the user list shows (only managed units carry a name and district there).
 */
async function loadUnits(loadedUsers: AdminUser[]) {
  const districts = await listDistricts()
  const congregations = (
    await Promise.all(districts.map((district) => listCongregations(district.id)))
  ).flat()
  const found = new Map<string, { unit: Unit; name: string }>()
  for (const district of districts) {
    found.set(unitKey('DISTRICT', district.id), {
      unit: { scopeType: 'DISTRICT', scopeId: district.id, districtId: district.id },
      name: district.name,
    })
  }
  for (const congregation of congregations) {
    found.set(unitKey('CONGREGATION', congregation.id), {
      unit: { scopeType: 'CONGREGATION', scopeId: congregation.id, districtId: congregation.district_id },
      name: congregation.name,
    })
  }
  for (const m of loadedUsers.flatMap((user) => user.memberships)) {
    const key = unitKey(m.scope_type, m.scope_id)
    if (found.has(key) || !m.scope_name) continue
    found.set(key, {
      unit: { scopeType: m.scope_type, scopeId: m.scope_id, districtId: m.district_id },
      name: m.scope_name,
    })
  }
  names.value = new Map([...found].map(([key, { name }]) => [key, name]))
  units.value = [...found.values()]
    .map(({ unit, name }) => unitOption(unit, name))
    .filter((option): option is UnitOption => option !== null)
}

async function load() {
  loading.value = true
  loadError.value = null
  try {
    const loadedUsers = await listUsers()
    await loadUnits(loadedUsers)
    users.value = loadedUsers
  } catch (cause) {
    loadError.value =
      cause instanceof ApiError && cause.status === 403
        ? 'Du verwaltest keine Bezirke oder Gemeinden.'
        : userMessage(cause, 'Benutzer konnten nicht geladen werden')
  } finally {
    loading.value = false
  }
}

/** After changing the own access the screen must reflect what is left of it. */
async function refreshOwnAccess() {
  await auth.refreshCurrentUserFlags()
  await load()
}

async function assign(user: AdminUser) {
  const unit = draftUnit(user.sub)
  const role = draftRole(user.sub)
  if (!unit || !role) return
  busy.value = user.sub
  try {
    replaceUser(await assignMembership(user.sub, { scope_type: unit.scopeType, scope_id: unit.scopeId, role }))
    drafts[user.sub] = { unitKey: '', role: '' }
    toast.success(`${roleLabel(role)} in ${unit.label} zugeordnet`)
    if (user.sub === auth.user?.sub) await refreshOwnAccess()
  } catch (cause) {
    toast.error(userMessage(cause, 'Zuordnung fehlgeschlagen'))
  } finally {
    busy.value = null
  }
}

async function remove(user: AdminUser, m: AdminMembership) {
  const unit = m.scope_name ?? unitName(m.scope_type, m.scope_id)
  const confirmed = await confirm({
    title: 'Zuordnung entfernen?',
    message: `${user.name || user.email} verliert die Rolle ${roleLabel(m.role)} in ${unit}. Andere Zuordnungen bleiben erhalten.`,
    confirmText: 'Entfernen',
    variant: 'danger',
  })
  if (!confirmed) return
  busy.value = user.sub
  try {
    await removeMembership(user.sub, m.id)
    replaceUser({ ...user, memberships: user.memberships.filter((other) => other.id !== m.id) })
    toast.success('Zuordnung entfernt')
    if (user.sub === auth.user?.sub) await refreshOwnAccess()
  } catch (cause) {
    toast.error(userMessage(cause, 'Zuordnung konnte nicht entfernt werden'))
  } finally {
    busy.value = null
  }
}

async function toggleSuperadmin(user: AdminUser) {
  const grant = !user.is_superadmin
  const self = user.sub === auth.user?.sub
  const confirmed = await confirm(
    grant
      ? {
          title: 'Zum Superadmin ernennen?',
          message: `${user.name || user.email} erhält Zugriff auf alle Bezirke und Gemeinden und kann selbst Superadmins ernennen.`,
          confirmText: 'Ernennen',
          variant: 'warning',
        }
      : {
          title: 'Superadmin entziehen?',
          message: self
            ? 'Du entziehst dir selbst den Superadmin-Status und behältst nur deine Zuordnungen.'
            : `${user.name || user.email} behält danach nur die eigenen Zuordnungen.`,
          confirmText: 'Entziehen',
          variant: 'danger',
        },
  )
  if (!confirmed) return
  busy.value = user.sub
  try {
    replaceUser(await setSuperadmin(user.sub, grant))
    toast.success(grant ? 'Superadmin ernannt' : 'Superadmin-Status entzogen')
    if (self) await refreshOwnAccess()
  } catch (cause) {
    toast.error(userMessage(cause, 'Superadmin-Status konnte nicht geändert werden'))
  } finally {
    busy.value = null
  }
}

onMounted(load)
</script>
