// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import * as registrationsApi from '../api/registrations'
import { useAuthStore } from '../stores/auth'
import RegistrationView from './RegistrationView.vue'

vi.mock('../api/registrations')
vi.mock('vue-router', async (importOriginal) => ({
  ...(await importOriginal<typeof import('vue-router')>()),
  useRouter: () => ({}),
}))

const getAuthorizationUrl = vi.hoisted(() => vi.fn())
vi.mock('../composables/useOIDC', () => ({ useOIDC: () => ({ getAuthorizationUrl }) }))

const districts: registrationsApi.PublicDistrictInfo[] = [
  { id: 'district-1', name: 'Bezirk Eins' },
  { id: 'district-2', name: 'Bezirk Zwei' },
]
const congregations: registrationsApi.PublicCongregationInfo[] = [
  { id: 'cong-1', name: 'Gemeinde A' },
  { id: 'cong-2', name: 'Gemeinde B' },
]

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason: Error) => void
  const promise = new Promise<T>((fulfill, fail) => {
    resolve = fulfill
    reject = fail
  })
  return { promise, resolve, reject }
}

function mountView() {
  return mount(RegistrationView, {
    global: {
      plugins: [createPinia()],
      stubs: {
        ContextualHelp: true,
        RouterLink: { template: '<a><slot /></a>' },
      },
    },
  })
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  vi.mocked(registrationsApi.listDistrictsPublic).mockResolvedValue(districts)
  vi.mocked(registrationsApi.listCongregationsPublic).mockResolvedValue(congregations)
})

describe('RegistrationView', () => {
  it('loads public districts and keeps submission disabled until a district is selected', async () => {
    const wrapper = mountView()
    await flushPromises()

    expect(registrationsApi.listDistrictsPublic).toHaveBeenCalledOnce()
    expect(wrapper.text()).toContain('Bezirk Eins')
    expect(wrapper.get('button[type="submit"]').attributes('disabled')).toBeDefined()
  })

  it('loads congregations after district selection and clears them when the district is reset', async () => {
    const wrapper = mountView()
    await flushPromises()
    const districtSelect = wrapper.findAll('select')[0]

    await districtSelect.setValue('district-1')
    await flushPromises()

    expect(registrationsApi.listCongregationsPublic).toHaveBeenCalledWith('district-1')
    expect(wrapper.text()).toContain('Gemeinde A')

    await districtSelect.setValue('')
    await flushPromises()
    expect(wrapper.text()).not.toContain('Gemeinde A')
  })

  it('ignores a late response from a district that is no longer selected', async () => {
    const first = deferred<registrationsApi.PublicCongregationInfo[]>()
    const second = deferred<registrationsApi.PublicCongregationInfo[]>()
    vi.mocked(registrationsApi.listCongregationsPublic).mockImplementation((id) =>
      id === 'district-1' ? first.promise : second.promise,
    )
    const wrapper = mountView()
    await flushPromises()
    const districtSelect = wrapper.findAll('select')[0]

    await districtSelect.setValue('district-1')
    await districtSelect.setValue('district-2')
    second.resolve([{ id: 'cong-b', name: 'Gemeinde Bezirk Zwei' }])
    await flushPromises()
    expect(wrapper.text()).toContain('Gemeinde Bezirk Zwei')

    first.resolve([{ id: 'cong-a', name: 'Gemeinde Bezirk Eins' }])
    await flushPromises()
    expect(wrapper.text()).toContain('Gemeinde Bezirk Zwei')
    expect(wrapper.text()).not.toContain('Gemeinde Bezirk Eins')
  })

  it('keeps the congregation list empty when a cancelled request finishes after reset', async () => {
    const previous = deferred<registrationsApi.PublicCongregationInfo[]>()
    vi.mocked(registrationsApi.listCongregationsPublic).mockReturnValue(previous.promise)
    const wrapper = mountView()
    await flushPromises()
    const districtSelect = wrapper.findAll('select')[0]

    await districtSelect.setValue('district-1')
    await districtSelect.setValue('')
    previous.resolve([{ id: 'stale', name: 'Veraltete Gemeinde' }])
    await flushPromises()
    expect(wrapper.text()).not.toContain('Veraltete Gemeinde')
    expect(wrapper.find('option[value="stale"]').exists()).toBe(false)
  })

  it('does not clear current congregations when an obsolete request rejects', async () => {
    const first = deferred<registrationsApi.PublicCongregationInfo[]>()
    vi.mocked(registrationsApi.listCongregationsPublic).mockImplementation((id) =>
      id === 'district-1' ? first.promise : Promise.resolve([{ id: 'second', name: 'Aktuelle Gemeinde' }]),
    )
    const wrapper = mountView()
    await flushPromises()
    const districtSelect = wrapper.findAll('select')[0]

    await districtSelect.setValue('district-1')
    await districtSelect.setValue('district-2')
    await flushPromises()
    first.reject(new Error('obsolete request'))
    await flushPromises()
    expect(wrapper.text()).toContain('Aktuelle Gemeinde')
  })

  it('fails closed to an empty congregation list when loading congregations fails', async () => {
    vi.mocked(registrationsApi.listCongregationsPublic).mockRejectedValue(new Error('offline'))
    const wrapper = mountView()
    await flushPromises()

    await wrapper.findAll('select')[0].setValue('district-1')
    await flushPromises()

    expect(wrapper.text()).not.toContain('Gemeinde A')
  })

  it('shows a public district load error', async () => {
    vi.mocked(registrationsApi.listDistrictsPublic).mockRejectedValue(new Error('offline'))
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('Bezirke konnten nicht geladen werden')
  })

  it('submits the normalized registration payload and shows the success state', async () => {
    vi.mocked(registrationsApi.submitRegistration).mockResolvedValue({} as registrationsApi.RegistrationResponse)
    const wrapper = mountView()
    await flushPromises()

    const selects = wrapper.findAll('select')
    await selects[0].setValue('district-1')
    await flushPromises()
    await wrapper.get('input[type="text"]').setValue('Erika Beispiel')
    await wrapper.get('input[type="email"]').setValue('erika@example.org')
    await wrapper.get('input[type="tel"]').setValue('+49 1234')
    await wrapper.get('textarea').setValue('Bitte freischalten')
    await wrapper.findAll('select')[1].setValue('Pr.')
    await wrapper.findAll('select')[2].setValue('cong-1')
    await wrapper.findAll('select')[3].setValue('Gemeindevorsteher')

    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(registrationsApi.submitRegistration).toHaveBeenCalledWith('district-1', {
      name: 'Erika Beispiel',
      email: 'erika@example.org',
      rank: 'Pr.',
      congregation_id: 'cong-1',
      special_role: 'Gemeindevorsteher',
      phone: '+49 1234',
      notes: 'Bitte freischalten',
    }, null)
    expect(wrapper.text()).toContain('Registrierung eingereicht')
  })

  it('normalizes empty optional fields to null', async () => {
    vi.mocked(registrationsApi.submitRegistration).mockResolvedValue({} as registrationsApi.RegistrationResponse)
    const wrapper = mountView()
    await flushPromises()

    await wrapper.findAll('select')[0].setValue('district-1')
    await wrapper.get('input[type="text"]').setValue('Erika Beispiel')
    await wrapper.get('input[type="email"]').setValue('erika@example.org')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(registrationsApi.submitRegistration).toHaveBeenCalledWith('district-1', expect.objectContaining({
      rank: null,
      congregation_id: null,
      special_role: null,
      phone: null,
      notes: null,
    }), null)
  })

  it('shows Error and non-Error submit failures and re-enables the form', async () => {
    const wrapper = mountView()
    await flushPromises()
    await wrapper.findAll('select')[0].setValue('district-1')
    await wrapper.get('input[type="text"]').setValue('Erika Beispiel')
    await wrapper.get('input[type="email"]').setValue('erika@example.org')

    vi.mocked(registrationsApi.submitRegistration).mockRejectedValueOnce(new Error('Registrierung abgelehnt'))
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('Registrierung abgelehnt')
    expect(wrapper.get('button[type="submit"]').attributes('disabled')).toBeUndefined()

    vi.mocked(registrationsApi.submitRegistration).mockRejectedValueOnce('unknown')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('Fehler beim Einreichen der Registrierung.')
  })

  describe('account creation after the registration', () => {
    async function submitRegistrationForm(wrapper: ReturnType<typeof mountView>) {
      await flushPromises()
      await wrapper.findAll('select')[0].setValue('district-1')
      await wrapper.get('input[type="text"]').setValue('Erika Beispiel')
      await wrapper.get('input[type="email"]').setValue('erika@example.org')
      await wrapper.get('form').trigger('submit')
      await flushPromises()
    }

    beforeEach(() => {
      vi.mocked(registrationsApi.submitRegistration).mockResolvedValue({} as registrationsApi.RegistrationResponse)
    })

    it('offers to create the account and names the email address that must match', async () => {
      const wrapper = mountView()
      await submitRegistrationForm(wrapper)

      const hint = wrapper.get('[data-testid="create-account"]')
      expect(hint.text()).toContain('erika@example.org')
      expect(hint.text()).toContain('dieselbe E-Mail-Adresse')
      expect(hint.get('button').text()).toBe('Konto anlegen')
      expect(wrapper.find('[data-testid="account-linked"]').exists()).toBe(false)
    })

    it('starts the login with prompt=create when the account is created', async () => {
      getAuthorizationUrl.mockResolvedValue('https://auth.example/auth?prompt=create')
      const hrefSetter = vi.fn()
      const original = window.location
      Object.defineProperty(window, 'location', {
        configurable: true,
        value: { set href(value: string) { hrefSetter(value) } },
      })
      try {
        const wrapper = mountView()
        await submitRegistrationForm(wrapper)

        await wrapper.get('[data-testid="create-account"] button').trigger('click')
        await flushPromises()

        expect(getAuthorizationUrl).toHaveBeenCalledWith({ prompt: 'create' })
        expect(hrefSetter).toHaveBeenCalledWith('https://auth.example/auth?prompt=create')
      } finally {
        Object.defineProperty(window, 'location', { configurable: true, value: original })
      }
    })

    it('shows a failed redirect and keeps the button usable', async () => {
      getAuthorizationUrl.mockRejectedValue(new Error('Discovery fehlgeschlagen'))
      const wrapper = mountView()
      await submitRegistrationForm(wrapper)

      await wrapper.get('[data-testid="create-account"] button').trigger('click')
      await flushPromises()

      expect(wrapper.get('[role="alert"]').text()).toContain('Discovery fehlgeschlagen')
      expect(wrapper.get('[data-testid="create-account"] button').attributes('disabled')).toBeUndefined()
    })

    it('sends the access token of a logged-in user and does not offer a second account', async () => {
      const wrapper = mountView()
      vi.spyOn(useAuthStore(), 'getToken').mockReturnValue('access-token-1')
      await submitRegistrationForm(wrapper)

      expect(registrationsApi.submitRegistration).toHaveBeenCalledWith(
        'district-1', expect.objectContaining({ email: 'erika@example.org' }), 'access-token-1',
      )
      expect(wrapper.find('[data-testid="account-linked"]').exists()).toBe(true)
      expect(wrapper.find('[data-testid="create-account"]').exists()).toBe(false)
    })

    it('prefills and locks the email of a logged-in account', async () => {
      const wrapper = mountView()
      useAuthStore().setToken(
        { accessToken: 'access-token-1', expiresAt: Date.now() / 1000 + 300 } as never,
        { sub: 'user-1', email: ' konto@example.org ' },
      )
      await flushPromises()

      const email = wrapper.get('input[type="email"]')
      expect((email.element as HTMLInputElement).value).toBe('konto@example.org')
      expect(email.attributes('readonly')).toBeDefined()
      expect(wrapper.find('[data-testid="account-email-hint"]').exists()).toBe(true)
    })

    it('keeps the email editable without a logged-in account', async () => {
      const wrapper = mountView()
      await flushPromises()

      expect(wrapper.get('input[type="email"]').attributes('readonly')).toBeUndefined()
      expect(wrapper.find('[data-testid="account-email-hint"]').exists()).toBe(false)
    })
  })
})
