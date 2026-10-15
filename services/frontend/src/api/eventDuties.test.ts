// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { expect,it,vi } from 'vitest'
import { apiFetch } from './client'
import * as api from './eventDuties'
vi.mock('./client',()=>({apiFetch:vi.fn().mockResolvedValue(undefined)}))
it('uses scoped routes for configuration, identity and suggestions',async()=>{
 await api.listDutyCategories('d','c');await api.createDutyCategory('d',{congregation_id:null,code:'x',label:'X',enabled:true,capacity:1,event_categories:[]});await api.updateDutyCategory('d','cat',{enabled:false});await api.putDutyConfiguration('d',{congregation_id:'c',duty_category_id:'cat',enabled:true,capacity:1,event_categories:[]});await api.restoreDutyInheritance('d','cat','c');await api.getSlotDuties('d','s',true);await api.saveDutyAssignment('d','s',{duty_category_id:'cat',name:'Anna'});await api.saveDutyAssignment('d','s',{duty_category_id:'cat',linked_user_sub:'verified'},'a');await api.revalidateDutyAssignment('d','a');await api.deleteDutyAssignment('d','a');await api.listEligibleUsers('d');await api.listSuggestions('d','cat','c',true);await api.setSuggestionHidden('d','name',true)
 expect(vi.mocked(apiFetch).mock.calls.map(x=>x[0])).toEqual(['/api/v1/districts/d/duties/categories?congregation_id=c','/api/v1/districts/d/duties/categories','/api/v1/districts/d/duties/categories/cat','/api/v1/districts/d/duties/configuration','/api/v1/districts/d/duties/configuration/cat?congregation_id=c','/api/v1/districts/d/duties/slots/s?include_quarantined=true','/api/v1/districts/d/duties/slots/s','/api/v1/districts/d/duties/assignments/a','/api/v1/districts/d/duties/assignments/a/revalidate','/api/v1/districts/d/duties/assignments/a','/api/v1/districts/d/duties/eligible-users','/api/v1/districts/d/duties/suggestions?duty_category_id=cat&include_hidden=true&congregation_id=c','/api/v1/districts/d/duties/suggestions/name'])
})
