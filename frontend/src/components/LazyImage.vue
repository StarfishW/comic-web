<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'

const props = defineProps({
  src: { type: String, required: true },
  alt: { type: String, default: '' },
  priority: { type: Number, default: 0 }, // 优先级，数字越小越优先
  sequential: { type: Boolean, default: false }, // 是否需要顺序加载
  placeholder: { type: String, default: '' }, // 占位图
})

const imgRef = ref(null)
const isLoaded = ref(false)
const isLoading = ref(false)
const hasError = ref(false)
const currentSrc = ref(props.placeholder || '')

let observer = null

// 加载图片
async function loadImage() {
  if (isLoaded.value || isLoading.value) return

  isLoading.value = true
  hasError.value = false

  return new Promise((resolve, reject) => {
    const img = new Image()

    img.onload = () => {
      currentSrc.value = props.src
      isLoaded.value = true
      isLoading.value = false
      resolve()
    }

    img.onerror = () => {
      hasError.value = true
      isLoading.value = false
      reject(new Error('Image load failed'))
    }

    img.src = props.src
  })
}

// 设置 Intersection Observer
function setupObserver() {
  if (!imgRef.value) return

  // 根据 sequential 属性决定 rootMargin
  // sequential 模式（阅读器）：不预加载，由代码控制
  // 非 sequential 模式（列表页）：提前 50px 预加载
  const rootMargin = props.sequential ? '0px' : '50px'

  observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          // 进入视口时加载图片
          if (props.sequential) {
            // 顺序加载：仅触发事件，不自动加载（由父组件控制）
            imgRef.value.dispatchEvent(new CustomEvent('visible', { bubbles: true }))
          } else {
            // 列表页：自动加载可见图片
            loadImage()
          }
          // 加载后停止观察
          if (observer && imgRef.value) {
            observer.unobserve(imgRef.value)
          }
        }
      })
    },
    {
      rootMargin: rootMargin,
      threshold: 0.01,
    }
  )

  observer.observe(imgRef.value)
}

// 重试加载
function retry() {
  hasError.value = false
  isLoaded.value = false
  loadImage()
}

// 暴露加载方法给父组件
defineExpose({
  loadImage,
  isLoaded,
  isLoading,
})

onMounted(() => {
  // 在 sequential 模式下，不使用 observer，完全由父组件控制加载
  if (!props.sequential) {
    setupObserver()
  }
})

onUnmounted(() => {
  if (observer && imgRef.value) {
    observer.unobserve(imgRef.value)
  }
})

// 监听 src 变化
watch(() => props.src, () => {
  if (isLoaded.value) {
    isLoaded.value = false
    currentSrc.value = props.placeholder || ''
    // 在 sequential 模式下，不使用 observer
    if (!props.sequential) {
      setupObserver()
    }
  }
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

    <!-- 加载状态 -->
    <div v-if="isLoading" class="lazy-loading">
      <div class="lazy-spinner"></div>
    </div>

    <!-- 错误状态 -->
    <div v-if="hasError" class="lazy-error" @click="retry">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
        <line x1="12" y1="9" x2="12" y2="13"/>
        <line x1="12" y1="17" x2="12.01" y2="17"/>
      </svg>
      <span>加载失败，点击重试</span>
    </div>

    <!-- 占位符 -->
    <div v-if="!isLoaded && !isLoading && !hasError" class="lazy-placeholder">
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
  to { transform: rotate(360deg); }
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
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
</style>
