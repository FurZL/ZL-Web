<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'

const props = defineProps<{ show: boolean; file: File | null }>()
const emit = defineEmits<{ confirm: [blob: Blob]; cancel: [] }>()

const imgRef = ref<HTMLImageElement | null>(null)
const imgLoaded = ref(false)
const imgNaturalWidth = ref(0)
const imgNaturalHeight = ref(0)

// 裁剪框（图片坐标系）
const cropX = ref(0)
const cropY = ref(0)
const cropSize = ref(100)

// 容器尺寸
const containerW = ref(400)
const containerH = ref(300)

const imgSrc = ref('')
let objectUrl: string | null = null

watch(() => props.show, (val) => {
  if (val && props.file) {
    if (objectUrl) URL.revokeObjectURL(objectUrl)
    objectUrl = URL.createObjectURL(props.file)
    imgSrc.value = objectUrl
    imgLoaded.value = false
    imgNaturalWidth.value = 0
    imgNaturalHeight.value = 0
  }
})

watch(() => props.file, (file) => {
  if (file && props.show) {
    if (objectUrl) URL.revokeObjectURL(objectUrl)
    objectUrl = URL.createObjectURL(file)
    imgSrc.value = objectUrl
    imgLoaded.value = false
  }
})

function onImgLoad() {
  const img = imgRef.value
  if (!img) return
  imgNaturalWidth.value = img.naturalWidth
  imgNaturalHeight.value = img.naturalHeight

  // 容器限制
  const maxW = Math.min(480, window.innerWidth - 80)
  const maxH = 320
  const ratio = Math.min(maxW / img.naturalWidth, maxH / img.naturalHeight, 1)
  containerW.value = Math.round(img.naturalWidth * ratio)
  containerH.value = Math.round(img.naturalHeight * ratio)

  // 初始裁剪框：居中，取短边 60%
  const minDim = Math.min(img.naturalWidth, img.naturalHeight)
  cropSize.value = Math.round(minDim * 0.6)
  cropX.value = Math.round((img.naturalWidth - cropSize.value) / 2)
  cropY.value = Math.round((img.naturalHeight - cropSize.value) / 2)

  imgLoaded.value = true
}

// 裁剪框显示尺寸
const displayScale = computed(() => containerW.value / imgNaturalWidth.value || 1)
const cropDisplayX = computed(() => cropX.value * displayScale.value)
const cropDisplayY = computed(() => cropY.value * displayScale.value)
const cropDisplaySize = computed(() => cropSize.value * displayScale.value)

// 预览 canvas
const previewCanvas = ref<HTMLCanvasElement | null>(null)

function updatePreview() {
  const canvas = previewCanvas.value
  const img = imgRef.value
  if (!canvas || !img || !imgLoaded.value) return

  const ctx = canvas.getContext('2d')
  if (!ctx) return

  canvas.width = 128
  canvas.height = 128
  ctx.drawImage(
    img,
    cropX.value, cropY.value, cropSize.value, cropSize.value,
    0, 0, 128, 128,
  )
}

watch([cropX, cropY, cropSize, imgLoaded], () => {
  if (imgLoaded.value) nextTick(updatePreview)
})

// 拖拽
let dragging = false
let dragStartX = 0
let dragStartY = 0
let cropStartX = 0
let cropStartY = 0

function onPointerDown(e: PointerEvent) {
  if (!imgLoaded.value) return
  dragging = true
  dragStartX = e.clientX
  dragStartY = e.clientY
  cropStartX = cropX.value
  cropStartY = cropY.value
  ;(e.target as HTMLElement).setPointerCapture(e.pointerId)
}

function onPointerMove(e: PointerEvent) {
  if (!dragging || !imgRef.value) return
  const dx = (e.clientX - dragStartX) / displayScale.value
  const dy = (e.clientY - dragStartY) / displayScale.value
  const maxX = imgNaturalWidth.value - cropSize.value
  const maxY = imgNaturalHeight.value - cropSize.value
  cropX.value = Math.max(0, Math.min(maxX, Math.round(cropStartX + dx)))
  cropY.value = Math.max(0, Math.min(maxY, Math.round(cropStartY + dy)))
}

function onPointerUp() {
  dragging = false
}

// 调整大小
let resizing = false
let resizeStartX = 0
let resizeStartSize = 0

function onResizeDown(e: PointerEvent) {
  e.stopPropagation()
  resizing = true
  resizeStartX = e.clientX
  resizeStartSize = cropSize.value
  ;(e.target as HTMLElement).setPointerCapture(e.pointerId)
}

function onResizeMove(e: PointerEvent) {
  if (!resizing || !imgRef.value) return
  const dx = (e.clientX - resizeStartX) / displayScale.value
  const maxDim = Math.min(imgNaturalWidth.value - cropX.value, imgNaturalHeight.value - cropY.value)
  const minDim = Math.round(Math.min(imgNaturalWidth.value, imgNaturalHeight.value) * 0.1)
  cropSize.value = Math.max(minDim, Math.min(maxDim, Math.round(resizeStartSize + dx * 2)))
}

function onResizeUp() {
  resizing = false
}

// 确认裁剪
function confirmCrop() {
  const img = imgRef.value
  if (!img) return

  const canvas = document.createElement('canvas')
  canvas.width = 128
  canvas.height = 128
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  // 高质量缩放：两步走
  const temp = document.createElement('canvas')
  const tempSize = cropSize.value
  temp.width = tempSize
  temp.height = tempSize
  const tempCtx = temp.getContext('2d')
  if (!tempCtx) return
  tempCtx.drawImage(img, cropX.value, cropY.value, tempSize, tempSize, 0, 0, tempSize, tempSize)

  // 缩到 128
  ctx.imageSmoothingEnabled = true
  ctx.imageSmoothingQuality = 'high'
  ctx.drawImage(temp, 0, 0, tempSize, tempSize, 0, 0, 128, 128)

  canvas.toBlob((blob) => {
    if (blob) emit('confirm', blob)
  }, 'image/jpeg', 0.85)
}

function cancel() {
  emit('cancel')
}
</script>

<template>
  <Teleport to="body">
    <div v-if="show" class="dialog-overlay flex items-center justify-center p-4" @click.self="cancel">
      <div class="glass-card p-5 w-full max-w-lg">
        <h2 class="text-lg font-bold text-ink">裁剪头像</h2>
        <p class="text-xs text-sub mt-1">拖动方框选择区域，拖动右下角调整大小</p>

        <!-- 图片 + 裁剪框 -->
        <div
          v-if="imgSrc"
          class="relative mt-4 mx-auto overflow-hidden select-none"
          :style="{ width: containerW + 'px', height: containerH + 'px', touchAction: 'none' }"
        >
          <img
            ref="imgRef"
            :src="imgSrc"
            class="block w-full h-full"
            draggable="false"
            @load="onImgLoad"
          />

          <!-- 暗色遮罩：用4个div模拟中间挖空 -->
          <div v-if="imgLoaded" class="absolute inset-0">
            <!-- 上 -->
            <div class="absolute left-0 right-0 top-0 bg-black/50" :style="{ height: cropDisplayY + 'px' }" />
            <!-- 下 -->
            <div class="absolute left-0 right-0 bottom-0 bg-black/50" :style="{ height: Math.max(0, containerH - cropDisplayY - cropDisplaySize) + 'px' }" />
            <!-- 左 -->
            <div class="absolute left-0 top-0 bg-black/50" :style="{ width: cropDisplayX + 'px', height: cropDisplaySize + 'px', top: cropDisplayY + 'px' }" />
            <!-- 右 -->
            <div class="absolute right-0 top-0 bg-black/50" :style="{ width: Math.max(0, containerW - cropDisplayX - cropDisplaySize) + 'px', height: cropDisplaySize + 'px', top: cropDisplayY + 'px' }" />

            <!-- 裁剪框 -->
            <div
              class="absolute border-2 border-white cursor-move"
              :style="{
                left: cropDisplayX + 'px',
                top: cropDisplayY + 'px',
                width: cropDisplaySize + 'px',
                height: cropDisplaySize + 'px',
              }"
              @pointerdown="onPointerDown"
              @pointermove="onPointerMove"
              @pointerup="onPointerUp"
            >
              <!-- 网格线 -->
              <div class="absolute inset-0 pointer-events-none">
                <div class="absolute left-1/3 top-0 bottom-0 w-px bg-white/40" />
                <div class="absolute left-2/3 top-0 bottom-0 w-px bg-white/40" />
                <div class="absolute top-1/3 left-0 right-0 h-px bg-white/40" />
                <div class="absolute top-2/3 left-0 right-0 h-px bg-white/40" />
              </div>
              <!-- 右下角调整手柄 -->
              <div
                class="absolute w-5 h-5 bg-white rounded-sm cursor-nwse-resize border border-gray-400"
                style="right: -4px; bottom: -4px;"
                @pointerdown="onResizeDown"
                @pointermove="onResizeMove"
                @pointerup="onResizeUp"
              />
            </div>
          </div>
        </div>

        <!-- 预览 -->
        <div v-if="imgLoaded" class="mt-4 flex items-center gap-4">
          <div>
            <p class="text-xs text-sub mb-1">预览 (128×128)</p>
            <canvas ref="previewCanvas" class="w-16 h-16 rounded-full border border-white/60 shadow-soft" />
          </div>
          <div>
            <p class="text-xs text-sub mb-1">小尺寸预览</p>
            <canvas ref="previewCanvas" class="w-8 h-8 rounded-full border border-white/60 shadow-soft" />
          </div>
        </div>

        <!-- 按钮 -->
        <div class="mt-5 flex gap-3">
          <button class="btn-ghost flex-1" @click="cancel">取消</button>
          <button class="btn-primary flex-1" :disabled="!imgLoaded" @click="confirmCrop">确认裁剪</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
