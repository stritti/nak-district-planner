// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { apiFetch } from './client'
export interface DutyCategory { id:string; district_id:string; congregation_id:string|null; code:string; label:string; event_categories:string[]; enabled:boolean; capacity:number }
export interface DutyConfiguration { id:string; duty_category_id:string; congregation_id:string; event_categories:string[]; enabled:boolean; capacity:number }
export interface DutyAssignment { id:string; planning_slot_id:string; duty_category_id:string; district_id:string; congregation_id:string|null; display_name:string; duty_label:string; linked_user_sub:string|null; suggestion_id:string|null; needs_review:boolean; over_capacity:boolean; quarantined:boolean }
export interface DutySuggestion { id:string; display_name:string; hidden:boolean }
export interface EligibleUser { sub:string; display_name:string }
export type DutyIdentity = { duty_category_id:string; name:string; suggestion_id?:string; linked_user_sub?:never } | { duty_category_id:string; linked_user_sub:string; name?:never }
const base = (district:string) => `/api/v1/districts/${encodeURIComponent(district)}/duties`
const scope = (congregation?:string) => congregation ? `?${new URLSearchParams({congregation_id:congregation})}` : ''
export function listDutyCategories(d:string,c?:string):Promise<{categories:DutyCategory[];overrides:DutyConfiguration[]}> { return apiFetch(`${base(d)}/categories${scope(c)}`) }
export function createDutyCategory(d:string,data:Omit<DutyCategory,'id'|'district_id'>):Promise<DutyCategory> { return apiFetch(`${base(d)}/categories`,{method:'POST',body:JSON.stringify(data)}) }
export function updateDutyCategory(d:string,id:string,data:Partial<DutyCategory>):Promise<DutyCategory> { return apiFetch(`${base(d)}/categories/${encodeURIComponent(id)}`,{method:'PATCH',body:JSON.stringify(data)}) }
export function putDutyConfiguration(d:string,data:Omit<DutyConfiguration,'id'>):Promise<DutyConfiguration> { return apiFetch(`${base(d)}/configuration`,{method:'PUT',body:JSON.stringify(data)}) }
export function restoreDutyInheritance(d:string,id:string,c:string):Promise<void> { return apiFetch(`${base(d)}/configuration/${encodeURIComponent(id)}${scope(c)}`,{method:'DELETE'}) }
export function getSlotDuties(d:string,id:string,includeQuarantined=false):Promise<{categories:DutyCategory[];assignments:DutyAssignment[]}> { const query=includeQuarantined?'?include_quarantined=true':'';return apiFetch(`${base(d)}/slots/${encodeURIComponent(id)}${query}`) }
export function saveDutyAssignment(d:string,slot:string,data:DutyIdentity,id?:string):Promise<DutyAssignment> { return apiFetch(id?`${base(d)}/assignments/${encodeURIComponent(id)}`:`${base(d)}/slots/${encodeURIComponent(slot)}`,{method:id?'PATCH':'POST',body:JSON.stringify(data)}) }
export function revalidateDutyAssignment(d:string,id:string):Promise<DutyAssignment> { return apiFetch(`${base(d)}/assignments/${encodeURIComponent(id)}/revalidate`,{method:'POST'}) }
export function deleteDutyAssignment(d:string,id:string):Promise<void> { return apiFetch(`${base(d)}/assignments/${encodeURIComponent(id)}`,{method:'DELETE'}) }
export function listEligibleUsers(d:string,c?:string):Promise<EligibleUser[]> { return apiFetch(`${base(d)}/eligible-users${scope(c)}`) }
export function listSuggestions(d:string,category:string,c?:string,hidden=false):Promise<DutySuggestion[]> { const q=new URLSearchParams({duty_category_id:category,include_hidden:String(hidden)}); if(c)q.set('congregation_id',c); return apiFetch(`${base(d)}/suggestions?${q}`) }
export function setSuggestionHidden(d:string,id:string,hidden:boolean):Promise<DutySuggestion> { return apiFetch(`${base(d)}/suggestions/${encodeURIComponent(id)}`,{method:'PATCH',body:JSON.stringify({hidden})}) }
