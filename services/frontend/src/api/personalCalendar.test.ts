// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { expect,it,vi } from 'vitest'
import { apiFetch } from './client'
import * as api from './personalCalendar'
vi.mock('./client',()=>({apiFetch:vi.fn().mockResolvedValue(undefined)}))
it('binds feed issuance and listing to one subject and district',async()=>{
 await api.listPersonalEvents('d','2026-01-01','2026-12-31');await api.listPersonalTokens('d','verified');await api.createPersonalToken('d','verified');await api.revokePersonalToken('a')
 expect(apiFetch).toHaveBeenCalledWith('/api/v1/personal-calendar/events?district_id=d&from_date=2026-01-01&to_date=2026-12-31')
 expect(apiFetch).toHaveBeenCalledWith('/api/v1/export-tokens?district_id=d&subject_sub=verified')
 expect(apiFetch).toHaveBeenCalledWith('/api/v1/export-tokens',{method:'POST',body:JSON.stringify({district_id:'d',subject_sub:'verified',token_type:'INTERNAL',label:'Mein Kalender'})})
 expect(apiFetch).toHaveBeenCalledWith('/api/v1/export-tokens/a',{method:'DELETE'})
})
