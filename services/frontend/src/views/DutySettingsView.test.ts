// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { beforeEach, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia,setActivePinia } from 'pinia'
import { useAuthStore } from '../stores/auth'
import { useDistrictsStore } from '../stores/districts'
import DutySettingsView from './DutySettingsView.vue'
import * as api from '../api/eventDuties'
vi.mock('../api/eventDuties',()=>({listDutyCategories:vi.fn(),updateDutyCategory:vi.fn(),putDutyConfiguration:vi.fn(),restoreDutyInheritance:vi.fn(),createDutyCategory:vi.fn()}))
beforeEach(()=>{setActivePinia(createPinia());vi.clearAllMocks();useDistrictsStore().selectedDistrictId='d';useDistrictsStore().congregations=[{id:'c',name:'Gemeinde',district_id:'d'}] as never;useAuthStore().isSuperadmin=true;vi.mocked(api.listDutyCategories).mockResolvedValue({categories:[{id:'cat',congregation_id:null,label:'Organist',code:'organist',event_categories:['Gottesdienst'],capacity:1,enabled:true}],overrides:[]} as never)})
it('labels inherited configuration and saves explicit congregation override',async()=>{
 const w=mount(DutySettingsView);await flushPromises();await w.get('[data-testid="scope"]').setValue('c');await flushPromises()
 expect(w.text()).toContain('Vom Bezirk geerbt');await w.get('[data-testid="capacity"]').setValue(2);await w.get('[data-testid="save-config"]').trigger('click');await flushPromises()
 expect(api.putDutyConfiguration).toHaveBeenCalledWith('d',{congregation_id:'c',duty_category_id:'cat',enabled:true,capacity:2,event_categories:['Gottesdienst']})
})
it('restores inheritance for explicit overrides',async()=>{
 vi.mocked(api.listDutyCategories).mockResolvedValue({categories:[{id:'cat',congregation_id:null,label:'Organist',event_categories:[],capacity:1,enabled:true}],overrides:[{duty_category_id:'cat',enabled:false,capacity:2,event_categories:[]}]} as never)
 const w=mount(DutySettingsView);await flushPromises();await w.get('[data-testid="scope"]').setValue('c');await flushPromises()
 expect(w.text()).toContain('Lokale Abweichung');await w.get('[data-testid="restore-config"]').trigger('click');await flushPromises();expect(api.restoreDutyInheritance).toHaveBeenCalledWith('d','cat','c')
})
it('does not allow catalogue mutation for viewers',async()=>{
 useAuthStore().isSuperadmin=false;const w=mount(DutySettingsView);await flushPromises();expect(w.find('[data-testid="save-config"]').exists()).toBe(false);expect(w.text()).toContain('Keine Verwaltungsberechtigung')
})
it('updates district definitions and creates optional duties',async()=>{
 const w=mount(DutySettingsView);await flushPromises()
 const rowInputs=w.get('section').findAll('input')
 await rowInputs[2]!.setValue(' Gottesdienst, Konzert, ')
 await w.get('[data-testid="save-config"]').trigger('click');await flushPromises()
 expect(api.updateDutyCategory).toHaveBeenCalledWith('d','cat',{enabled:true,capacity:1,event_categories:['Gottesdienst','Konzert']})

 const createInputs=w.get('form').findAll('input')
 await createInputs[0]!.setValue('Schließdienst');await createInputs[1]!.setValue(' closing ')
 await w.get('form').trigger('submit');await flushPromises()
 expect(api.createDutyCategory).toHaveBeenCalledWith('d',{congregation_id:null,code:'closing',label:'Schließdienst',event_categories:[],enabled:true,capacity:1})
})
it('accepts scoped administrators and reports operation failures',async()=>{
 useAuthStore().isSuperadmin=false
 useAuthStore().memberships=[{role:'CONGREGATION_ADMIN',scope_type:'CONGREGATION',scope_id:'c'}] as never
 vi.mocked(api.listDutyCategories).mockResolvedValue({categories:[{id:'cat',congregation_id:null,label:'Organist',code:'organist',event_categories:[],capacity:1,enabled:true}],overrides:[{duty_category_id:'cat',enabled:true,capacity:1,event_categories:[]}]} as never)
 const w=mount(DutySettingsView);await flushPromises()
 expect(w.text()).toContain('Keine Verwaltungsberechtigung')
 await w.get('[data-testid="scope"]').setValue('c');await flushPromises()
 expect(w.find('[data-testid="save-config"]').exists()).toBe(true)

 vi.mocked(api.putDutyConfiguration).mockRejectedValueOnce('save')
 await w.get('[data-testid="save-config"]').trigger('click');await flushPromises()
 expect(w.get('[role="alert"]').text()).toContain('Speichern fehlgeschlagen')
 vi.mocked(api.restoreDutyInheritance).mockRejectedValueOnce(new Error('restore'))
 await w.get('[data-testid="restore-config"]').trigger('click');await flushPromises()
 expect(w.get('[role="alert"]').text()).toContain('restore')

 const createInputs=w.get('form').findAll('input')
 await createInputs[0]!.setValue('Dirigent');await createInputs[1]!.setValue('conductor')
 vi.mocked(api.createDutyCategory).mockRejectedValueOnce('create')
 await w.get('form').trigger('submit');await flushPromises()
 expect(w.get('[role="alert"]').text()).toContain('Anlegen fehlgeschlagen')
})
it('handles missing districts and catalogue load failures',async()=>{
 useDistrictsStore().selectedDistrictId=''
 const empty=mount(DutySettingsView);await flushPromises()
 expect(api.listDutyCategories).not.toHaveBeenCalled();expect(empty.text()).toContain('Bitte einen Bezirk auswählen')
 empty.unmount()

 vi.mocked(api.listDutyCategories).mockRejectedValueOnce('load')
 useDistrictsStore().selectedDistrictId='d'
 const failed=mount(DutySettingsView);await flushPromises()
 expect(failed.get('[role="alert"]').text()).toContain('Konfiguration konnte nicht geladen werden')
})
