import { afterEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import AutocompleteInput, { type AutocompleteOption } from './AutocompleteInput.vue'

const options: AutocompleteOption[] = [
  { id: '1', label: 'Anna Beispiel', sublabel: 'Gemeinde A', isPriority: true },
  { id: '2', label: 'Bernd Muster', sublabel: 'Gemeinde B' },
  { id: '3', label: 'Clara Test' },
]

function mountInput(modelValue = { id: null as string | null, text: '' }) {
  return mount(AutocompleteInput, {
    props: { options, modelValue, placeholder: 'Name suchen' },
  })
}

afterEach(() => {
  vi.useRealTimers()
})

describe('AutocompleteInput', () => {
  it('groups priority options and filters by label or sublabel', async () => {
    const wrapper = mountInput()
    const input = wrapper.get('input')

    await input.trigger('focus')
    expect(wrapper.text()).toContain('Eigene Gemeinde')
    expect(wrapper.text()).toContain('Weitere Amtstragende')
    expect(wrapper.findAll('[role="option"]')).toHaveLength(3)

    await input.setValue('Gemeinde B')
    expect(wrapper.findAll('[role="option"]')).toHaveLength(1)
    expect(wrapper.text()).toContain('Bernd Muster')
  })

  it('emits free text with a null id and resets the highlight', async () => {
    const wrapper = mountInput({ id: '1', text: 'Anna Beispiel' })

    await wrapper.get('input').setValue('Freier Name')

    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([{ id: null, text: 'Freier Name' }])
  })

  it('selects an option by mouse and emits its real id', async () => {
    const wrapper = mountInput()
    const input = wrapper.get('input')
    await input.trigger('focus')

    await wrapper.findAll('[role="option"]')[1].trigger('mousedown')

    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([
      { id: '2', text: 'Bernd Muster' },
    ])
    expect(wrapper.find('[role="listbox"]').exists()).toBe(false)
  })

  it('opens and cycles options with arrow keys and confirms with Enter', async () => {
    const wrapper = mountInput()
    const input = wrapper.get('input')

    await input.trigger('keydown', { key: 'ArrowDown' })
    expect(wrapper.find('[role="listbox"]').exists()).toBe(true)

    await input.trigger('keydown', { key: 'ArrowDown' })
    await input.trigger('keydown', { key: 'ArrowUp' })
    await input.trigger('keydown', { key: 'Enter' })

    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([
      { id: '3', text: 'Clara Test' },
    ])
  })

  it('closes on Enter without a highlight and on Escape', async () => {
    const wrapper = mountInput()
    const input = wrapper.get('input')

    await input.trigger('focus')
    await input.trigger('keydown', { key: 'Enter' })
    expect(wrapper.find('[role="listbox"]').exists()).toBe(false)

    await input.trigger('focus')
    await input.trigger('keydown', { key: 'Escape' })
    expect(wrapper.find('[role="listbox"]').exists()).toBe(false)
  })

  it('pre-selects the best match while typing so Enter confirms it', async () => {
    const wrapper = mountInput()
    const input = wrapper.get('input')
    await input.trigger('focus')

    await input.setValue('ber')

    const options = wrapper.findAll('[role="option"]')
    expect(options).toHaveLength(1)
    expect(options[0].attributes('aria-selected')).toBe('true')
    await input.trigger('keydown', { key: 'Enter' })
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([{ id: '2', text: 'Bernd Muster' }])
  })

  it('does not highlight anything before the user types', async () => {
    const wrapper = mountInput()
    await wrapper.get('input').trigger('focus')
    expect(wrapper.findAll('[role="option"]').every((o) => o.attributes('aria-selected') === 'false')).toBe(true)
  })

  it('accepts the pre-selected match with Tab', async () => {
    const wrapper = mountInput()
    const input = wrapper.get('input')
    await input.setValue('clar')

    await input.trigger('keydown', { key: 'Tab' })

    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([{ id: '3', text: 'Clara Test' }])
  })

  it('leaves free text alone on Tab and on blur when it matches no name exactly', async () => {
    vi.useFakeTimers()
    const wrapper = mountInput()
    const input = wrapper.get('input')

    await input.setValue('Muster')
    await input.setValue('')
    await input.trigger('keydown', { key: 'Tab' })
    await input.setValue('Gast Prediger')
    await input.trigger('blur')
    vi.advanceTimersByTime(200)

    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([{ id: null, text: 'Gast Prediger' }])
  })

  it('selects a typed name that equals a known option when leaving the field', async () => {
    vi.useFakeTimers()
    const wrapper = mountInput()
    const input = wrapper.get('input')

    await input.setValue('clara test')
    await input.trigger('blur')
    vi.advanceTimersByTime(200)

    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([{ id: '3', text: 'Clara Test' }])
  })

  it('opens the list upwards when there is no room below the input', async () => {
    const wrapper = mount(AutocompleteInput, {
      props: { options, modelValue: { id: null, text: '' } },
      attachTo: document.body,
    })
    const input = wrapper.get('input').element as HTMLInputElement
    vi.spyOn(input, 'getBoundingClientRect').mockReturnValue({
      top: 560, bottom: 600, left: 40, right: 340, width: 300, height: 40, x: 40, y: 560,
      toJSON: () => ({}),
    })
    Object.defineProperty(window, 'innerHeight', { value: 640, configurable: true })

    await wrapper.get('input').trigger('focus')
    await wrapper.vm.$nextTick()

    const style = wrapper.get('[role="listbox"]').attributes('style') ?? ''
    expect(style).toContain('bottom:')
    expect(style).not.toContain('top:')
    expect(style).toContain('width: 300px')
    wrapper.unmount()
  })

  it('opens the list below the input and caps its height when there is room', async () => {
    const wrapper = mount(AutocompleteInput, {
      props: { options, modelValue: { id: null, text: '' } },
      attachTo: document.body,
    })
    const input = wrapper.get('input').element as HTMLInputElement
    vi.spyOn(input, 'getBoundingClientRect').mockReturnValue({
      top: 100, bottom: 140, left: 40, right: 340, width: 300, height: 40, x: 40, y: 100,
      toJSON: () => ({}),
    })
    Object.defineProperty(window, 'innerHeight', { value: 800, configurable: true })

    await wrapper.get('input').trigger('focus')
    await wrapper.vm.$nextTick()

    const style = wrapper.get('[role="listbox"]').attributes('style') ?? ''
    expect(style).toContain('top: 142px')
    expect(style).toContain('max-height: 176px')
    wrapper.unmount()
  })

  it('handles empty filtered results without moving a highlight', async () => {
    const wrapper = mountInput()
    const input = wrapper.get('input')
    await input.setValue('does-not-exist')
    await input.trigger('focus')

    await input.trigger('keydown', { key: 'ArrowDown' })
    await input.trigger('keydown', { key: 'Enter' })

    expect(wrapper.find('[role="listbox"]').exists()).toBe(false)
  })

  it('delays blur closing and cancels the pending close when focused again', async () => {
    vi.useFakeTimers()
    const wrapper = mountInput()
    const input = wrapper.get('input')
    await input.trigger('focus')
    await input.trigger('blur')
    expect(wrapper.find('[role="listbox"]').exists()).toBe(true)

    await input.trigger('focus')
    vi.advanceTimersByTime(200)
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[role="listbox"]').exists()).toBe(true)

    await input.trigger('blur')
    vi.advanceTimersByTime(200)
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[role="listbox"]').exists()).toBe(false)
  })

  it('synchronizes external model changes, exposes focus and clears timers on unmount', async () => {
    vi.useFakeTimers()
    const wrapper = mountInput()
    const input = wrapper.get('input')
    const focus = vi.spyOn(input.element as HTMLInputElement, 'focus')

    ;(wrapper.vm as unknown as { focus: () => void }).focus()
    expect(focus).toHaveBeenCalled()

    await wrapper.setProps({ modelValue: { id: '3', text: 'Clara Test' } })
    expect((wrapper.get('input').element as HTMLInputElement).value).toBe('Clara Test')

    await wrapper.get('input').trigger('blur')
    wrapper.unmount()
    expect(() => vi.runAllTimers()).not.toThrow()
  })
})