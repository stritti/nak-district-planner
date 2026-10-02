export type HelpRole = 'guest' | 'viewer' | 'planner'
export type HelpContext = 'login' | 'registration' | 'events' | 'matrix'

export interface HelpEntry {
  readonly help_id: string
  readonly roles: readonly HelpRole[]
  readonly contexts: readonly HelpContext[]
  readonly title: string
  readonly description: string
  readonly steps: readonly string[]
  readonly links?: readonly { readonly label: string; readonly to: string }[]
}

/** Content remains separate from presentation and authorization. Links must be trusted app routes. */
export const HELP_CATALOG: readonly HelpEntry[] = [
  {
    help_id: 'guest-sign-in',
    roles: ['guest'],
    contexts: ['login'],
    title: 'Anmelden und Zugang erhalten',
    description: 'Melde dich mit deinem bestehenden Konto an oder beantrage einen Zugang.',
    steps: ['Wähle „Mit Single Sign-on anmelden“, wenn du bereits einen Zugang hast.', 'Ohne Konto kannst du dich zunächst registrieren.', 'Nach der Registrierung prüft die Bezirksadministration deine Anfrage.'],
    links: [{ label: 'Zur Registrierung', to: '/register' }],
  },
  {
    help_id: 'guest-registration',
    roles: ['guest'],
    contexts: ['registration'],
    title: 'Registrierung',
    description: 'Mit diesen Angaben kann dein Bezirk deinen Zugang prüfen.',
    steps: ['Wähle deinen Bezirk und gib deine Kontaktdaten an.', 'Ergänze optional Gemeinde und weitere Angaben.', 'Reiche die Registrierung ein. Die Freischaltung erfolgt nach Prüfung.'],
    links: [{ label: 'Zur Anmeldung', to: '/login' }],
  },
  {
    help_id: 'viewer-events',
    roles: ['viewer'],
    contexts: ['events'],
    title: 'Ereignisse finden',
    description: 'Die Filter helfen dir, relevante Ereignisse schnell zu finden.',
    steps: ['Wähle Bezirk und gegebenenfalls Gemeinde.', 'Grenze Ereignisse über Zeitraum und Typ ein.', 'Wechsle zwischen Listen-, Wochen- und Monatsansicht.'],
  },
  {
    help_id: 'planner-events',
    roles: ['planner'],
    contexts: ['events'],
    title: 'Ereignisse planen',
    description: 'Behalte Ereignisse, Zuordnungen und deren Status im Blick.',
    steps: ['Wähle den gewünschten Bezirk und Zeitraum.', 'Öffne ein Ereignis, um seine Zuordnung zu prüfen oder zu bearbeiten.', 'Kontrolliere den Planungs- und Freigabestatus.'],
  },
  {
    help_id: 'planner-matrix',
    roles: ['planner'],
    contexts: ['matrix'],
    title: 'Mit der Dienstplan-Matrix arbeiten',
    description: 'Plane Dienste nach Bezirk, Gemeinde und Zeitraum.',
    steps: ['Wähle Bezirk und Zeitraum in der Filterleiste.', 'Öffne eine Matrixzelle, um die Besetzung zu bearbeiten.', 'Prüfe die Zuordnungen vor der Monatsfreigabe.'],
  },
]

export interface HelpAccess {
  readonly authenticated: boolean
  readonly memberships: readonly { readonly role: string }[]
  readonly isSuperadmin?: boolean
  readonly accessStatus?: string
}

/** Fail closed: unrecognised and not-yet-loaded memberships expose no role-specific guidance. */
export function resolveHelpRole(access: HelpAccess): HelpRole | null {
  if (!access.authenticated) return 'guest'
  if (access.accessStatus === 'PENDING_APPROVAL') return null
  if (access.isSuperadmin || access.memberships.some(({ role }) => ['DISTRICT_ADMIN', 'PLANNER', 'CONGREGATION_ADMIN'].includes(role.toUpperCase()))) return 'planner'
  if (access.memberships.some(({ role }) => ['VIEWER', 'READ_ONLY'].includes(role.toUpperCase()))) return 'viewer'
  return null
}

export function resolveHelp(context: HelpContext, access: HelpAccess): readonly HelpEntry[] {
  const role = resolveHelpRole(access)
  if (!role) return []
  return HELP_CATALOG.filter((entry) => entry.roles.includes(role) && entry.contexts.includes(context))
}
