<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from "vue";
import { useRouter } from "vue-router";
import { getChapterDetail, getChapterImageUrl, startChapterCache, getChapterCacheStatus, getCachedImageUrl, getComicDetail } from "../api";
import { startChapterPdf, getChapterPdfStatus, getChapterPdfDownloadUrl } from '../api'
import LazyImage from "../components/LazyImage.vue";
import ImageLoader from "../utils/imageLoader";
import { viewMode } from '../utils/viewMode'

// 图片加载配置
const LOADING_CONFIG = {
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
const showEpisodeList = ref(false);
const episodeListRef = ref(null);
const imageLoader = new ImageLoader({
  maxConcurrent: LOADING_CONFIG.maxConcurrent,
  sequential: true,
});
const lazyImageRefs = ref([]);
const scrollContainerRef = ref(null);
const scrollPageRefs = ref([]);
let chapterRequestId = 0;
let sequentialStartTimer = null;
let scrollFrame = null;
let loadingCancelled = false; // 用于取消加载

// 缩放
const zoom = ref(1.0)
const ZOOM_MIN = 0.5
const ZOOM_MAX = 3.0
const ZOOM_STEP = 0.25

// 翻页模式下的拖拽平移（缩放 > 1 时可用）
const panX = ref(0)
const panY = ref(0)
const isPanning = ref(false)
let panStartX = 0
let panStartY = 0
let panOriginX = 0
let panOriginY = 0
const cacheStatus = ref(null)   // null | 'pending' | 'downloading' | 'ready' | 'error'
const cacheProgress = ref(0)
let cachePoller = null
const pdfStatus = ref(null)    // null | 'caching' | 'converting' | 'ready' | 'error'
const pdfProgress = ref(0)
const pdfPhase = ref('')
let pdfPoller = null
let pdfDownloadTriggered = false

function clearAsyncState() {
  if (cachePoller) {
    clearInterval(cachePoller)
    cachePoller = null
  }
  if (pdfPoller) {
    clearInterval(pdfPoller)
    pdfPoller = null
  }
  if (sequentialStartTimer) {
    clearTimeout(sequentialStartTimer)
    sequentialStartTimer = null
  }
  if (scrollFrame) {
    cancelAnimationFrame(scrollFrame)
    scrollFrame = null
  }
}

function startCachePolling(albumId, photoId, requestId) {
  if (cachePoller) clearInterval(cachePoller)
  cachePoller = setInterval(async () => {
    try {
      const data = await getChapterCacheStatus(albumId, photoId)
      if (requestId !== chapterRequestId) return
      cacheStatus.value = data.status
      cacheProgress.value = data.progress || 0
      if (data.status === 'ready' || data.status === 'error') {
        clearInterval(cachePoller)
        cachePoller = null
      }
    } catch {
      clearInterval(cachePoller)
      cachePoller = null
    }
  }, 1000)
}

function startPdfPolling(albumId, photoId, requestId) {
  if (pdfPoller) clearInterval(pdfPoller)
  pdfPoller = setInterval(async () => {
    try {
      const data = await getChapterPdfStatus(albumId, photoId)
      if (requestId !== chapterRequestId) return
      pdfStatus.value = data.status
      pdfProgress.value = data.progress || 0
      pdfPhase.value = data.phase || ''
      if (data.status === 'ready' || data.status === 'error') {
        clearInterval(pdfPoller)
        pdfPoller = null
        if (data.status === 'ready' && !pdfDownloadTriggered) {
          pdfDownloadTriggered = true
          triggerPdfDownload(albumId, photoId)
        }
      }
    } catch {
      clearInterval(pdfPoller)
      pdfPoller = null
    }
  }, 1000)
}

function triggerPdfDownload(albumId, photoId) {
  const a = document.createElement('a')
  a.href = getChapterPdfDownloadUrl(albumId, photoId)
  a.download = `JMComic_${photoId}.pdf`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

function zoomIn() {
  zoom.value = Math.min(ZOOM_MAX, parseFloat((zoom.value + ZOOM_STEP).toFixed(2)))
}
function zoomOut() {
  zoom.value = Math.max(ZOOM_MIN, parseFloat((zoom.value - ZOOM_STEP).toFixed(2)))
  if (zoom.value <= 1) { panX.value = 0; panY.value = 0 }
}
function resetZoom() {
  zoom.value = 1.0
  panX.value = 0
  panY.value = 0
}

// Ctrl + 滚轮缩放
function handleWheel(e) {
  if (!e.ctrlKey && !e.metaKey) return
  e.preventDefault()
  e.deltaY < 0 ? zoomIn() : zoomOut()
}

// 翻页模式双击切换 2x / 1x
function handleDoubleClick(e) {
  e.stopPropagation()
  if (zoom.value !== 1.0) {
    resetZoom()
  } else {
    zoom.value = 2.0
  }
}

// 捏合缩放辅助
function getTouchDist(touches) {
  const dx = touches[0].clientX - touches[1].clientX
  const dy = touches[0].clientY - touches[1].clientY
  return Math.sqrt(dx * dx + dy * dy)
}

// ---- 翻页模式：拖拽平移 + 捏合缩放 ----
let pinchStartDist = 0
let pinchStartZoom = 1

function onPanStart(e) {
  if (e.touches && e.touches.length === 2) {
    // 双指捏合开始
    pinchStartDist = getTouchDist(e.touches)
    pinchStartZoom = zoom.value
    e.preventDefault()
    return
  }
  if (zoom.value <= 1) return
  isPanning.value = true
  const p = e.touches ? e.touches[0] : e
  panStartX = p.clientX
  panStartY = p.clientY
  panOriginX = panX.value
  panOriginY = panY.value
  e.preventDefault()
}
function onPanMove(e) {
  if (e.touches && e.touches.length === 2) {
    // 捏合缩放
    e.preventDefault()
    const dist = getTouchDist(e.touches)
    const scale = dist / pinchStartDist
    zoom.value = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN,
      parseFloat((pinchStartZoom * scale).toFixed(2))
    ))
    if (zoom.value <= 1) { panX.value = 0; panY.value = 0 }
    return
  }
  if (!isPanning.value) return
  e.preventDefault()
  const p = e.touches ? e.touches[0] : e
  panX.value = panOriginX + (p.clientX - panStartX)
  panY.value = panOriginY + (p.clientY - panStartY)
}
function onPanEnd(e) {
  if (e?.touches?.length === 0 || !e?.touches) {
    isPanning.value = false
    pinchStartDist = 0
  }
}

// ---- 滚动模式：捏合缩放 ----
let scrollPinchActive = false
let scrollPinchStartDist = 0
let scrollPinchStartZoom = 1

function onScrollTouchStart(e) {
  if (e.touches.length === 2) {
    scrollPinchActive = true
    scrollPinchStartDist = getTouchDist(e.touches)
    scrollPinchStartZoom = zoom.value
    e.preventDefault()
  }
}
function onScrollTouchMove(e) {
  if (!scrollPinchActive || e.touches.length !== 2) return
  e.preventDefault()
  const dist = getTouchDist(e.touches)
  zoom.value = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN,
    parseFloat((scrollPinchStartZoom * dist / scrollPinchStartDist).toFixed(2))
  ))
}
function onScrollTouchEnd(e) {
  if (e.touches.length < 2) scrollPinchActive = false
}

// 滚动模式下追踪当前页
function updateCurrentPageFromScroll() {
  if (!scrollContainerRef.value) return;
  const container = scrollContainerRef.value;
  const midPoint = container.scrollTop + container.clientHeight / 2;
  let closest = 0;
  let minDist = Infinity;
  scrollPageRefs.value.forEach((el, i) => {
    if (!el) return;
    const center = el.offsetTop + el.offsetHeight / 2;
    const dist = Math.abs(center - midPoint);
    if (dist < minDist) {
      minDist = dist;
      closest = i;
    }
  });
  currentPage.value = closest;
}

function handleScroll() {
  if (scrollFrame) return;
  scrollFrame = requestAnimationFrame(() => {
    scrollFrame = null;
    updateCurrentPageFromScroll();
  });
}

const totalPages = computed(() => chapter.value?.images?.length || 0);
const albumId = computed(() => chapter.value?.album_id || '')

const episodeList = ref([])

const currentEpisodeIndex = computed(() =>
  episodeList.value.findIndex(ep => ep.id === props.photoId)
)
const prevEpisode = computed(() =>
  currentEpisodeIndex.value > 0 ? episodeList.value[currentEpisodeIndex.value - 1] : null
)
const nextEpisode = computed(() =>
  currentEpisodeIndex.value !== -1 && currentEpisodeIndex.value < episodeList.value.length - 1
    ? episodeList.value[currentEpisodeIndex.value + 1]
    : null
)

function epTitle(ep) {
  return ep?.title || `第${ep?.sort}话`
}

function goToEpisode(ep) {
  if (!ep) return
  router.push({ name: 'Reader', params: { photoId: ep.id } })
}

function getImageSrc(index) {
  if (viewMode.value === 'cache' && cacheStatus.value === 'ready') {
    return getCachedImageUrl(albumId.value, props.photoId, index)
  }
  return getChapterImageUrl(props.photoId, index);
}

async function fetchChapter() {
  const requestId = ++chapterRequestId;
  try {
    loading.value = true;
    error.value = null;
    loadingCancelled = false;
    resetZoom()
    imageLoader.clear();
    lazyImageRefs.value = []; // 清空旧的 refs
    scrollPageRefs.value = []; // 清空旧的 DOM 引用
    cacheStatus.value = null
    cacheProgress.value = 0
    pdfStatus.value = null
    pdfProgress.value = 0
    pdfPhase.value = ''
    pdfDownloadTriggered = false
    episodeList.value = []
    clearAsyncState()

    chapter.value = await getChapterDetail(props.photoId);
    if (requestId !== chapterRequestId) return;

    // 后台拉取本漫画章节列表（不 await，不影响加载速度）
    if (chapter.value.album_id) {
      episodeList.value = [] // 重置，防止上一章节残留
      getComicDetail(chapter.value.album_id)
        .then(data => {
          if (requestId === chapterRequestId) {
            episodeList.value = data.episodes || []
          }
        })
        .catch(() => {})
    }

    // 缓存模式处理
    if (viewMode.value === 'cache') {
      const statusData = await getChapterCacheStatus(albumId.value, props.photoId)
      if (requestId !== chapterRequestId) return;
      if (statusData.status === 'ready') {
        cacheStatus.value = 'ready'
        cacheProgress.value = 100
      } else {
        cacheStatus.value = statusData.status === 'not_started' ? 'pending' : statusData.status
        cacheProgress.value = statusData.progress || 0
        await startChapterCache(albumId.value, props.photoId)
        if (requestId !== chapterRequestId) return;
        startCachePolling(albumId.value, props.photoId, requestId)
      }
    } else if (viewMode.value === 'pdf') {
      const statusData = await getChapterPdfStatus(albumId.value, props.photoId)
      if (requestId !== chapterRequestId) return;
      if (statusData.status === 'ready') {
        pdfStatus.value = 'ready'
        pdfProgress.value = 100
        if (!pdfDownloadTriggered) {
          pdfDownloadTriggered = true
          triggerPdfDownload(albumId.value, props.photoId)
        }
      } else {
        pdfStatus.value = 'caching'
        await startChapterPdf(albumId.value, props.photoId)
        if (requestId !== chapterRequestId) return;
        startPdfPolling(albumId.value, props.photoId, requestId)
      }
    } else {
      cacheStatus.value = 'ready'
    }

    currentPage.value = 0;

    // 等待 DOM 更新后开始顺序加载
    await nextTick();
    if (requestId !== chapterRequestId) return;

    // 再次等待，确保所有 refs 都已设置
    await nextTick();

    // 在滚动模式下启动顺序加载
    if (mode.value === "scroll") {
      // 添加一个小延迟，确保 refs 完全就绪
      sequentialStartTimer = setTimeout(() => {
        sequentialStartTimer = null;
        if (requestId === chapterRequestId) {
          startSequentialLoading();
        }
      }, 100);
    }
  } catch (e) {
    if (requestId !== chapterRequestId) return;
    error.value = "加载失败: " + (e.response?.data?.detail || e.message);
  } finally {
    if (requestId === chapterRequestId) {
      loading.value = false;
    }
  }
}

// 顺序加载图片 - 纯并发槽控制，无延迟
function startSequentialLoading() {
  const images = chapter.value?.images || [];
  if (!images.length || lazyImageRefs.value.length === 0) return;

  loadingCancelled = false;
  let nextIndex = 0;
  let completed = 0;
  const total = images.length;

  function tryLoadNext() {
    if (loadingCancelled || nextIndex >= total) return;
    const i = nextIndex++;
    const ref = lazyImageRefs.value[i];

    function onDone() {
      if (loadingCancelled) return;
      completed++;
      tryLoadNext();
    }

    if (!ref || ref.isLoaded) {
      onDone();
      return;
    }
    ref.loadImage().then(onDone).catch(onDone);
  }

  const concurrency = Math.min(LOADING_CONFIG.maxConcurrent, total);
  for (let i = 0; i < concurrency; i++) tryLoadNext();
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

function handleReaderClick() {
  if (showEpisodeList.value) {
    showEpisodeList.value = false;
    return;
  }
  showToolbar.value = !showToolbar.value;
}

async function toggleEpisodeList() {
  showEpisodeList.value = !showEpisodeList.value;
  if (showEpisodeList.value) {
    await nextTick();
    episodeListRef.value?.querySelector('.ep-item.active')?.scrollIntoView({ block: 'center' });
  }
}

function handleKeydown(e) {
  if (mode.value !== "page") return;
  if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
    if (currentPage.value === 0 && prevEpisode.value) goToEpisode(prevEpisode.value)
    else prevPage()
  }
  if (e.key === "ArrowRight" || e.key === "ArrowDown") {
    if (currentPage.value >= totalPages.value - 1 && nextEpisode.value) goToEpisode(nextEpisode.value)
    else nextPage()
  }
  if (e.key === '+' || e.key === '=') zoomIn()
  if (e.key === '-') zoomOut()
  if (e.key === '0') resetZoom()
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
  chapterRequestId += 1;
  document.removeEventListener("keydown", handleKeydown);
  cancelSequentialLoading();
  clearAsyncState();
  imageLoader.clear();
});
</script>

<template>
  <div class="reader-view" @click="handleReaderClick">
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
        <button
          :class="['tool-btn', 'toc-btn', { active: showEpisodeList }]"
          @click.stop="toggleEpisodeList"
          :title="showEpisodeList ? '关闭目录' : '目录'"
          aria-label="目录"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <line x1="3" y1="6" x2="21" y2="6"/>
            <line x1="3" y1="12" x2="15" y2="12"/>
            <line x1="3" y1="18" x2="18" y2="18"/>
          </svg>
        </button>
      </div>
    </transition>

    <!-- Drawer Mask -->
    <transition name="mask-fade">
      <div v-if="showEpisodeList" class="drawer-mask" @click="showEpisodeList = false"></div>
    </transition>

    <!-- Episode List Drawer -->
    <transition name="drawer">
      <div v-if="showEpisodeList" class="episode-drawer" @click.stop>
        <div class="drawer-header">
          <span class="drawer-title">目录</span>
          <span class="drawer-count" v-if="episodeList.length">{{ episodeList.length }} 话</span>
          <button class="drawer-close" @click="showEpisodeList = false" aria-label="关闭">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
        <div class="drawer-list" ref="episodeListRef">
          <div v-if="!episodeList.length" class="drawer-empty">
            <div class="drawer-spinner"></div>
            目录加载中…
          </div>
          <button
            v-for="ep in episodeList"
            :key="ep.id"
            :class="['ep-item', { active: ep.id === photoId }]"
            @click="goToEpisode(ep); showEpisodeList = false"
          >
            <span class="ep-item-indicator" v-if="ep.id === photoId"></span>
            <span class="ep-item-title">{{ epTitle(ep) }}</span>
            <svg v-if="ep.id === photoId" class="ep-item-check" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
          </button>
        </div>
      </div>
    </transition>

    <!-- Cache Mode Overlay -->
    <div
      v-if="viewMode === 'cache' && cacheStatus !== 'ready' && !loading"
      class="cache-overlay"
      @click.stop
    >
      <div v-if="cacheStatus === 'error'" class="cache-message">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="1.5">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="12"/>
          <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        <p>缓存失败，请返回重试</p>
      </div>
      <div v-else class="cache-message">
        <div class="cache-spinner"></div>
        <p class="cache-text">正在缓存章节</p>
        <div class="cache-bar-wrap">
          <div class="cache-bar-fill" :style="{ width: cacheProgress + '%' }"></div>
        </div>
        <span class="cache-pct">{{ cacheProgress }}%</span>
      </div>
    </div>

    <!-- PDF Mode Overlay -->
    <div
      v-if="viewMode === 'pdf' && pdfStatus !== 'ready' && !loading"
      class="cache-overlay"
      @click.stop
    >
      <div v-if="pdfStatus === 'error'" class="cache-message">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="1.5">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="12"/>
          <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        <p>PDF 生成失败，请返回重试</p>
        <button class="retry-btn" @click="goBack">返回</button>
      </div>
      <div v-else class="cache-message">
        <div class="cache-spinner"></div>
        <p class="cache-text">
          {{ pdfPhase === 'converting' ? '正在合成 PDF...' : '正在下载图片...' }}
        </p>
        <div class="cache-bar-wrap">
          <div class="cache-bar-fill" :style="{ width: pdfProgress + '%' }"></div>
        </div>
        <span class="cache-pct">{{ pdfProgress }}%</span>
      </div>
    </div>

    <!-- PDF Ready Overlay -->
    <div
      v-if="viewMode === 'pdf' && pdfStatus === 'ready' && !loading"
      class="cache-overlay"
      @click.stop
    >
      <div class="cache-message">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" stroke-width="1.5">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
          <polyline points="9 12 11 14 15 10" stroke="var(--color-primary)" stroke-width="2"/>
        </svg>
        <p class="cache-text" style="color: rgba(255,255,255,0.9)">PDF 已生成，正在下载</p>
        <a
          :href="getChapterPdfDownloadUrl(albumId, photoId)"
          :download="`JMComic_${photoId}.pdf`"
          class="pdf-manual-link"
        >如未自动下载，点此下载</a>
        <button class="retry-btn" style="margin-top:8px" @click="goBack">返回</button>
      </div>
    </div>

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
    <template v-else-if="mode === 'scroll'">
      <div
        ref="scrollContainerRef"
        class="scroll-container"
        v-show="(viewMode === 'direct') || (viewMode === 'cache' && cacheStatus === 'ready')"
        @scroll="handleScroll"
        @wheel="handleWheel"
        @touchstart="onScrollTouchStart"
        @touchmove="onScrollTouchMove"
        @touchend="onScrollTouchEnd"
      >
        <div v-for="(img, i) in chapter.images" :key="i" :ref="(el) => { if (el) scrollPageRefs[i] = el }" class="scroll-page" :style="{ maxWidth: `${800 * zoom}px` }">
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
        </div>

        <!-- 章节导航（滚动到底部后可见） -->
        <div v-if="prevEpisode || nextEpisode" class="episode-nav-scroll">
          <button v-if="prevEpisode" class="ep-nav-btn" @click="goToEpisode(prevEpisode)">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
            上一话：{{ epTitle(prevEpisode) }}
          </button>
          <button v-if="nextEpisode" class="ep-nav-btn ep-nav-next" @click="goToEpisode(nextEpisode)">
            下一话：{{ epTitle(nextEpisode) }}
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
          </button>
        </div>
      </div>
    </template>

    <!-- Page Mode -->
    <template v-else>
      <div
        class="page-container"
        v-show="(viewMode === 'direct') || (viewMode === 'cache' && cacheStatus === 'ready')"
        @click.stop
      >
        <div
          class="page-viewer"
          :style="{
            transform: `scale(${zoom}) translate(${panX / zoom}px, ${panY / zoom}px)`,
            cursor: zoom > 1 ? (isPanning ? 'grabbing' : 'grab') : 'default',
            transformOrigin: 'center center',
          }"
          @dblclick="handleDoubleClick"
          @mousedown="onPanStart"
          @mousemove="onPanMove"
          @mouseup="onPanEnd"
          @mouseleave="onPanEnd"
          @touchstart="onPanStart"
          @touchmove="onPanMove"
          @touchend="onPanEnd"
          @wheel.prevent="handleWheel"
        >
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
    </template>

    <!-- Bottom Toolbar -->
    <transition name="slide-up">
      <div
        v-if="showToolbar && !loading && chapter"
        class="toolbar bottom-bar"
        @click.stop
      >
        <div class="zoom-controls" @click.stop>
          <button class="zoom-btn" @click="zoomOut" :disabled="zoom <= ZOOM_MIN" title="缩小 (-)">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"/></svg>
          </button>
          <button class="zoom-pct" @click="resetZoom" title="重置缩放">{{ Math.round(zoom * 100) }}%</button>
          <button class="zoom-btn" @click="zoomIn" :disabled="zoom >= ZOOM_MAX" title="放大 (+)">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          </button>
        </div>
        <span class="page-info">{{ currentPage + 1 }} / {{ totalPages }}</span>
        <!-- 翻页模式章节导航 -->
        <div v-if="mode === 'page'" class="episode-nav-page">
          <button
            v-if="currentPage === 0 && prevEpisode"
            class="ep-nav-page-btn"
            @click="goToEpisode(prevEpisode)"
            :title="`上一话：${epTitle(prevEpisode)}`"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/><polyline points="8 18 2 12 8 6"/></svg>
            上一话
          </button>
          <button
            v-if="currentPage >= totalPages - 1 && nextEpisode"
            class="ep-nav-page-btn ep-nav-page-next"
            @click="goToEpisode(nextEpisode)"
            :title="`下一话：${epTitle(nextEpisode)}`"
          >
            下一话
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/><polyline points="16 18 22 12 16 6"/></svg>
          </button>
        </div>
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
  justify-content: space-between;
  gap: 12px;
  padding: 10px 20px;
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
  min-height: 200px;
}

.page-img {
  width: 100%;
  display: block;
}

.page-img :deep(.lazy-image-wrapper) {
  height: auto;
}

.page-img :deep(.lazy-image) {
  display: block;
  height: auto;
  object-fit: initial;
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

/* Cache overlay */
.cache-overlay {
  position: absolute;
  inset: 0;
  z-index: 20;
  background: rgba(17, 17, 17, 0.95);
  display: flex;
  align-items: center;
  justify-content: center;
}

.cache-message {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  color: rgba(255, 255, 255, 0.85);
}

.cache-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(255, 255, 255, 0.15);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.cache-text {
  font-size: 15px;
  font-weight: 500;
}

.cache-bar-wrap {
  width: 200px;
  height: 4px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 2px;
  overflow: hidden;
}

.cache-bar-fill {
  height: 100%;
  background: var(--color-primary);
  border-radius: 2px;
  transition: width 0.4s ease;
}

.cache-pct {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.5);
  font-variant-numeric: tabular-nums;
}

.pdf-manual-link {
  font-size: 13px;
  color: var(--color-primary);
  text-decoration: underline;
  cursor: pointer;
}

/* 缩放控件 */
.zoom-controls {
  display: flex;
  align-items: center;
  gap: 2px;
}

.zoom-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  color: rgba(255, 255, 255, 0.7);
  transition: background 0.15s, color 0.15s;
}
.zoom-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
}
.zoom-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.zoom-pct {
  min-width: 44px;
  height: 28px;
  padding: 0 4px;
  font-size: 12px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.7);
  font-variant-numeric: tabular-nums;
  border-radius: 4px;
  transition: background 0.15s;
  text-align: center;
}
.zoom-pct:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

/* 章节导航 - 滚动模式底部 */
.episode-nav-scroll {
  max-width: 800px;
  margin: 0 auto;
  padding: 24px 16px 40px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ep-nav-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 20px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: var(--radius-md);
  color: rgba(255, 255, 255, 0.75);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;
}
.ep-nav-btn:hover {
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
  border-color: rgba(255, 255, 255, 0.25);
}
.ep-nav-next {
  justify-content: flex-end;
}

/* 章节导航 - 翻页模式底部工具栏 */
.episode-nav-page {
  display: flex;
  gap: 6px;
}

.ep-nav-page-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 12px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 14px;
  color: rgba(255, 255, 255, 0.8);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}
.ep-nav-page-btn:hover {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: #fff;
}

/* TOC 按钮 */
.toc-btn {
  flex-shrink: 0;
  color: rgba(255, 255, 255, 0.7);
  transition: background 0.15s, color 0.15s;
}
.toc-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}
.toc-btn.active {
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
}

/* 遮罩 */
.drawer-mask {
  position: absolute;
  inset: 0;
  z-index: 15;
  background: rgba(0, 0, 0, 0.5);
}

/* 抽屉 */
.episode-drawer {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  z-index: 16;
  width: min(320px, 85vw);
  display: flex;
  flex-direction: column;
  background: rgba(18, 18, 18, 0.97);
  backdrop-filter: blur(12px);
  border-left: 1px solid rgba(255, 255, 255, 0.08);
}

.drawer-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 16px 13px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  flex-shrink: 0;
}

.drawer-title {
  font-size: 15px;
  font-weight: 600;
  color: #fff;
  letter-spacing: 0.02em;
}

.drawer-count {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.35);
  font-variant-numeric: tabular-nums;
}

.drawer-close {
  margin-left: auto;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  color: rgba(255, 255, 255, 0.5);
  transition: background 0.15s, color 0.15s;
  flex-shrink: 0;
}
.drawer-close:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

.drawer-list {
  flex: 1;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 6px 0;
}
.drawer-list::-webkit-scrollbar {
  width: 3px;
}
.drawer-list::-webkit-scrollbar-track {
  background: transparent;
}
.drawer-list::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.12);
  border-radius: 2px;
}

.drawer-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 48px 16px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.35);
}

.drawer-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.15);
  border-top-color: rgba(255, 255, 255, 0.5);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  flex-shrink: 0;
}

.ep-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 10px 16px 10px 20px;
  text-align: left;
  font-size: 13.5px;
  color: rgba(255, 255, 255, 0.6);
  transition: background 0.12s, color 0.12s;
  line-height: 1.4;
}
.ep-item:hover {
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.9);
}
.ep-item.active {
  color: #fff;
  background: rgba(255, 255, 255, 0.04);
}

.ep-item-indicator {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 60%;
  min-height: 18px;
  background: var(--color-primary);
  border-radius: 0 2px 2px 0;
}

.ep-item-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ep-item.active .ep-item-title {
  font-weight: 500;
}

.ep-item-check {
  flex-shrink: 0;
  color: var(--color-primary);
  opacity: 0.9;
}

/* 抽屉动画 */
.drawer-enter-active,
.drawer-leave-active {
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.drawer-enter-from,
.drawer-leave-to {
  transform: translateX(100%);
}

.mask-fade-enter-active,
.mask-fade-leave-active {
  transition: opacity 0.25s ease;
}
.mask-fade-enter-from,
.mask-fade-leave-to {
  opacity: 0;
}
</style>
