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