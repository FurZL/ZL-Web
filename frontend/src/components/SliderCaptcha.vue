<script setup lang="ts">
import { nextTick, ref, watch } from "vue"
import { request } from "@/api/client"

const props = defineProps<{ show: boolean }>()
const emit = defineEmits<{ close: []; verified: [token: string] }>()

type Phase = "loading" | "ready" | "sliding" | "verifying" | "success" | "error"
const phase = ref<Phase>("loading")
const errMsg = ref("")
const trackEl = ref<HTMLElement | null>(null)

const token = ref("")
const gapX = ref(0)
const gapY = ref(0)
const pos = ref(0)
const max = ref(0)
const dragging = ref(false)
const pointId = ref(-1)
const startX = ref(0)
const startPos = ref(0)
const imgSrc = ref("")

const W = 320; const H = 180; const PW = 42

const BGS = [
  "https://bing.com/th?id=OHR.SanMiguelAllende_ZH-CN1840507091_640x360.jpg",
  "https://cn.bing.com/th?id=OHR.AmazonianEcuador_ZH-CN9873999948_640x360.jpg",
  "https://bing.com/th?id=OHR.DalyanTombs_ZH-CN1519154607_640x360.jpg",
  "https://bing.com/th?id=OHR.TheGreatHeat2024_ZH-CN6033129823_640x360.jpg",
  "https://bing.com/th?id=OHR.HauntedEdinburgh_ZH-CN1461834159_640x360.jpg",
  "https://bing.com/th?id=OHR.BabySloth_ZH-CN8329403615_640x360.jpg",
  "https://bing.com/th?id=OHR.SantaPark_ZH-CN7444715899_640x360.jpg",
  "https://bing.com/th?id=OHR.MassapequaOwl_ZH-CN8747028921_640x360.jpg",
  "https://bing.com/th?id=OHR.SardiniaFlavia_ZH-CN6784449568_640x360.jpg",
  "https://bing.com/th?id=OHR.Antilles_ZH-CN8267285876_640x360.jpg",
]

async function loadChallenge() {
  phase.value = "loading"
  errMsg.value = ""
  pos.value = 0
  gapX.value = 0
  gapY.value = 0
  imgSrc.value = BGS[Math.floor(Math.random() * BGS.length)]
  try {
    const data = await request<{ token: string; gap_x: number; gap_y: number }>({ method: "GET", url: "/captcha/challenge" })
    token.value = data.token
    gapX.value = data.gap_x
    gapY.value = data.gap_y || Math.round((H - PW) / 2)
    phase.value = "ready"
    await nextTick()
    if (trackEl.value) max.value = trackEl.value.clientWidth - 36
  } catch (e) {
    errMsg.value = e instanceof Error ? e.message : "加载失败"
    phase.value = "error"
  }
}

const pieceStyle = () => ({
  width: PW + "px",
  height: PW + "px",
  backgroundImage: imgSrc.value ? "url(" + imgSrc.value + ")" : "none",
  backgroundPosition: "-" + gapX.value + "px -" + gapY.value + "px",
  backgroundSize: W + "px " + H + "px",
  transform: "translateX(" + pos.value + "px)",
  transition: dragging.value ? "none" : "transform 0.15s ease",
})

function onPointerDown(e: PointerEvent) {
  if (phase.value !== "ready" && phase.value !== "sliding") return
  dragging.value = true
  phase.value = "sliding"
  startX.value = e.clientX
  startPos.value = pos.value
  pointId.value = e.pointerId
  ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
}

function onPointerMove(e: PointerEvent) {
  if (!dragging.value || e.pointerId !== pointId.value) return
  pos.value = Math.max(0, Math.min(startPos.value + (e.clientX - startX.value), max.value))
}

async function onPointerUp(e: PointerEvent) {
  if (!dragging.value || e.pointerId !== pointId.value) return
  dragging.value = false
  pointId.value = -1
  try { (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId) } catch {}
  if (Math.abs(pos.value - startPos.value) < 5) { phase.value = "ready"; return }
  phase.value = "verifying"
  try {
    const r = await request<{ verification_token: string }>({
      method: "POST",
      url: "/captcha/verify",
      data: { token: token.value, x: Math.round(pos.value) },
    })
    phase.value = "success"
    setTimeout(() => emit("verified", r.verification_token), 400)
  } catch {
    errMsg.value = "验证失败，请重试"
    phase.value = "error"
  }
}

watch(() => props.show, (v) => { if (v) loadChallenge() })
</script>

<template>
  <Teleport to="body">
    <div v-if="show" class="dialog-overlay" @click.self="emit('close')">
      <div class="glass-card p-6 w-full max-w-sm">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-base font-bold text-ink">安全验证</h3>
          <button class="text-faint hover:text-ink text-lg leading-none" @click="emit('close')">&times;</button>
        </div>

        <div v-if="phase === 'loading'" class="flex items-center justify-center" :style="{ height: H + 'px' }">
          <span class="spinner mr-2" /> <span class="text-sm text-sub">加载中…</span>
        </div>

        <div v-else-if="phase === 'error'" class="flex flex-col items-center justify-center gap-3" :style="{ height: H + 'px' }">
          <p class="text-sm text-blush">{{ errMsg || '加载失败' }}</p>
          <button class="btn-ghost text-xs !px-3 !py-1" @click="loadChallenge">重试</button>
        </div>

        <template v-else>
          <div class="relative mb-3 select-none rounded-lg" :style="{ width: W + 'px', height: H + 'px' }">
            <img v-if="imgSrc" :src="imgSrc" class="absolute inset-0 w-full h-full object-cover rounded-lg" alt="" />
            <div class="absolute inset-0 bg-black/25 rounded-lg" />
            <div class="absolute z-10" :style="{ top: gapY + 'px' }">
              <div :style="pieceStyle() as any" />
            </div>
            <div
              v-if="gapX > 0"
              class="absolute w-[42px] h-[42px] rounded border-2 border-dashed border-white/70 shadow-[0_0_0_6px_rgba(255,255,255,0.1)]"
              :style="{ left: gapX + 'px', top: gapY + 'px' }"
            />
          </div>

          <div
            ref="trackEl"
            class="relative h-10 bg-ink/5 rounded-lg cursor-pointer select-none overflow-hidden touch-none"
            @pointerdown.prevent="onPointerDown"
            @pointermove="onPointerMove"
            @pointerup="onPointerUp"
          >
            <div class="absolute inset-y-0 left-0 bg-primary/20 rounded-lg" :style="{ width: pos + 18 + 'px', transition: dragging ? 'none' : 'width 0.1s ease' }" />
            <div class="absolute inset-0 flex items-center justify-center text-xs text-faint pointer-events-none">
              向右拖动滑块填充拼图
            </div>
            <div
              class="absolute top-0.5 left-0.5 w-9 h-9 rounded-lg flex items-center justify-center shadow bg-white text-primary hover:text-primary-700"
              :style="{ transform: 'translateX(' + pos + 'px)', transition: dragging ? 'none' : 'transform 0.1s ease' }"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M5 12h14"/><path d="M12 5l7 7-7 7"/></svg>
            </div>
          </div>
        </template>
      </div>
    </div>
  </Teleport>
</template>
