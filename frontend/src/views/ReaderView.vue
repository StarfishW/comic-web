<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from "vue";
import { useRouter } from "vue-router";
import { getChapterDetail, getChapterImageUrl } from "../api";
import LazyImage from "../components/LazyImage.vue";
import ImageLoader from "../utils/imageLoader";

// 图片加载配置
const LOADING_CONFIG = {
  priorityPages: 10, // 优先加载的页数
  priorityDelay: 50, // 优先页面加载间隔（毫秒）
  normalDelay: 500, // 普通页面加载间隔（毫秒）
  maxConcurrent: 5, // 最大并发数
};

const props = defineProps({ photoId: { type: String, required: true } });
const router = useRouter();

const chapter = ref(null);
const loading = ref(true);
const error = ref(null);
const mode = ref("scroll"); // 'scroll' | 'page'
const currentPage = ref(0);
const showToolbar = ref(true);
const loadingProgress = ref(0);
const imageLoader = new ImageLoader({
  maxConcurrent: LOADING_CONFIG.maxConcurrent,
  sequential: true,
});
const lazyImageRefs = ref([]);
let loadingCancelled = false; // 用于取消加载

let hideTimer = null;

const totalPages = computed(() => chapter.value?.images?.length || 0);

function getImageSrc(index) {
  return getChapterImageUrl(props.photoId, index);
}

async function fetchChapter() {
  try {
    loading.value = true;
    error.value = null;
    loadingProgress.value = 0;
    loadingCancelled = false;
    imageLoader.clear();
    lazyImageRefs.value = []; // 清空旧的 refs

    chapter.value = await getChapterDetail(props.photoId);
    currentPage.value = 0;

    // 等待 DOM 更新后开始顺序加载
    await nextTick();

    // 再次等待，确保所有 refs 都已设置
    await nextTick();

    // 在滚动模式下启动顺序加载
    if (mode.value === "scroll") {
      // 添加一个小延迟，确保 refs 完全就绪
      setTimeout(() => {
        startSequentialLoading();
      }, 100);
    }
  } catch (e) {
    error.value = "加载失败: " + (e.response?.data?.detail || e.message);
  } finally {
    loading.value = false;
  }
}

// 顺序加载图片 - 优化版：支持并发加载
function startSequentialLoading() {
  const images = chapter.value?.images || [];
  let currentIndex = 0;
  let loadingCount = 0; // 当前正在加载的数量
  let completedCount = 0; // 已完成的数量
  loadingCancelled = false; // 重置取消标志

  console.log('[加载] 开始顺序加载', {
    totalImages: images.length,
    refsCount: lazyImageRefs.value.length,
    maxConcurrent: LOADING_CONFIG.maxConcurrent,
  });

  // 检查 refs 是否正确设置
  if (lazyImageRefs.value.length === 0) {
    console.error('[加载] lazyImageRefs 为空，无法加载图片！');
    return;
  }

  function loadNext() {
    // 检查是否已取消或已完成所有加载
    if (loadingCancelled || currentIndex >= images.length) return;

    // 控制并发数：确保不超过 maxConcurrent
    while (
      loadingCount < LOADING_CONFIG.maxConcurrent &&
      currentIndex < images.length &&
      !loadingCancelled
    ) {
      const indexToLoad = currentIndex;
      currentIndex++;
      loadingCount++;

      const ref = lazyImageRefs.value[indexToLoad];
      if (ref && !ref.isLoaded) {
        // 计算延迟：前N页快速，后续慢速
        const delay =
          indexToLoad < LOADING_CONFIG.priorityPages
            ? LOADING_CONFIG.priorityDelay * indexToLoad
            : LOADING_CONFIG.priorityDelay * LOADING_CONFIG.priorityPages +
              LOADING_CONFIG.normalDelay *
                (indexToLoad - LOADING_CONFIG.priorityPages);

        setTimeout(() => {
          if (loadingCancelled) {
            loadingCount--;
            return;
          }

          console.log(`[加载] 开始加载第 ${indexToLoad + 1} 页`);

          ref
            .loadImage()
            .then(() => {
              if (loadingCancelled) return;
              completedCount++;
              loadingCount--;
              loadingProgress.value = (completedCount / images.length) * 100;
              console.log(`[加载] 第 ${indexToLoad + 1} 页加载成功，进度: ${loadingProgress.value.toFixed(1)}%`);
              // 继续加载下一批
              loadNext();
            })
            .catch(() => {
              if (loadingCancelled) return;
              completedCount++;
              loadingCount--;
              console.error(`[加载] 第 ${indexToLoad + 1} 页加载失败`);
              // 加载失败也继续
              loadNext();
            });
        }, delay);
      } else {
        // 已加载或无效，直接跳过
        if (!ref) {
          console.warn(`[加载] 第 ${indexToLoad + 1} 页的 ref 不存在`);
        }
        loadingCount--;
        completedCount++;
        loadingProgress.value = (completedCount / images.length) * 100;
      }
    }
  }

  // 开始加载
  loadNext();
}

// 取消顺序加载
function cancelSequentialLoading() {
  loadingCancelled = true;
}

// 处理图片可见事件（懒加载触发）
function handleImageVisible(index) {
  // 当图片进入视口时，从该位置开始顺序加载
  const ref = lazyImageRefs.value[index];
  if (ref && !ref.isLoaded && !ref.isLoading) {
    ref.loadImage();
  }
}

// 预加载翻页模式的图片
function preloadPageImages() {
  if (mode.value !== "page") return;

  const indexes = [];
  // 当前页
  indexes.push(currentPage.value);
  // 下一页
  if (currentPage.value < totalPages.value - 1) {
    indexes.push(currentPage.value + 1);
  }
  // 上一页
  if (currentPage.value > 0) {
    indexes.push(currentPage.value - 1);
  }

  indexes.forEach((index, priority) => {
    const src = getImageSrc(index);
    imageLoader.add(src, priority);
  });
}

function prevPage() {
  if (currentPage.value > 0) currentPage.value--;
}

function nextPage() {
  if (currentPage.value < totalPages.value - 1) currentPage.value++;
}

function goBack() {
  if (chapter.value?.album_id) {
    router.push({
      name: "ComicDetail",
      params: { id: chapter.value.album_id },
    });
  } else {
    router.back();
  }
}

function toggleToolbar() {
  showToolbar.value = !showToolbar.value;
}

function handleKeydown(e) {
  if (mode.value !== "page") return;
  if (e.key === "ArrowLeft" || e.key === "ArrowUp") prevPage();
  if (e.key === "ArrowRight" || e.key === "ArrowDown") nextPage();
}

watch(() => props.photoId, fetchChapter);

// 监听模式切换
watch(mode, (newMode) => {
  if (newMode === "page") {
    // 切换到翻页模式，取消顺序加载
    cancelSequentialLoading();
    preloadPageImages();
  } else if (newMode === "scroll") {
    // 切换到滚动模式，重新启动顺序加载
    startSequentialLoading();
  }
});

// 监听翻页，预加载相邻页面
watch(currentPage, () => {
  if (mode.value === "page") {
    preloadPageImages();
  }
});

onMounted(() => {
  fetchChapter();
  document.addEventListener("keydown", handleKeydown);
});
onUnmounted(() => {
  document.removeEventListener("keydown", handleKeydown);
  cancelSequentialLoading();
  imageLoader.clear();
});
</script>

<template>
  <div class="reader-view" @click="toggleToolbar">
    <!-- Top Toolbar -->
    <transition name="slide-down">
      <div v-if="showToolbar" class="toolbar top-bar" @click.stop>
        <button class="tool-btn" @click="goBack" aria-label="返回">
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <path d="M19 12H5M12 19l-7-7 7-7" />
          </svg>
        </button>
        <span class="toolbar-title">{{ chapter?.title || "阅读中..." }}</span>
        <div class="mode-switch">
          <button
            :class="['mode-btn', { active: mode === 'scroll' }]"
            @click="mode = 'scroll'"
          >
            滚动
          </button>
          <button
            :class="['mode-btn', { active: mode === 'page' }]"
            @click="mode = 'page'"
          >
            翻页
          </button>
        </div>
      </div>
    </transition>

    <!-- Loading Progress Bar -->
    <transition name="fade">
      <div
        v-if="mode === 'scroll' && loadingProgress > 0 && loadingProgress < 100"
        class="progress-bar"
      >
        <div
          class="progress-fill"
          :style="{ width: loadingProgress + '%' }"
        ></div>
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
        <LazyImage
          :ref="
            (el) => {
              if (el) lazyImageRefs[i] = el;
            }
          "
          :src="getImageSrc(i)"
          :alt="`第${i + 1}页`"
          :sequential="true"
          class="page-img"
          @visible="handleImageVisible(i)"
        />
        <span class="page-num">{{ i + 1 }} / {{ totalPages }}</span>
      </div>
    </div>

    <!-- Page Mode -->
    <div v-else class="page-container" @click.stop>
      <div class="page-viewer">
        <LazyImage
          :src="getImageSrc(currentPage)"
          :alt="`第${currentPage + 1}页`"
          :sequential="false"
          class="page-img-single"
        />
      </div>
      <div class="page-nav" @click.stop>
        <button
          class="page-area left"
          @click="prevPage"
          :disabled="currentPage === 0"
          aria-label="上一页"
        ></button>
        <button
          class="page-area right"
          @click="nextPage"
          :disabled="currentPage >= totalPages - 1"
          aria-label="下一页"
        ></button>
      </div>
    </div>

    <!-- Bottom Toolbar -->
    <transition name="slide-up">
      <div
        v-if="showToolbar && !loading && chapter"
        class="toolbar bottom-bar"
        @click.stop
      >
        <span class="page-info"
          >{{ mode === "page" ? currentPage + 1 : "—" }} /
          {{ totalPages }}</span
        >
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

/* Loading Progress Bar */
.progress-bar {
  position: absolute;
  top: 56px;
  left: 0;
  right: 0;
  height: 3px;
  background: rgba(255, 255, 255, 0.1);
  z-index: 10;
}

.progress-fill {
  height: 100%;
  background: var(--color-primary);
  transition: width 0.3s ease;
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

.page-img :deep(.lazy-image) {
  display: block;
}

.page-img-single :deep(.lazy-image-wrapper) {
  max-height: calc(100vh - 120px);
  max-width: 100%;
  width: auto;
  height: auto;
}

.page-img-single :deep(.lazy-image) {
  max-height: calc(100vh - 120px);
  max-width: 100%;
  object-fit: contain;
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
  background: linear-gradient(to right, rgba(0, 0, 0, 0.1), transparent);
}

.page-area.right:hover:not(:disabled) {
  background: linear-gradient(to left, rgba(0, 0, 0, 0.1), transparent);
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

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.retry-btn {
  padding: 8px 24px;
  background: var(--color-primary);
  color: #fff;
  border-radius: var(--radius-sm);
  font-weight: 500;
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-down-enter-active,
.slide-down-leave-active {
  transition:
    transform 0.25s ease,
    opacity 0.2s ease;
}
.slide-down-enter-from,
.slide-down-leave-to {
  transform: translateY(-100%);
  opacity: 0;
}

.slide-up-enter-active,
.slide-up-leave-active {
  transition:
    transform 0.25s ease,
    opacity 0.2s ease;
}
.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateY(100%);
  opacity: 0;
}
</style>
