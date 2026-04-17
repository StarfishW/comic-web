<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { placeholderSrc, isShimmerStyle } from '../utils/placeholder'

const props = defineProps({
  src: { type: String, required: true },
  alt: { type: String, default: '' },
  priority: { type: Number, default: 0 },
  sequential: { type: Boolean, default: false },
  placeholder: { type: String, default: '' },
  shouldLoad: { default: null },
})

const emit = defineEmits(['loaded', 'error'])

const imgRef = ref(null)
const isLoaded = ref(false)
const isLoading = ref(false)
const hasError = ref(false)
const currentSrc = ref(props.placeholder || placeholderSrc.value)

let observer = null
let activeRequestId = 0
let mounted = false

function clearObserver() {
  if (observer) {
    observer.disconnect()
    observer = null
  }
}

function resetState() {
  activeRequestId += 1
  isLoaded.value = false
  isLoading.value = false
  hasError.value = false
  currentSrc.value = props.placeholder || placeholderSrc.value
  clearObserver()
}

async function loadImage() {
  if (!props.src || isLoaded.value || isLoading.value) {
    return Promise.resolve()
  }

  const requestId = ++activeRequestId
  isLoading.value = true
  hasError.value = false

  return new Promise((resolve, reject) => {
    const img = new Image()

    img.onload = () => {
      if (requestId !== activeRequestId) {
        resolve()
        return
      }

      currentSrc.value = props.src
      isLoaded.value = true
      isLoading.value = false
      emit('loaded')
      resolve()
    }

    img.onerror = () => {
      if (requestId !== activeRequestId) {
        resolve()
        return
      }

      hasError.value = true
      isLoading.value = false
      emit('error')
      reject(new Error('Image load failed'))
    }

    img.src = props.src
  })
}

watch(() => props.shouldLoad, (val) => {
  if (val === true) {
    loadImage()
  }
}, { immediate: true })

function setupObserver() {
  if (!imgRef.value || props.shouldLoad !== null || props.sequential) return

  clearObserver()
  observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return

        loadImage()
        clearObserver()
      })
    },
    {
      rootMargin: '50px',
      threshold: 0.01,
    },
  )

  observer.observe(imgRef.value)
}

function retry() {
  hasError.value = false
  loadImage()
}

defineExpose({
  loadImage,
  isLoaded,
  isLoading,
})

onMounted(() => {
  mounted = true

  if (props.shouldLoad === true) {
    loadImage()
    return
  }

  setupObserver()
})

onUnmounted(() => {
  mounted = false
  resetState()
})

watch(() => props.src, () => {
  resetState()

  if (!mounted) return

  if (props.shouldLoad === true) {
    loadImage()
    return
  }

  setupObserver()
})
</script>

<template>
  <div ref="imgRef" class="lazy-image-wrapper">
    <img
      v-if="currentSrc"
      :src="currentSrc"
      :alt="alt"
      :class="['lazy-image', { loaded: isLoaded, loading: isLoading }]"
    />

    <div v-if="isLoading" class="lazy-loading">
      <div class="lazy-spinner"></div>
    </div>

    <div v-if="hasError" class="lazy-error" @click="retry">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
        <line x1="12" y1="9" x2="12" y2="13"/>
        <line x1="12" y1="17" x2="12.01" y2="17"/>
      </svg>
      <span>加载失败，点击重试</span>
    </div>

    <div v-if="isShimmerStyle && !isLoaded && !hasError" class="lazy-placeholder">
      <div class="lazy-placeholder-shimmer"></div>
    </div>
  </div>
</template>

<style scoped>
.lazy-image-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  background: var(--color-border, #e5e7eb);
  overflow: hidden;
}

.lazy-image {
  width: 100%;
  height: 100%;
  object-fit: inherit;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.lazy-image.loaded {
  opacity: 1;
}

.lazy-loading {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.05);
}

.lazy-spinner {
  width: 24px;
  height: 24px;
  border: 2px solid rgba(0, 0, 0, 0.1);
  border-top-color: var(--color-primary, #3b82f6);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.lazy-error {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #ef4444;
  font-size: 12px;
  cursor: pointer;
  padding: 12px;
  text-align: center;
  background: rgba(239, 68, 68, 0.05);
}

.lazy-error:hover {
  background: rgba(239, 68, 68, 0.1);
}

.lazy-placeholder {
  position: absolute;
  inset: 0;
  background: var(--color-border, #e5e7eb);
}

.lazy-placeholder-shimmer {
  width: 100%;
  height: 100%;
  background: linear-gradient(
    90deg,
    rgba(255, 255, 255, 0) 0%,
    rgba(255, 255, 255, 0.4) 50%,
    rgba(255, 255, 255, 0) 100%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% {
    background-position: -200% 0;
  }

  100% {
    background-position: 200% 0;
  }
}
</style>
