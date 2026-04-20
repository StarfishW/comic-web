<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from "vue";
import { useRouter } from "vue-router";
import * as api from "../api";
import LazyImage from "../components/LazyImage.vue";
import ImageLoader from "../utils/imageLoader";
import { viewMode } from '../utils/viewMode'
import { setDocumentTitle, resetDocumentTitle } from '../utils/documentTitle'
import {
  buildReadingProgressPayload,
  formatEpisodeProgress,
  mergeEpisodesWithReadingState,
  normalizeReadingState,
} from '../utils/reading'

const LOADING_CONFIG = {
  maxConcurrent: 5,
};

const props = defineProps({ photoId: { type: String, required: true } });
const router = useRouter();

const chapter = ref(null);
const loading = ref(true);
const error = ref(null);
const mode = ref("scroll");
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
let loadingCancelled = false;
let persistTimer = null;
let pendingProgressPayload = null;
let lastPersistFingerprint = '';

const zoom = ref(1.0)
const ZOOM_MIN = 0.5
const ZOOM_MAX = 3.0
const ZOOM_STEP = 0.25

const panX = ref(0)
const panY = ref(0)
const isPanning = ref(false)
let panStartX = 0
let panStartY = 0
let panOriginX = 0
let panOriginY = 0
const cacheStatus = ref(null)
const cacheProgress = ref(0)
let cachePoller = null
const pdfStatus = ref(null)
const pdfProgress = ref(0)
const pdfPhase = ref('')
let pdfPoller = null
let pdfDownloadTriggered = false
const readingState = ref(normalizeReadingState({}, ''))

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

function clearPersistTimer() {
  if (persistTimer) {
    clearTimeout(persistTimer)
    persistTimer = null
  }
}

function createPersistFingerprint(payload) {
  if (!payload) return ''
  return `${payload.album_id}:${payload.photo_id}:${payload.page_index}:${payload.total_pages}`
}

function startCachePolling(albumId, photoId, requestId) {
  if (cachePoller) clearInterval(cachePoller)
  cachePoller = setInterval(async () => {
    try {
      const data = await api.getChapterCacheStatus(albumId, photoId)
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
      const data = await api.getChapterPdfStatus(albumId, photoId)
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
  const anchor = document.createElement('a')
  anchor.href = api.getChapterPdfDownloadUrl(albumId, photoId)
  anchor.download = `JMComic_${photoId}.pdf`
  document.body.appendChild(anchor)
  anchor.click()
  document.body.removeChild(anchor)
}

function zoomIn() {
  zoom.value = Math.min(ZOOM_MAX, parseFloat((zoom.value + ZOOM_STEP).toFixed(2)))
}
function zoomOut() {
  zoom.value = Math.max(ZOOM_MIN, parseFloat((zoom.value - ZOOM_STEP).toFixed(2)))
  if (zoom.value <= 1) {
    panX.value = 0
    panY.value = 0
  }
}
function resetZoom() {
  zoom.value = 1.0
  panX.value = 0
  panY.value = 0
}

function handleWheel(e) {
  if (!e.ctrlKey && !e.metaKey) return
  e.preventDefault()
  e.deltaY < 0 ? zoomIn() : zoomOut()
}

function handleDoubleClick(e) {
  e.stopPropagation()
  if (zoom.value !== 1.0) {
    resetZoom()
  } else {
    zoom.value = 2.0
  }
}

function getTouchDist(touches) {
  const dx = touches[0].clientX - touches[1].clientX
  const dy = touches[0].clientY - touches[1].clientY
  return Math.sqrt(dx * dx + dy * dy)
}

let pinchStartDist = 0
let pinchStartZoom = 1

function onPanStart(e) {
  if (e.touches && e.touches.length === 2) {
    pinchStartDist = getTouchDist(e.touches)
    pinchStartZoom = zoom.value
    e.preventDefault()
    return
  }
  if (zoom.value <= 1) return
  isPanning.value = true
  const point = e.touches ? e.touches[0] : e
  panStartX = point.clientX
  panStartY = point.clientY
  panOriginX = panX.value
  panOriginY = panY.value
  e.preventDefault()
}
function onPanMove(e) {
  if (e.touches && e.touches.length === 2) {
    e.preventDefault()
    const dist = getTouchDist(e.touches)
    const scale = dist / pinchStartDist
    zoom.value = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN,
      parseFloat((pinchStartZoom * scale).toFixed(2))
    ))
    if (zoom.value <= 1) {
      panX.value = 0
      panY.value = 0
    }
    return
  }
  if (!isPanning.value) return
  e.preventDefault()
  const point = e.touches ? e.touches[0] : e
  panX.value = panOriginX + (point.clientX - panStartX)
  panY.value = panOriginY + (point.clientY - panStartY)
}
function onPanEnd(e) {
  if (e?.touches?.length === 0 || !e?.touches) {
    isPanning.value = false
    pinchStartDist = 0
  }
}

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

function clampPageIndex(index, total = totalPages.value) {
  const safeIndex = Number.isFinite(index) ? Math.trunc(index) : 0
  const maxIndex = total > 0 ? total - 1 : 0
  return Math.min(Math.max(safeIndex, 0), Math.max(maxIndex, 0))
}

function updateCurrentPageFromScroll() {
  if (!scrollContainerRef.value) return
  const container = scrollContainerRef.value
  const midPoint = container.scrollTop + container.clientHeight / 2
  let closest = 0
  let minDist = Infinity

  scrollPageRefs.value.forEach((el, index) => {
    if (!el) return
    const center = el.offsetTop + el.offsetHeight / 2
    const distance = Math.abs(center - midPoint)
    if (distance < minDist) {
      minDist = distance
      closest = index
    }
  })

  currentPage.value = closest
}

function handleScroll() {
  if (scrollFrame) return
  scrollFrame = requestAnimationFrame(() => {
    scrollFrame = null
    updateCurrentPageFromScroll()
  })
}

const totalPages = computed(() => chapter.value?.images?.length || 0);
const albumId = computed(() => chapter.value?.album_id || '')

const episodeList = ref([])
const albumTitle = ref('')
const albumAuthor = ref('')
const episodeListWithState = computed(() =>
  mergeEpisodesWithReadingState(episodeList.value, readingState.value),
)

const currentEpisodeIndex = computed(() =>
  episodeListWithState.value.findIndex(ep => String(ep.id) === String(props.photoId))
)
const currentEpisodeMeta = computed(() =>
  currentEpisodeIndex.value === -1 ? null : episodeListWithState.value[currentEpisodeIndex.value]
)
const prevEpisode = computed(() =>
  currentEpisodeIndex.value > 0 ? episodeListWithState.value[currentEpisodeIndex.value - 1] : null
)
const nextEpisode = computed(() =>
  currentEpisodeIndex.value !== -1 && currentEpisodeIndex.value < episodeListWithState.value.length - 1
    ? episodeListWithState.value[currentEpisodeIndex.value + 1]
    : null
)
const currentChapterReading = computed(() =>
  readingState.value.chapterMap?.[props.photoId] || null,
)
const currentChapterBadge = computed(() => {
  const progress = currentChapterReading.value
  if (!progress) return ''
  if (progress.isRead) return '已读'
  if (progress.progress > 0) return `${progress.progress}%`
  if (progress.visited) return '已看'
  return ''
})

function epTitle(ep) {
  return ep?.title || `第${ep?.sort}话`
}

function getEpisodeStateLabel(ep) {
  const progress = ep?.reading
  if (!progress) return ''
  if (ep.isLastRead && !progress.isRead) {
    return progress.progress > 0 ? `继续 ${progress.progress}%` : '继续阅读'
  }
  return formatEpisodeProgress(progress)
}

function getEpisodeStateClass(ep) {
  const progress = ep?.reading
  if (!progress) return ''
  if (ep.isLastRead && !progress.isRead) return 'ep-item-state--continue'
  if (progress.isRead) return 'ep-item-state--read'
  if (progress.progress > 0) return 'ep-item-state--progress'
  return 'ep-item-state--visited'
}

const currentEpisodeTitle = computed(() => {
  if (currentEpisodeMeta.value?.title) return currentEpisodeMeta.value.title
  if (chapter.value?.title && chapter.value.title !== albumTitle.value) return chapter.value.title

  const sort = currentEpisodeMeta.value?.sort || chapter.value?.album_index
  return sort ? `第${sort}话` : `章节 ${props.photoId}`
})

const readerTitle = computed(() => {
  const album = albumTitle.value || chapter.value?.title || ''
  const episode = currentEpisodeTitle.value
  if (album && episode && episode !== album) return `${album} · ${episode}`
  return album || episode || '阅读中...'
})

function getEpisodeMetaById(photoId) {
  return episodeListWithState.value.find((episode) => String(episode.id) === String(photoId)) || null
}

function getEpisodeTitleById(photoId) {
  if (!photoId) return ''
  const episode = getEpisodeMetaById(photoId)
  if (episode) return epTitle(episode)
  if (photoId === props.photoId) return currentEpisodeTitle.value
  return `章节 ${photoId}`
}

function getEpisodeSortById(photoId) {
  const episode = getEpisodeMetaById(photoId)
  if (episode?.sort !== undefined && episode?.sort !== null) return episode.sort
  if (photoId === props.photoId) return chapter.value?.album_index ?? null
  return null
}

function applyReadingState(rawState, albumIdOverride = '') {
  readingState.value = normalizeReadingState(rawState, albumIdOverride || chapter.value?.album_id || '')
}

function buildPersistContext({
  photoId = props.photoId,
  pageIndex = currentPage.value,
} = {}) {
  if (!chapter.value?.album_id) return null

  return {
    albumId: chapter.value.album_id,
    photoId,
    currentPageIndex: clampPageIndex(pageIndex, totalPages.value),
    totalPages: totalPages.value,
    comicTitle: albumTitle.value || chapter.value?.title || '',
    chapterTitle: getEpisodeTitleById(photoId),
    author: albumAuthor.value || chapter.value?.author || '',
    sort: getEpisodeSortById(photoId),
    mode: mode.value,
  }
}

function applyLocalProgress(payload) {
  if (!payload?.photo_id) return

  const updatedAt = Date.now()
  const chapterMap = { ...(readingState.value.chapterMap || {}) }
  const existing = chapterMap[payload.photo_id] || {}

  chapterMap[payload.photo_id] = {
    ...existing,
    albumId: payload.album_id,
    photoId: payload.photo_id,
    title: payload.chapter_title || existing.title || getEpisodeTitleById(payload.photo_id),
    sort: payload.sort ?? existing.sort ?? getEpisodeSortById(payload.photo_id),
    pageIndex: payload.page_index ?? existing.pageIndex ?? 0,
    currentPage: payload.current_page ?? existing.currentPage ?? 0,
    totalPages: payload.total_pages ?? existing.totalPages ?? 0,
    progress: payload.progress ?? existing.progress ?? 0,
    isRead: Boolean(payload.completed),
    visited: true,
    updatedAt,
  }

  readingState.value = {
    ...readingState.value,
    albumId: payload.album_id || readingState.value.albumId,
    lastReadPhotoId: payload.photo_id,
    lastReadPage: payload.current_page ?? readingState.value.lastReadPage,
    lastReadPageIndex: payload.page_index ?? readingState.value.lastReadPageIndex,
    progress: payload.progress ?? readingState.value.progress,
    updatedAt,
    chapterMap,
    chapters: Object.values(chapterMap),
  }
}

function queueReadingPersist() {
  const context = buildPersistContext()
  if (!context) return

  const progressPayload = buildReadingProgressPayload(context)
  const fingerprint = createPersistFingerprint(progressPayload)

  applyLocalProgress(progressPayload)
  pendingProgressPayload = progressPayload

  if (fingerprint === lastPersistFingerprint && !persistTimer) return

  clearPersistTimer()
  persistTimer = setTimeout(() => {
    void flushReadingPersist()
  }, 800)
}

async function flushReadingPersist() {
  clearPersistTimer()

  const progressPayload = pendingProgressPayload
  pendingProgressPayload = null

  if (!progressPayload) return

  const fingerprint = createPersistFingerprint(progressPayload)
  if (progressPayload && fingerprint === lastPersistFingerprint) return

  if (progressPayload) {
    lastPersistFingerprint = fingerprint
  }

  const tasks = []
  if (typeof api.saveReadingProgress === 'function') {
    tasks.push(api.saveReadingProgress(progressPayload))
  }

  if (!tasks.length) return

  try {
    await Promise.allSettled(tasks)
  } catch {
  }
}

function getRestoredPageIndex() {
  const progress = readingState.value.chapterMap?.[props.photoId]
  if (!progress) return 0
  return clampPageIndex(progress.pageIndex, totalPages.value)
}

function restoreScrollPosition() {
  if (mode.value !== 'scroll' || !scrollContainerRef.value) return
  const target = scrollPageRefs.value[currentPage.value]
  if (!target) return
  scrollContainerRef.value.scrollTo({
    top: target.offsetTop,
    behavior: 'auto',
  })
}

function goToEpisode(ep) {
  if (!ep) return
  router.push({ name: 'Reader', params: { photoId: ep.id } })
}

function getImageSrc(index) {
  if (viewMode.value === 'cache' && cacheStatus.value === 'ready') {
    return api.getCachedImageUrl(albumId.value, props.photoId, index)
  }
  return api.getChapterImageUrl(props.photoId, index);
}

async function fetchChapter() {
  const requestId = ++chapterRequestId;

  try {
    loading.value = true;
    error.value = null;
    loadingCancelled = false;
    resetZoom()
    imageLoader.clear();
    lazyImageRefs.value = [];
    scrollPageRefs.value = [];
    cacheStatus.value = null
    cacheProgress.value = 0
    pdfStatus.value = null
    pdfProgress.value = 0
    pdfPhase.value = ''
    pdfDownloadTriggered = false
    episodeList.value = []
    albumTitle.value = ''
    albumAuthor.value = ''
    applyReadingState({})
    clearAsyncState()

    chapter.value = await api.getChapterDetail(props.photoId);
    if (requestId !== chapterRequestId) return;
    albumTitle.value = chapter.value?.title || ''

    if (chapter.value.album_id) {
      api.getComicDetail(chapter.value.album_id)
        .then((data) => {
          if (requestId === chapterRequestId) {
            albumTitle.value = data.title || albumTitle.value
            albumAuthor.value = data.author || albumAuthor.value
            episodeList.value = data.episodes || []
          }
        })
        .catch(() => {})

      if (typeof api.getReadingState === 'function') {
        const rawState = await api.getReadingState(chapter.value.album_id).catch(() => null)
        if (requestId !== chapterRequestId) return
        if (rawState) {
          applyReadingState(rawState, chapter.value.album_id)
        }
      }
    }

    if (viewMode.value === 'cache') {
      const statusData = await api.getChapterCacheStatus(albumId.value, props.photoId)
      if (requestId !== chapterRequestId) return;
      if (statusData.status === 'ready') {
        cacheStatus.value = 'ready'
        cacheProgress.value = 100
      } else {
        cacheStatus.value = statusData.status === 'not_started' ? 'pending' : statusData.status
        cacheProgress.value = statusData.progress || 0
        await api.startChapterCache(albumId.value, props.photoId)
        if (requestId !== chapterRequestId) return;
        startCachePolling(albumId.value, props.photoId, requestId)
      }
    } else if (viewMode.value === 'pdf') {
      const statusData = await api.getChapterPdfStatus(albumId.value, props.photoId)
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
        await api.startChapterPdf(albumId.value, props.photoId)
        if (requestId !== chapterRequestId) return;
        startPdfPolling(albumId.value, props.photoId, requestId)
      }
    } else {
      cacheStatus.value = 'ready'
    }

    currentPage.value = getRestoredPageIndex();

    await nextTick();
    if (requestId !== chapterRequestId) return;

    await nextTick();
    if (requestId !== chapterRequestId) return;

    if (mode.value === "scroll") {
      if (currentPage.value > 0) {
        restoreScrollPosition()
      }
      sequentialStartTimer = setTimeout(() => {
        sequentialStartTimer = null;
        if (requestId === chapterRequestId) {
          startSequentialLoading();
        }
      }, 100);
    }

    queueReadingPersist()
  } catch (e) {
    if (requestId !== chapterRequestId) return;
    error.value = "加载失败: " + (e.response?.data?.detail || e.message);
  } finally {
    if (requestId === chapterRequestId) {
      loading.value = false;
    }
  }
}

function startSequentialLoading() {
  const images = chapter.value?.images || [];
  if (!images.length || lazyImageRefs.value.length === 0) return;

  loadingCancelled = false;
  let nextIndex = 0;
  const total = images.length;

  function tryLoadNext() {
    if (loadingCancelled || nextIndex >= total) return;
    const i = nextIndex++;
    const imageRef = lazyImageRefs.value[i];

    function onDone() {
      if (loadingCancelled) return;
      tryLoadNext();
    }

    if (!imageRef || imageRef.isLoaded) {
      onDone();
      return;
    }
    imageRef.loadImage().then(onDone).catch(onDone);
  }

  const concurrency = Math.min(LOADING_CONFIG.maxConcurrent, total);
  for (let i = 0; i < concurrency; i++) tryLoadNext();
}

function cancelSequentialLoading() {
  loadingCancelled = true;
}

function handleImageVisible(index) {
  const imageRef = lazyImageRefs.value[index];
  if (imageRef && !imageRef.isLoaded && !imageRef.isLoading) {
    imageRef.loadImage();
  }
}

function preloadPageImages() {
  if (mode.value !== "page") return;

  const indexes = [currentPage.value];
  if (currentPage.value < totalPages.value - 1) {
    indexes.push(currentPage.value + 1);
  }
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

watch(() => props.photoId, (newId, oldId) => {
  if (oldId && oldId !== newId) {
    void flushReadingPersist()
  }
  fetchChapter()
});

watch(mode, (newMode) => {
  if (newMode === "page") {
    cancelSequentialLoading();
    preloadPageImages();
  } else if (newMode === "scroll") {
    startSequentialLoading();
    nextTick(() => {
      restoreScrollPosition()
    })
  }
});

watch(currentPage, (newPage, oldPage) => {
  if (mode.value === "page") {
    preloadPageImages();
  }

  if (!loading.value && chapter.value && newPage !== oldPage) {
    queueReadingPersist()
  }
});

watch([loading, error, readerTitle], ([isLoading, currentError, title]) => {
  if (isLoading) {
    setDocumentTitle('阅读中')
    return
  }
  if (currentError) {
    setDocumentTitle('章节加载失败')
    return
  }
  setDocumentTitle(title || '阅读中')
}, { immediate: true })

onMounted(() => {
  fetchChapter();
  document.addEventListener("keydown", handleKeydown);
});
onUnmounted(() => {
  chapterRequestId += 1;
  document.removeEventListener("keydown", handleKeydown);
  cancelSequentialLoading();
  clearAsyncState();
  void flushReadingPersist();
  imageLoader.clear();
  resetDocumentTitle()
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
        <span class="toolbar-title" :title="readerTitle">{{ readerTitle }}</span>
        <span v-if="currentChapterBadge" class="toolbar-progress">{{ currentChapterBadge }}</span>
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
          <span class="drawer-count" v-if="episodeListWithState.length">{{ episodeListWithState.length }} 话</span>
          <button class="drawer-close" @click="showEpisodeList = false" aria-label="关闭">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
        <div class="drawer-list" ref="episodeListRef">
          <div v-if="!episodeListWithState.length" class="drawer-empty">
            <div class="drawer-spinner"></div>
            目录加载中…
          </div>
          <button
            v-for="ep in episodeListWithState"
            :key="ep.id"
            :class="['ep-item', { active: String(ep.id) === String(photoId) }]"
            @click="goToEpisode(ep); showEpisodeList = false"
          >
            <span class="ep-item-indicator" v-if="String(ep.id) === String(photoId)"></span>
            <span class="ep-item-main">
              <span class="ep-item-title">{{ epTitle(ep) }}</span>
              <span
                v-if="getEpisodeStateLabel(ep)"
                :class="['ep-item-state', getEpisodeStateClass(ep)]"
              >
                {{ getEpisodeStateLabel(ep) }}
              </span>
            </span>
            <svg v-if="String(ep.id) === String(photoId)" class="ep-item-check" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
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
          :href="api.getChapterPdfDownloadUrl(albumId, photoId)"
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

.toolbar-progress {
  flex-shrink: 0;
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  color: var(--color-primary);
  background: rgba(255, 255, 255, 0.12);
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
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ep-item.active .ep-item-title {
  font-weight: 500;
}

.ep-item-main {
  display: flex;
  flex: 1;
  min-width: 0;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}

.ep-item-state {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 600;
  white-space: nowrap;
}

.ep-item-state--continue {
  color: var(--color-primary);
  background: rgba(59, 130, 246, 0.16);
}

.ep-item-state--read {
  color: #22c55e;
  background: rgba(34, 197, 94, 0.16);
}

.ep-item-state--progress {
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.16);
}

.ep-item-state--visited {
  color: rgba(255, 255, 255, 0.6);
  background: rgba(255, 255, 255, 0.08);
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
