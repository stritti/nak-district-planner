import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import * as registrationsApi from '../api/registrations'
import RegistrationView from './RegistrationView.vue'

vi.mock('../api/registrations')

const districts: registrationsApi.PublicDistrictInfo[] = [
  { id: 'district-1', name: 'Bezirk Eins' },
  { id: 'district-2', name: 'Bezirk Zwei' },
]
const congregations: registrationsApi.PublicCongregationInfo[] = [
  { id: 'cong-1', name: 'Gemeinde A' },
  { id: 'cong-2', name: 'Gemeinde B' },
]

function mountView() {
  return mount(RegistrationView, {
    global: {
      stubs: {
        ContextualHelp: true,
        RouterLink: { template: '<a><slot /></a>' },
      },
    },
  })
}

beforeEach(() => {
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
    await wrapper.findAll('select')[1].setValue('PRIEST')
    await wrapper.findAll('select')[2].setValue('cong-1')
    await wrapper.findAll('select')[3].setValue('YOUTH_LEADER')

    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(registrationsApi.submitRegistration).toHaveBeenCalledWith('district-1', {
      name: 'Erika Beispiel',
      email: 'erika@example.org',
      rank: 'PRIEST',
      congregation_id: 'cong-1',
      special_role: 'YOUTH_LEADER',
      phone: '+49 1234',
      notes: 'Bitte freischalten',
    })
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
    }))
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
})
