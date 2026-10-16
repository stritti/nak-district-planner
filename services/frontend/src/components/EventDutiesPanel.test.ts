// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { beforeEach, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import EventDutiesPanel from './EventDutiesPanel.vue'
import * as api from '../api/eventDuties'
import { ApiError } from '../api/errors'
vi.mock('../api/eventDuties', () => ({ getSlotDuties: vi.fn(), listEligibleUsers: vi.fn(), listSuggestions: vi.fn(), saveDutyAssignment: vi.fn(), revalidateDutyAssignment: vi.fn(), deleteDutyAssignment: vi.fn(), setSuggestionHidden: vi.fn() }))
const category = { id:'cat', label:'Organist', capacity:1, enabled:true }
beforeEach(() => {
 vi.clearAllMocks(); vi.mocked(api.getSlotDuties).mockResolvedValue({ categories:[category], assignments:[] } as never)
 vi.mocked(api.listEligibleUsers).mockResolvedValue([{sub:'verified',display_name:'Anna'}])
 vi.mocked(api.listSuggestions).mockResolvedValue([{id:'name',display_name:'Anna',hidden:false,revision:'"s:v1"'}] as never)
 vi.mocked(api.setSuggestionHidden).mockImplementation(async (_district, _id, hidden) => ({id:'name',display_name:'Anna',hidden,revision:'"s:v2"'}) as never)
})
it('keeps duties optional and uses text identity without linking by matching name', async () => {
 const w=mount(EventDutiesPanel,{props:{districtId:'d',slotId:'s',congregationId:'c',canEdit:true}}); await flushPromises()
 expect(w.text()).toContain('Optional'); expect(api.saveDutyAssignment).not.toHaveBeenCalled()
 await w.get('[data-testid="duty-name"]').setValue('Anna'); await w.get('form').trigger('submit'); await flushPromises()
 expect(api.saveDutyAssignment).toHaveBeenCalledWith('d','s',{duty_category_id:'cat',name:'Anna'},undefined,undefined)
 expect(w.emitted('mutated')).toHaveLength(1)
})
it('saves selected verified account without supplying text identity', async () => {
 const w=mount(EventDutiesPanel,{props:{districtId:'d',slotId:'s',canEdit:true}}); await flushPromises()
 await w.get('[data-testid="identity-kind"]').setValue('account'); await w.get('[data-testid="duty-account"]').setValue('verified')
 await w.get('form').trigger('submit'); await flushPromises()
 expect(api.saveDutyAssignment).toHaveBeenCalledWith('d','s',{duty_category_id:'cat',linked_user_sub:'verified'},undefined,undefined)
})
it('shows review flags and allows removal without losing history silently',async()=>{
 vi.mocked(api.getSlotDuties).mockResolvedValue({categories:[category],assignments:[{id:'a',display_name:'Anna',duty_label:'Organist',needs_review:true,over_capacity:true,revision:'"a:v1"'}]} as never)
 const w=mount(EventDutiesPanel,{props:{districtId:'d',slotId:'s',canEdit:true}});await flushPromises()
 expect(w.text()).toContain('Prüfung erforderlich');expect(w.text()).toContain('Kapazität überschritten')
 await w.get('[data-testid="remove-duty"]').trigger('click');await flushPromises();expect(api.deleteDutyAssignment).toHaveBeenCalledWith('d','a','"a:v1"')
})
it('loads authorized quarantined duties and revalidates their current scope',async()=>{
 vi.mocked(api.getSlotDuties).mockResolvedValue({categories:[category],assignments:[{id:'a',display_name:'Anna',duty_label:'Organist',needs_review:true,over_capacity:false,quarantined:true,revision:'"a:v1"'}]} as never)
 const w=mount(EventDutiesPanel,{props:{districtId:'d',slotId:'s',canEdit:true}});await flushPromises()
 expect(api.getSlotDuties).toHaveBeenCalledWith('d','s',true)
 await w.get('[data-testid="revalidate-duty"]').trigger('click');await flushPromises()
 expect(api.revalidateDutyAssignment).toHaveBeenCalledWith('d','a','"a:v1"')
})
it('reports errors and hides edit controls for readers',async()=>{
 vi.mocked(api.getSlotDuties).mockRejectedValue(new Error('Access denied'))
 const w=mount(EventDutiesPanel,{props:{districtId:'d',slotId:'s',canEdit:false}});await flushPromises()
 expect(w.get('[role="alert"]').text()).toContain('Access denied');expect(w.find('form').exists()).toBe(false)
})
it('reassigns a linked account and manages remembered names',async()=>{
 vi.mocked(api.getSlotDuties).mockResolvedValue({categories:[category],assignments:[{id:'a',duty_category_id:'cat',display_name:'Anna',duty_label:'Organist',linked_user_sub:'verified',needs_review:false,over_capacity:false,revision:'"a:v1"'}]} as never)
 const w=mount(EventDutiesPanel,{props:{districtId:'d',slotId:'s',congregationId:'c',canEdit:true}});await flushPromises()
 const suggestionButton=w.get('details button')
 await suggestionButton.trigger('click');await flushPromises()
 expect(api.setSuggestionHidden).toHaveBeenCalledWith('d','name',true,'"s:v1"')
 expect(w.text()).toContain('Wiederherstellen')
 await w.get('button.text-blue-600').trigger('click');await flushPromises()
 expect(w.get('[data-testid="identity-kind"]').element.value).toBe('account')
 await w.get('form').trigger('submit');await flushPromises()
 expect(api.saveDutyAssignment).toHaveBeenCalledWith('d','s',{duty_category_id:'cat',linked_user_sub:'verified'},'a','"a:v1"')
})
it('surfaces suggestion, save, removal, and visibility failures',async()=>{
 vi.mocked(api.listSuggestions).mockRejectedValueOnce(new Error('Vorschläge kaputt'))
 const w=mount(EventDutiesPanel,{props:{districtId:'d',slotId:'s',canEdit:true}});await flushPromises()
 expect(w.get('[role="alert"]').text()).toContain('Vorschläge kaputt')
 vi.mocked(api.saveDutyAssignment).mockRejectedValueOnce('save')
 await w.get('[data-testid="duty-name"]').setValue('Anna');await w.get('form').trigger('submit');await flushPromises()
 expect(w.get('[role="alert"]').text()).toContain('Speichern fehlgeschlagen')

 vi.mocked(api.getSlotDuties).mockResolvedValueOnce({categories:[category],assignments:[{id:'a',duty_category_id:'cat',display_name:'Anna',duty_label:'Organist'}]} as never)
 await w.setProps({slotId:'other'});await flushPromises()
 vi.mocked(api.deleteDutyAssignment).mockRejectedValueOnce('remove')
 await w.get('[data-testid="remove-duty"]').trigger('click');await flushPromises()
 expect(w.get('[role="alert"]').text()).toContain('Entfernen fehlgeschlagen')
 w.unmount()
 vi.mocked(api.listSuggestions).mockResolvedValueOnce([{id:'name',display_name:'Anna',hidden:false,revision:'"s:v1"'}] as never)
 vi.mocked(api.setSuggestionHidden).mockRejectedValueOnce('hide')
 const hideView=mount(EventDutiesPanel,{props:{districtId:'d',slotId:'s',canEdit:true}});await flushPromises()
 await hideView.get('details button').trigger('click');await flushPromises()
 expect(hideView.get('[role="alert"]').text()).toContain('Änderung fehlgeschlagen')
})

it('guards suggestion visibility changes while another action is loading', async () => {
 let release!: () => void
 vi.mocked(api.setSuggestionHidden).mockImplementationOnce(() => new Promise(resolve => {
  release = () => resolve({id:'name',display_name:'Anna',hidden:true} as never)
 }))
 const w=mount(EventDutiesPanel,{props:{districtId:'d',slotId:'s',canEdit:true}});await flushPromises()
 const button=w.get('details button')
 await button.trigger('click')
 await button.trigger('click')
 expect(api.setSuggestionHidden).toHaveBeenCalledTimes(1)
 release();await flushPromises()
})
it.each([412, 428])('reloads and explains a stale write (%i) instead of showing a raw error', async status => {
 const fresh = {id:'a',duty_category_id:'cat',display_name:'Remote',duty_label:'Organist',revision:'"a:v9"'}
 vi.mocked(api.getSlotDuties)
  .mockResolvedValueOnce({categories:[category],assignments:[{...fresh,display_name:'Anna',revision:'"a:v1"'}]} as never)
  .mockResolvedValueOnce({categories:[category],assignments:[fresh]} as never)
 vi.mocked(api.deleteDutyAssignment).mockRejectedValueOnce(new ApiError(status,'Precondition',{detail:'x'}))
 const w=mount(EventDutiesPanel,{props:{districtId:'d',slotId:'s',canEdit:true}});await flushPromises()
 await w.get('[data-testid="remove-duty"]').trigger('click');await flushPromises()
 expect(w.get('[role="alert"]').text()).toContain('zwischenzeitlich geändert')
 expect(w.text()).toContain('Remote')
 // The retry uses the refreshed revision.
 vi.mocked(api.deleteDutyAssignment).mockResolvedValueOnce(undefined)
 await w.get('[data-testid="remove-duty"]').trigger('click');await flushPromises()
 expect(api.deleteDutyAssignment).toHaveBeenLastCalledWith('d','a','"a:v9"')
})
it('keeps the revision read when the edit started', async () => {
 vi.mocked(api.getSlotDuties).mockResolvedValue({categories:[category],assignments:[{id:'a',duty_category_id:'cat',display_name:'Anna',duty_label:'Organist',linked_user_sub:null,needs_review:false,over_capacity:false,revision:'"a:v1"'}]} as never)
 const w=mount(EventDutiesPanel,{props:{districtId:'d',slotId:'s',canEdit:true}});await flushPromises()
 await w.get('button.text-blue-600').trigger('click')
 await w.get('[data-testid="duty-name"]').setValue('Berta');await w.get('form').trigger('submit');await flushPromises()
 expect(api.saveDutyAssignment).toHaveBeenCalledWith('d','s',{duty_category_id:'cat',name:'Berta'},'a','"a:v1"')
})

