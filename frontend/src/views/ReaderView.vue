<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { getChapterDetail, getChapterImageUrl } from '../api'

const props = defineProps({ photoId: { type: String, required: true } })
const router = useRouter()

const chapter = ref(null)
const loading = ref(true)
const error = ref(null)
const mode = ref('scroll') // 'scroll' | 'page'
const currentPage = ref(0)
const showToolbar = ref(true)
let hideTimer = null

const totalPages = computed(() => chapter.value?.images?.length || 0)

function getImageSrc(index) {
  return getChapterImageUrl(props.photoId, index)
}

async function fetchChapter() {
  try {
    loading.value = true
    error.value = null
    chapter.value = await getChapterDetail(props.photoId)
    currentPage.value = 0
  } catch (e) {
    error.value = '加载失败: ' + (e.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

function prevPage() {
  if (currentPage.value > 0) currentPage.value--
}

function nextPage() {
  if (currentPage.value < totalPages.value - 1) currentPage.value++
}

function goBack() {
  if (chapter.value?.album_id) {
    router.push({ name: 'ComicDetail', params: { id: chapter.value.album_id } })
  } else {
    router.back()
  }
}

function toggleToolbar() {
  showToolbar.value = !showToolbar.value
}

function handleKeydown(e) {
  if (mode.value !== 'page') return
  if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') prevPage()
  if (e.key === 'ArrowRight' || e.key === 'ArrowDown') nextPage()
}

watch(() => props.photoId, fetchChapter)
onMounted(() => {
  fetchChapter()
  document.addEventListener('keydown', handleKeydown)
})
onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <div class="reader-view" @click="toggleToolbar">
    <!-- Top Toolbar -->
    <transition name="slide-down">
      <div v-if="showToolbar" class="toolbar top-bar" @click.stop>
        <button class="tool-btn" @click="goBack" aria-label="返回">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
        </button>
        <span class="toolbar-title">{{ chapter?.title || '阅读中...' }}</span>
        <div class="mode-switch">
          <button :class="['mode-btn', { active: mode === 'scroll' }]" @click="mode = 'scroll'">滚动</button>
          <button :class="['mode-btn', { active: mode === 'page' }]" @click="mode = 'page'">翻页</button>
        </div>
      </div>
    </transition>

    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <div class="spinner-lg"></div>
      <p>加载中...</p>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="error-state" @click.stop>
      <p>{{ error }}</p>
      <button class="retry-btn" @click="fetchChapter">重试</button>
    </div>

    <!-- Scroll Mode -->
    <div v-else-if="mode === 'scroll'" class="scroll-container">
      <div v-for="(img, i) in chapter.images" :key="i" class="scroll-page">
        <img :src="getImageSrc(i)" :alt="`第${i + 1}页`" loading="lazy" class="page-img" />
        <span class="page-num">{{ i + 1 }} / {{ totalPages }}</span>
      </div>
    </div>

    <!-- Page Mode -->
    <div v-else class="page-container" @click.stop>
      <div class="page-viewer">
        <img
          :src="getImageSrc(currentPage)"
          :alt="`第${currentPage + 1}页`"
          class="page-img-single"
        />
      </div>
      <div class="page-nav" @click.stop>
        <button class="page-area left" @click="prevPage" :disabled="currentPage === 0" aria-label="上一页"></button>
        <button class="page-area right" @click="nextPage" :disabled="currentPage >= totalPages - 1" aria-label="下一页"></button>
      </div>
    </div>

    <!-- Bottom Toolbar -->
    <transition name="slide-up">
      <div v-if="showToolbar && !loading && chapter" class="toolbar bottom-bar" @click.stop>
        <span class="page-info">{{ (mode === 'page' ? currentPage + 1 : '—') }} / {{ totalPages }}</span>
        <input
          v-if="mode === 'page'"
          type="range"
          :min="0"
          :max="totalPages - 1"
          v-model.number="currentPage"
          class="page-slider"
        />
      </div>
    </transition>
  </div>
</template>

<style scoped>
.reader-view {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: #111;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* Toolbars */
.toolbar {
  position: absolute;
  left: 0;
  right: 0;
  z-index: 10;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(8px);
  padding: 10px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.top-bar {
  top: 0;
}

.bottom-bar {
  bottom: 0;
  justify-content: center;
  gap: 16px;
}

.tool-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  color: #fff;
  flex-shrink: 0;
}

.tool-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

.toolbar-title {
  flex: 1;
  font-size: 14px;
  font-weight: 500;
  color: #fff;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mode-switch {
  display: flex;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 6px;
  overflow: hidden;
}

.mode-btn {
  padding: 4px 14px;
  font-size: 12px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.6);
  transition: all 0.2s;
}

.mode-btn.active {
  background: var(--color-primary);
  color: #fff;
}

.page-info {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
  font-variant-numeric: tabular-nums;
}

.page-slider {
  width: 200px;
  max-width: 50vw;
  accent-color: var(--color-primary);
}

/* Scroll mode */
.scroll-container {
  flex: 1;
  overflow-y: auto;
  padding: 56px 0 50px;
}

.scroll-page {
  position: relative;
  max-width: 800px;
  margin: 0 auto;
}

.page-img {
  width: 100%;
  display: block;
}

.page-num {
  position: absolute;
  bottom: 8px;
  right: 12px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
  background: rgba(0, 0, 0, 0.5);
  padding: 2px 8px;
  border-radius: 4px;
}

/* Page mode */
.page-container {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  padding: 56px 0 50px;
}

.page-viewer {
  max-height: 100%;
  max-width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.page-img-single {
  max-height: calc(100vh - 120px);
  max-width: 100%;
  object-fit: contain;
}

.page-nav {
  position: absolute;
  inset: 56px 0 50px;
  display: flex;
}

.page-area {
  flex: 1;
  background: none;
  border: none;
  cursor: pointer;
}

.page-area:disabled {
  cursor: default;
}

.page-area.left:hover:not(:disabled) {
  background: linear-gradient(to right, rgba(0,0,0,0.1), transparent);
}

.page-area.right:hover:not(:disabled) {
  background: linear-gradient(to left, rgba(0,0,0,0.1), transparent);
}

/* States */
.loading-state,
.error-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: rgba(255, 255, 255, 0.6);
  gap: 12px;
}

.spinner-lg {
  width: 32px;
  height: 32px;
  border: 3px solid rgba(255, 255, 255, 0.15);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.retry-btn {
  padding: 8px 24px;
  background: var(--color-primary);
  color: #fff;
  border-radius: var(--radius-sm);
  font-weight: 500;
}

/* Transitions */
.slide-down-enter-active,
.slide-down-leave-active {
  transition: transform 0.25s ease, opacity 0.2s ease;
}
.slide-down-enter-from,
.slide-down-leave-to {
  transform: translateY(-100%);
  opacity: 0;
}

.slide-up-enter-active,
.slide-up-leave-active {
  transition: transform 0.25s ease, opacity 0.2s ease;
}
.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateY(100%);
  opacity: 0;
}
</style>
