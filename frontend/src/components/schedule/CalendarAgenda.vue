<script setup lang="ts">
import { ref } from 'vue'
import { deleteCalendarEntry, saveCalendarEntry } from '@/api/schedule'
import { useDialog } from '@/composables/useDialog'
import type { CalendarEntry } from '@/types'
defineProps<{entries: CalendarEntry[]}>()
const emit=defineEmits<{refresh:[]}>()
const {showConfirm}=useDialog()
const title=ref(''), location=ref(''), start=ref(''), end=ref(''), id=ref<string|null>(null)
const opened=ref(false), error=ref(''), busy=ref(false)
function edit(e?:CalendarEntry) {
  title.value=e?.title ?? ''; location.value=e?.location ?? ''; id.value=e?.id ?? null
  start.value=e?.starts_at.slice(0,16) ?? ''; end.value=e?.ends_at.slice(0,16) ?? ''
  opened.value=true;error.value=''
}
async function save() {
  if(busy.value)return
  if(end.value<=start.value){error.value='结束时间必须晚于开始时间';return}
  busy.value=true
  try { await saveCalendarEntry(id.value,{title:title.value,location:location.value||null,starts_at:start.value+':00+08:00',ends_at:end.value+':00+08:00'}); opened.value=false; error.value=''; emit('refresh') }
  catch(e){error.value=(e as Error).message} finally {busy.value=false}
}
async function remove(e:CalendarEntry) {
  if(busy.value || !(await showConfirm('删除这条个人日程？')))return
  busy.value=true
  try{await deleteCalendarEntry(e.id);error.value='';if(id.value===e.id)opened.value=false;emit('refresh')}catch(e){error.value=(e as Error).message}finally{busy.value=false}
}
</script>
<template>
<section class="glass-card mt-5 space-y-3 p-5 sm:p-7">
  <div class="flex items-center justify-between gap-3"><h2 class="text-xl font-bold">我的日程</h2><button class="btn-xs" @click="edit()">＋ 添加个人日程</button></div>
  <p class="text-sm text-sub">只发生一次的安排记在这里（北京时间）。它们和课表里的安排都会占用约饭时间。</p>
  <form v-if="opened" class="grid gap-3 sm:grid-cols-2" @submit.prevent="save">
    <label class="label">名称<input required maxlength="128" class="input" v-model="title"/></label><label class="label">地点<input maxlength="255" class="input" v-model="location"/></label>
    <label class="label">开始<input type="datetime-local" required class="input" v-model="start"/></label><label class="label">结束<input type="datetime-local" required class="input" v-model="end"/></label>
    <button class="btn-primary" :disabled="busy">保存</button><button class="btn-ghost" type="button" @click="opened=false">返回</button>
  </form>
  <p v-if="error" role="alert" class="text-sm text-red-700">{{error}}</p>
  <p v-if="!entries.length" class="text-sm text-sub">还没有一次性日程。确认的约饭也会出现在这里。</p>
  <article v-for="e in entries" :key="e.id" class="rounded-xl bg-primary-50 p-3">
    <strong>{{ e.title }}</strong> <span class="text-xs">{{ e.appointment_id ? '已确认约饭' : '个人安排' }} · {{e.location || '未填地点'}}</span>
    <p class="text-sm">{{ e.starts_at.slice(0,16).replace('T',' ') }} 至 {{e.ends_at.slice(0,16).replace('T',' ')}}</p>
    <div v-if="!e.appointment_id"><button class="btn-xs" :disabled="busy" @click="edit(e)">编辑</button> <button class="btn-xs" :disabled="busy" @click="remove(e)">删除</button></div>
  </article>
</section>
</template>
