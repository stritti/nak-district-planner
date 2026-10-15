<!-- SPDX-FileCopyrightText: 2026 Stephan Strittmatter
     SPDX-License-Identifier: AGPL-3.0-only -->

<script setup lang="ts">
import { ref, watch } from 'vue'
import { getSlotDuties, listEligibleUsers, listSuggestions, saveDutyAssignment, revalidateDutyAssignment, deleteDutyAssignment, setSuggestionHidden, type DutyCategory, type DutyAssignment, type DutySuggestion, type EligibleUser } from '../api/eventDuties'
const props=defineProps<{districtId:string;slotId:string;congregationId?:string|null;canEdit:boolean}>()
const categories=ref<DutyCategory[]>([]), assignments=ref<DutyAssignment[]>([]), users=ref<EligibleUser[]>([]), suggestions=ref<DutySuggestion[]>([])
const category=ref(''), kind=ref('name'), name=ref(''), subject=ref(''), editing=ref<string>(), loading=ref(false), error=ref('')
let version=0, suggestionsVersion=0
async function load() {
 const current=++version; categories.value=[];assignments.value=[];users.value=[];suggestions.value=[];error.value='';loading.value=true
 try {
  const data=await getSlotDuties(props.districtId,props.slotId,props.canEdit)
  if(current!==version)return
  categories.value=data.categories;assignments.value=data.assignments;category.value=data.categories[0]?.id??''
  if(props.canEdit) { const choices=await listEligibleUsers(props.districtId,props.congregationId??undefined);if(current===version)users.value=choices }
 }catch(cause){if(current===version)error.value=cause instanceof Error?cause.message:'Dienste konnten nicht geladen werden'}
 finally{if(current===version)loading.value=false}
}
watch(()=>[props.districtId,props.slotId,props.congregationId,props.canEdit],()=>{ editing.value=undefined;name.value='';subject.value='';void load() },{immediate:true})
watch([category,()=>props.districtId,()=>props.congregationId],async()=>{
 const current=++suggestionsVersion;suggestions.value=[]
 if(!category.value||!props.canEdit)return
 try { const data=await listSuggestions(props.districtId,category.value,props.congregationId??undefined,true);if(current===suggestionsVersion)suggestions.value=data }
 catch(cause){if(current===suggestionsVersion)error.value=cause instanceof Error?cause.message:'Namensvorschläge konnten nicht geladen werden'}
})
async function save(){
 if(loading.value||!category.value||!(kind.value==='name'?name.value.trim():subject.value))return
 loading.value=true;error.value=''
 try{
  await saveDutyAssignment(props.districtId,props.slotId,kind.value==='name'?{duty_category_id:category.value,name:name.value.trim()}:{duty_category_id:category.value,linked_user_sub:subject.value},editing.value)
  name.value='';subject.value='';editing.value=undefined;await load()
 }catch(cause){error.value=cause instanceof Error?cause.message:'Speichern fehlgeschlagen';loading.value=false}
}
async function remove(id:string){loading.value=true;error.value='';try{await deleteDutyAssignment(props.districtId,id);await load()}catch(cause){error.value=cause instanceof Error?cause.message:'Entfernen fehlgeschlagen';loading.value=false}}
async function revalidate(id:string){loading.value=true;error.value='';try{await revalidateDutyAssignment(props.districtId,id);await load()}catch(cause){error.value=cause instanceof Error?cause.message:'Bestätigung fehlgeschlagen';loading.value=false}}
async function hide(s:DutySuggestion){error.value='';try{const updated=await setSuggestionHidden(props.districtId,s.id,!s.hidden);suggestions.value=suggestions.value.map(x=>x.id===s.id?updated:x)}catch(cause){error.value=cause instanceof Error?cause.message:'Änderung fehlgeschlagen'}}
function edit(a:DutyAssignment){editing.value=a.id;category.value=a.duty_category_id;kind.value=a.linked_user_sub?'account':'name';subject.value=a.linked_user_sub??'';name.value=a.display_name}
</script>
<template>
 <section class="space-y-3 border-t pt-4" aria-label="Organisatorische Dienste">
  <h3 class="font-semibold">Organisatorische Dienste</h3><p class="text-sm text-gray-500">Optional – freie Namen erhalten keinen persönlichen Kalender.</p>
  <p v-if="loading" role="status">Laden…</p><p v-if="error" role="alert" class="text-red-600">{{ error }}</p>
  <div v-for="a in assignments" :key="a.id" class="rounded border p-2 text-sm">
   <p>{{ a.duty_label }}: {{ a.display_name }} <span v-if="a.linked_user_sub">(Konto)</span></p>
   <p v-if="a.needs_review" class="text-amber-700">Prüfung erforderlich</p><p v-if="a.over_capacity" class="text-amber-700">Kapazität überschritten</p>
   <div v-if="canEdit" class="flex gap-3"><button v-if="a.quarantined" type="button" data-testid="revalidate-duty" :disabled="loading" class="text-blue-600" @click="revalidate(a.id)">Geltungsbereich bestätigen</button><button v-else type="button" :disabled="loading" class="text-blue-600" @click="edit(a)">Neu zuordnen</button><button type="button" data-testid="remove-duty" :disabled="loading" class="text-red-600" @click="remove(a.id)">Entfernen</button></div>
  </div>
  <form v-if="canEdit && categories.length" class="space-y-2" @submit.prevent="save">
   <label class="block">Dienst<select v-model="category" class="form-input"><option v-for="c in categories" :key="c.id" :value="c.id">{{ c.label }} ({{ c.capacity }} Plätze)</option></select></label>
   <label class="block">Zuordnung<select v-model="kind" data-testid="identity-kind" class="form-input"><option value="name">Freier Name</option><option value="account">Verknüpftes Konto</option></select></label>
   <label v-if="kind==='name'" class="block">Name<input v-model="name" data-testid="duty-name" class="form-input" :list="`duty-names-${slotId}`" maxlength="200" /><datalist :id="`duty-names-${slotId}`"><option v-for="s in suggestions.filter(x=>!x.hidden)" :key="s.id" :value="s.display_name" /></datalist></label>
   <label v-else class="block">Konto<select v-model="subject" data-testid="duty-account" class="form-input"><option value="">Konto auswählen</option><option v-for="u in users" :key="u.sub" :value="u.sub">{{ u.display_name }}</option></select></label>
   <button type="submit" class="btn-primary" :disabled="loading || !(kind==='name'?name.trim():subject)">{{ editing ? 'Zuordnung ersetzen' : 'Dienst zuordnen' }}</button>
  </form>
  <details v-if="canEdit && suggestions.length"><summary class="cursor-pointer text-sm">Gespeicherte Namen verwalten</summary><div v-for="s in suggestions" :key="s.id" class="flex gap-2 text-sm py-1"><span>{{ s.display_name }}</span><button type="button" class="text-blue-600" @click="hide(s)">{{ s.hidden?'Wiederherstellen':'Ausblenden' }}</button></div></details>
 </section>
</template>
