import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ConfirmDialog from '@/components/ConfirmDialog.vue'

const globalStubs = { global: { stubs: { Teleport: true } } }

describe('ConfirmDialog', () => {
  it('renders nothing when closed', () => {
    const wrapper = mount(ConfirmDialog, {
      ...globalStubs,
      props: {
        open: false,
        title: 'Löschen?',
        message: 'Wirklich löschen?',
      },
    })
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
  })

  it('renders title and message when open', () => {
    const wrapper = mount(ConfirmDialog, {
      ...globalStubs,
      props: {
        open: true,
        title: 'Integration löschen?',
        message: 'Wird unwiderruflich gelöscht.',
      },
    })
    expect(wrapper.text()).toContain('Integration löschen?')
    expect(wrapper.text()).toContain('Wird unwiderruflich gelöscht.')
  })

  it('emits cancel when the cancel button is clicked', async () => {
    const wrapper = mount(ConfirmDialog, {
      ...globalStubs,
      props: {
        open: true,
        title: 'Löschen?',
        message: 'Wirklich?',
      },
    })
    const buttons = wrapper.findAll('button')
    await buttons[0]!.trigger('click')
    expect(wrapper.emitted('cancel')).toHaveLength(1)
    expect(wrapper.emitted('confirm')).toBeUndefined()
  })

  it('emits confirm when the confirm button is clicked (non-dangerous)', async () => {
    const wrapper = mount(ConfirmDialog, {
      ...globalStubs,
      props: {
        open: true,
        title: 'Löschen?',
        message: 'Wirklich?',
        variant: 'danger',
      },
    })
    const buttons = wrapper.findAll('button')
    await buttons[1]!.trigger('click')
    expect(wrapper.emitted('confirm')).toHaveLength(1)
  })

  it('disables confirm in dangerous mode until the confirm word is typed', async () => {
    const wrapper = mount(ConfirmDialog, {
      ...globalStubs,
      props: {
        open: true,
        title: 'Integration löschen?',
        message: 'Wird unwiderruflich gelöscht.',
        variant: 'danger',
        dangerous: true,
      },
    })
    const confirmButton = wrapper.findAll('button')[1]!
    expect(confirmButton.attributes('disabled')).toBeDefined()

    await confirmButton.trigger('click')
    expect(wrapper.emitted('confirm')).toBeUndefined()

    const input = wrapper.find('input')
    await input.setValue('LÖSCHEN')
    expect(confirmButton.attributes('disabled')).toBeUndefined()

    await confirmButton.trigger('click')
    expect(wrapper.emitted('confirm')).toHaveLength(1)
  })

  it('keeps confirm disabled in dangerous mode while loading, even with the correct word typed', async () => {
    const wrapper = mount(ConfirmDialog, {
      ...globalStubs,
      props: {
        open: true,
        title: 'Integration löschen?',
        message: 'Wird unwiderruflich gelöscht.',
        variant: 'danger',
        dangerous: true,
        loading: true,
      },
    })
    const input = wrapper.find('input')
    await input.setValue('LÖSCHEN')

    const confirmButton = wrapper.findAll('button')[1]!
    expect(confirmButton.attributes('disabled')).toBeDefined()

    await confirmButton.trigger('click')
    expect(wrapper.emitted('confirm')).toBeUndefined()

    // Enter key in the input goes through the same onConfirm() guard.
    await input.trigger('keydown.enter')
    expect(wrapper.emitted('confirm')).toBeUndefined()
  })
})
