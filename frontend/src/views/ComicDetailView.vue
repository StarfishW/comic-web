<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import * as api from '../api'
import { registerMeta, startPolling as startGlobalPolling } from '../utils/cacheQueue'
import { setDocumentTitle, resetDocumentTitle } from '../utils/documentTitle'
import { formatEpisodeProgress, mergeEpisodesWithReadingState, normalizeReadingState } from '../utils/reading'
import LazyImage from '../components/LazyImage.vue'
import CommentSection from '../components/CommentSection.vue'

const props = defineProps({ id: { type: String, required: true } })

const comic = ref(null)
const loading = ref(true)
const error = ref(null)
const favoriteLoading = ref(false)
const readingStateLoading = ref(false)
const readingState = ref(normalizeReadingState({}, props.id))

const cacheMode = ref(false)
const selectedIds = ref(new Set())
const cacheStatusMap = ref({})
const cacheAllLoading = ref(false)
let cachePoller = null

const authorList = computed(() => {
  const authors = Array.isArray(comic.value?.authors)
    ? comic.value.authors.filter(Boolean)
    : [comic.value?.author].filter(Boolean)

  return authors
})

const episodesWithState = computed(() =>
  mergeEpisodesWithReadingState(comic.value?.episodes || [], readingState.value),
)

const latestReadEpisode = computed(() =>
  episodesWithState.value.find((episode) => episode.isLastRead) || null,
)

const primaryEpisode = computed(() =>
  latestReadEpisode.value || episodesWithState.value[0] || null,
)

const primaryActionText = computed(() =>
  latestReadEpisode.value ? '继续阅读' : '开始阅读',
)

const favoriteText = computed(() => {
  if (favoriteLoading.value) return '处理中...'
  return readingState.value.isFavorite ? '已收藏' : '收藏'
})

const readingStats = computed(() => {
  const episodes = episodesWithState.value
  const readCount = episodes.filter((episode) => episode.reading?.isRead).length
  const inProgressCount = episodes.filter((episode) => {
    const progress = episode.reading
    return progress && !progress.isRead && progress.progress > 0
  }).length
  const visitedCount = episodes.filter((episode) => episode.reading?.visited).length

  return {
    total: episodes.length,
    readCount,
    inProgressCount,
    visitedCount,
  }
})

const readingSummary = computed(() => {
  if (latestReadEpisode.value) {
    const progress = latestReadEpisode.value.reading
    const suffix = progress && !progress.isRead && progress.progress > 0
      ? ` · ${progress.progress}%`
      : ''
    return `最近读到 ${getEpisodeTitle(latestReadEpisode.value)}${suffix}`
  }

  if (readingStats.value.readCount > 0) {
    return `已读 ${readingStats.value.readCount}/${readingStats.value.total} 话`
  }

  if (readingStats.value.inProgressCount > 0 || readingStats.value.visitedCount > 0) {
    return `已打开 ${readingStats.value.visitedCount || readingStats.value.inProgressCount} 话`
  }

  return ''
})

const cacheAllStats = computed(() => {
  const episodes = comic.value?.episodes || []
  const total = episodes.length
  const readyCount = episodes.filter((episode) => cacheStatusMap.value[episode.id]?.status === 'ready').length
  const pendingCache = episodes.filter((episode) => {
    const status = cacheStatusMap.value[episode.id]?.status
    return !status || status === 'not_started' || status === 'error'
  })

  return { total, readyCount, pendingCache }
})

function getEpisodeTitle(episode) {
  return episode?.title || `第${episode?.sort}话`
}

function getEpisodeReadingLabel(episode) {
  const progress = episode?.reading
  if (!progress) return ''
  if (episode.isLastRead && !progress.isRead) {
    return progress.progress > 0 ? `继续 ${progress.progress}%` : '继续阅读'
  }
  return formatEpisodeProgress(progress)
}

function getEpisodeReadingClass(episode) {
  const progress = episode?.reading
  if (!progress) return ''
  if (episode.isLastRead && !progress.isRead) return 'ep-reading-tag--continue'
  if (progress.isRead) return 'ep-reading-tag--read'
  if (progress.progress > 0) return 'ep-reading-tag--progress'
  return 'ep-reading-tag--visited'
}

function applyReadingState(rawState) {
  readingState.value = normalizeReadingState(rawState, props.id)
}

async function fetchComic() {
  const nextId = props.id

  try {
    loading.value = true
    error.value = null
    comic.value = null
    cacheMode.value = false
    selectedIds.value = new Set()
    cacheStatusMap.value = {}
    applyReadingState({})
    readingStateLoading.value = typeof api.getReadingState === 'function'

    const [comicData, rawState] = await Promise.all([
      api.getComicDetail(nextId),
      typeof api.getReadingState === 'function'
        ? api.getReadingState(nextId).catch(() => null)
        : Promise.resolve(null),
    ])

    comic.value = comicData

    if (rawState) {
      applyReadingState(rawState)
    }

    loadCacheStatus()
  } catch (e) {
    error.value = '加载失败: ' + (e.response?.data?.detail || e.message)
  } finally {
    loading.value = false
    readingStateLoading.value = false
  }
}

async function handleFavorite() {
  if (favoriteLoading.value || !comic.value) return

  const willFavorite = !readingState.value.isFavorite
  const action = willFavorite ? api.addFavorite : api.removeFavorite

  if (typeof action !== 'function') return

  favoriteLoading.value = true

  try {
    if (willFavorite) {
      await action(props.id, {
        title: comic.value.title || '',
        author: comic.value.author || authorList.value[0] || '',
        cover: api.getCoverUrl(props.id),
      })
    } else {
      await action(props.id)
    }

    readingState.value = {
      ...readingState.value,
      isFavorite: willFavorite,
    }
  } catch {
    alert(willFavorite ? '收藏失败，请先登录' : '取消收藏失败，请稍后重试')
  } finally {
    favoriteLoading.value = false
  }
}

function toggleCacheMode() {
  cacheMode.value = !cacheMode.value
  if (!cacheMode.value) {
    selectedIds.value = new Set()
  }
}

function toggleSelect(id) {
  const nextValue = new Set(selectedIds.value)
  if (nextValue.has(id)) nextValue.delete(id)
  else nextValue.add(id)
  selectedIds.value = nextValue
}

function selectAll() {
  selectedIds.value = new Set((comic.value?.episodes || []).map((episode) => episode.id))
}

function clearSelect() {
  selectedIds.value = new Set()
}

async function startCaching() {
  if (!selectedIds.value.size) return

  const albumId = props.id
  const ids = [...selectedIds.value]
  const albumTitle = comic.value?.title || props.id

  ids.forEach((id) => {
    const episode = comic.value?.episodes?.find((item) => item.id === id)
    registerMeta(id, {
      albumId: props.id,
      albumTitle,
      chapterTitle: episode ? getEpisodeTitle(episode) : id,
    })
  })

  const nextMap = { ...cacheStatusMap.value }
  ids.forEach((id) => {
    nextMap[id] = { status: 'pending', progress: 0 }
  })
  cacheStatusMap.value = nextMap

  const chunks = []
  for (let index = 0; index < ids.length; index += 3) {
    chunks.push(ids.slice(index, index + 3))
  }

  for (const chunk of chunks) {
    await Promise.allSettled(chunk.map((id) => {
      const episode = comic.value?.episodes?.find((item) => item.id === id)
      return api.startChapterCache(albumId, id, {
        album_title: comic.value?.title || '',
        author: comic.value?.author || '',
        chapter_title: episode ? getEpisodeTitle(episode) : '',
      })
    }))
  }

  cacheMode.value = false
  selectedIds.value = new Set()
  startPolling(albumId)
  startGlobalPolling()
}

async function loadCacheStatus() {
  try {
    const data = await api.getAlbumCacheStatus(props.id)
    const nextMap = {}

    Object.entries(data || {}).forEach(([photoId, info]) => {
      nextMap[photoId] = { status: info.status, progress: info.progress }
    })

    cacheStatusMap.value = { ...nextMap, ...cacheStatusMap.value }

    const hasActiveTask = Object.values(cacheStatusMap.value).some((status) =>
      status.status === 'pending' || status.status === 'downloading',
    )

    if (hasActiveTask) {
      startPolling(props.id)
    }
  } catch {
  }
}

function startPolling(albumId) {
  if (cachePoller) clearInterval(cachePoller)

  cachePoller = setInterval(async () => {
    const pendingIds = Object.entries(cacheStatusMap.value)
      .filter(([, value]) => value.status === 'pending' || value.status === 'downloading')
      .map(([id]) => id)

    if (!pendingIds.length) {
      clearInterval(cachePoller)
      cachePoller = null
      return
    }

    const results = await Promise.allSettled(
      pendingIds.map((id) => api.getChapterCacheStatus(albumId, id)),
    )
    const nextMap = { ...cacheStatusMap.value }

    results.forEach((result, index) => {
      if (result.status === 'fulfilled') {
        nextMap[pendingIds[index]] = {
          status: result.value.status,
          progress: result.value.progress,
        }
      }
    })

    cacheStatusMap.value = nextMap
  }, 2000)
}

async function cacheAll() {
  if (cacheAllLoading.value) return

  const { pendingCache } = cacheAllStats.value
  if (!pendingCache.length) return

  cacheAllLoading.value = true

  try {
    const albumId = props.id
    const albumTitle = comic.value?.title || props.id

    pendingCache.forEach((episode) => {
      registerMeta(episode.id, {
        albumId,
        albumTitle,
        chapterTitle: getEpisodeTitle(episode),
      })
    })

    const nextMap = { ...cacheStatusMap.value }
    pendingCache.forEach((episode) => {
      nextMap[episode.id] = { status: 'pending', progress: 0 }
    })
    cacheStatusMap.value = nextMap

    const ids = pendingCache.map((episode) => episode.id)
    const chunks = []
    for (let index = 0; index < ids.length; index += 3) {
      chunks.push(ids.slice(index, index + 3))
    }

    for (const chunk of chunks) {
      await Promise.allSettled(chunk.map((id) => {
        const episode = comic.value?.episodes?.find((item) => item.id === id)
        return api.startChapterCache(albumId, id, {
          album_title: comic.value?.title || '',
          author: comic.value?.author || '',
          chapter_title: episode ? getEpisodeTitle(episode) : '',
        })
      }))
    }

    startPolling(albumId)
    startGlobalPolling()
  } finally {
    cacheAllLoading.value = false
  }
}

onUnmounted(() => {
  if (cachePoller) clearInterval(cachePoller)
})

watch([loading, error, () => comic.value?.title], ([isLoading, currentError, title]) => {
  if (isLoading) {
    setDocumentTitle('漫画详情')
    return
  }
  if (currentError) {
    setDocumentTitle('漫画加载失败')
    return
  }
  setDocumentTitle(title || '漫画详情')
}, { immediate: true })

watch(() => props.id, fetchComic)
onMounted(fetchComic)
onUnmounted(resetDocumentTitle)
</script>

<template>
  <div class="detail-view">
    <div class="container">
      <div v-if="loading" class="skeleton-detail">
        <div class="skeleton-cover shimmer"></div>
        <div class="skeleton-info">
          <div class="sk-line sk-title shimmer"></div>
          <div class="sk-line sk-meta shimmer"></div>
          <div class="sk-line sk-desc shimmer"></div>
        </div>
      </div>

      <div v-else-if="error" class="error-state">
        <p>{{ error }}</p>
        <button class="retry-btn" @click="fetchComic">重试</button>
      </div>

      <template v-else-if="comic">
        <div class="detail-header">
          <div class="cover-box">
            <LazyImage :src="api.getCoverUrl(comic.id)" :alt="comic.title" class="cover-img" />
          </div>

          <div class="meta-box">
            <h1 class="comic-title">{{ comic.title }}</h1>

            <div v-if="authorList.length" class="meta-row">
              <span class="meta-label">作者</span>
              <router-link
                v-for="author in authorList"
                :key="author"
                :to="{ name: 'Search', query: { q: author, main_tag: 2 } }"
                class="meta-link"
              >
                {{ author }}
              </router-link>
            </div>

            <div v-if="comic.tags && comic.tags.length" class="meta-row">
              <span class="meta-label">标签</span>
              <div class="tag-list">
                <router-link
                  v-for="tag in comic.tags"
                  :key="tag"
                  :to="{ name: 'Search', query: { q: tag, main_tag: 3 } }"
                  class="tag"
                >
                  {{ tag }}
                </router-link>
              </div>
            </div>

            <div class="stats">
              <span v-if="comic.views">浏览 {{ comic.views }}</span>
              <span v-if="comic.likes">喜欢 {{ comic.likes }}</span>
              <span v-if="comic.page_count">{{ comic.page_count }} 页</span>
            </div>

            <p v-if="comic.description" class="description">{{ comic.description }}</p>

            <div class="actions">
              <router-link
                v-if="primaryEpisode"
                :to="{ name: 'Reader', params: { photoId: primaryEpisode.id } }"
                class="btn-primary"
              >
                {{ primaryActionText }}
              </router-link>
              <button
                class="btn-outline"
                :class="{ 'is-active': readingState.isFavorite }"
                :disabled="favoriteLoading"
                @click="handleFavorite"
              >
                {{ favoriteText }}
              </button>
            </div>

            <div v-if="comic.episodes?.length" class="reading-overview">
              <span v-if="readingStats.readCount" class="overview-pill">
                已读 {{ readingStats.readCount }}/{{ readingStats.total }}
              </span>
              <span v-if="readingStats.inProgressCount" class="overview-pill overview-pill--progress">
                进行中 {{ readingStats.inProgressCount }}
              </span>
              <span v-if="readingSummary" class="overview-detail">{{ readingSummary }}</span>
              <span v-else-if="readingStateLoading" class="overview-detail">正在同步阅读状态...</span>
            </div>
          </div>
        </div>

        <section v-if="episodesWithState.length" class="chapter-section">
          <div class="chapter-header">
            <div class="chapter-heading">
              <h2 class="section-title">章节列表 ({{ episodesWithState.length }})</h2>
              <p v-if="readingSummary" class="section-subtitle">{{ readingSummary }}</p>
            </div>

            <div class="chapter-actions">
              <template v-if="cacheMode">
                <button class="act-btn" @click="selectAll">全选</button>
                <button class="act-btn" @click="clearSelect">清空</button>
                <button
                  class="act-btn act-btn-primary"
                  :disabled="!selectedIds.size"
                  @click="startCaching"
                >
                  缓存 ({{ selectedIds.size }})
                </button>
                <button class="act-btn" @click="toggleCacheMode">取消</button>
              </template>

              <template v-else>
                <span v-if="cacheAllStats.readyCount > 0" class="cache-summary">
                  已缓存 {{ cacheAllStats.readyCount }}/{{ cacheAllStats.total }}
                </span>
                <button
                  v-if="cacheAllStats.pendingCache.length > 0"
                  class="act-btn act-btn-primary"
                  :disabled="cacheAllLoading"
                  @click="cacheAll"
                >
                  {{ cacheAllLoading ? '队列中...' : `一键缓存 (${cacheAllStats.pendingCache.length})` }}
                </button>
                <button class="act-btn" @click="toggleCacheMode">管理缓存</button>
              </template>
            </div>
          </div>

          <div class="chapter-grid">
            <div
              v-for="episode in episodesWithState"
              :key="episode.id"
              :class="['chapter-item', {
                'is-selected': cacheMode && selectedIds.has(episode.id),
                'is-cached': cacheStatusMap[episode.id]?.status === 'ready',
                'is-caching': cacheStatusMap[episode.id]?.status === 'downloading' || cacheStatusMap[episode.id]?.status === 'pending',
                'is-error': cacheStatusMap[episode.id]?.status === 'error',
                'is-read': episode.reading?.isRead,
                'is-reading': episode.reading && !episode.reading.isRead && episode.reading.progress > 0,
                'is-latest-read': episode.isLastRead,
              }]"
              @click="cacheMode ? toggleSelect(episode.id) : null"
            >
              <span v-if="cacheMode" class="ep-checkbox">
                <svg v-if="selectedIds.has(episode.id)" width="16" height="16" viewBox="0 0 16 16" fill="var(--color-primary)">
                  <rect width="16" height="16" rx="3" />
                  <path d="M4 8l3 3 5-5" stroke="#fff" stroke-width="1.5" fill="none" stroke-linecap="round" />
                </svg>
                <svg v-else width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="var(--color-border)" stroke-width="1.5">
                  <rect x="0.75" y="0.75" width="14.5" height="14.5" rx="2.5" />
                </svg>
              </span>

              <router-link
                v-if="!cacheMode"
                :to="{ name: 'Reader', params: { photoId: episode.id } }"
                class="ep-link"
              >
                <span class="ep-sort">{{ episode.sort }}</span>
                <span class="ep-body">
                  <span class="ep-title">{{ getEpisodeTitle(episode) }}</span>
                  <span
                    v-if="getEpisodeReadingLabel(episode)"
                    :class="['ep-reading-tag', getEpisodeReadingClass(episode)]"
                  >
                    {{ getEpisodeReadingLabel(episode) }}
                  </span>
                </span>
                <span v-if="cacheStatusMap[episode.id]" class="ep-status">
                  <span v-if="cacheStatusMap[episode.id].status === 'ready'" class="status-icon status-ready">✓</span>
                  <span v-else-if="cacheStatusMap[episode.id].status === 'error'" class="status-icon status-error">✕</span>
                  <span v-else class="status-icon status-loading">{{ cacheStatusMap[episode.id].progress }}%</span>
                </span>
              </router-link>

              <template v-else>
                <span class="ep-sort">{{ episode.sort }}</span>
                <span class="ep-body">
                  <span class="ep-title">{{ getEpisodeTitle(episode) }}</span>
                  <span
                    v-if="getEpisodeReadingLabel(episode)"
                    :class="['ep-reading-tag', getEpisodeReadingClass(episode)]"
                  >
                    {{ getEpisodeReadingLabel(episode) }}
                  </span>
                </span>
                <span v-if="cacheStatusMap[episode.id]" class="ep-status">
                  <span v-if="cacheStatusMap[episode.id].status === 'ready'" class="status-icon status-ready">✓</span>
                  <span v-else-if="cacheStatusMap[episode.id].status === 'error'" class="status-icon status-error">✕</span>
                  <span v-else class="status-icon status-loading">{{ cacheStatusMap[episode.id].progress }}%</span>
                </span>
              </template>
            </div>
          </div>
        </section>

        <CommentSection
          :album-id="props.id"
          :title="comic.title || ''"
          :initial-count="comic.comment_count || comic.comments_count || 0"
        />
      </template>
    </div>
  </div>
</template>

<style scoped>
.detail-view {
  padding: 20px 0 40px;
}

.container {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 20px;
}

.detail-header {
  display: flex;
  gap: 28px;
  align-items: flex-start;
}

.cover-box {
  flex-shrink: 0;
  width: 220px;
  border-radius: var(--radius-md);
  overflow: hidden;
  box-shadow: var(--shadow-md);
}

.cover-img :deep(.lazy-image-wrapper) {
  width: 100%;
  aspect-ratio: 3 / 4;
}

.cover-img :deep(.lazy-image) {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.meta-box {
  flex: 1;
  min-width: 0;
}

.comic-title {
  font-size: 22px;
  font-weight: 700;
  line-height: 1.3;
  color: var(--color-text);
  margin-bottom: 14px;
}

.meta-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.meta-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-muted);
  flex-shrink: 0;
  min-width: 36px;
  padding-top: 2px;
}

.meta-link {
  font-size: 14px;
  color: var(--color-primary);
  cursor: pointer;
}

.meta-link:hover {
  text-decoration: underline;
}

.tag-list {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.tag {
  font-size: 12px;
  padding: 2px 10px;
  background: var(--color-primary-light);
  color: var(--color-primary);
  border-radius: 12px;
  cursor: pointer;
  transition: background 0.2s;
}

.tag:hover {
  background: var(--color-primary);
  color: #fff;
}

.stats {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: var(--color-text-muted);
  margin: 12px 0;
}

.description {
  font-size: 14px;
  line-height: 1.7;
  color: var(--color-text-secondary);
  margin: 12px 0 16px;
}

.actions {
  display: flex;
  gap: 10px;
  margin-top: 16px;
  flex-wrap: wrap;
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  padding: 10px 28px;
  background: var(--color-primary);
  color: #fff;
  border-radius: var(--radius-sm);
  font-weight: 600;
  font-size: 14px;
  transition: background 0.2s;
  cursor: pointer;
}

.btn-primary:hover {
  background: var(--color-primary-hover);
}

.btn-outline {
  padding: 10px 24px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-weight: 500;
  font-size: 14px;
  color: var(--color-text-secondary);
  transition: all 0.2s;
}

.btn-outline:hover:not(:disabled) {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.btn-outline.is-active {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: var(--color-primary-light);
}

.reading-overview {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 14px;
}

.overview-pill {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  color: var(--color-primary);
  background: var(--color-primary-light);
}

.overview-pill--progress {
  color: #b45309;
  background: rgba(245, 158, 11, 0.12);
}

.overview-detail {
  font-size: 13px;
  color: var(--color-text-muted);
}

.chapter-section {
  margin-top: 36px;
}

.chapter-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 8px;
}

.chapter-heading {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.section-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text);
}

.section-subtitle {
  font-size: 13px;
  color: var(--color-text-muted);
}

.chapter-actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.act-btn {
  padding: 5px 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 500;
  color: var(--color-text-secondary);
  background: var(--color-bg);
  transition: all 0.2s;
  cursor: pointer;
}

.act-btn:hover:not(:disabled) {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.act-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.act-btn-primary {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: #fff;
}

.act-btn-primary:hover:not(:disabled) {
  background: var(--color-primary-hover);
  color: #fff;
}

.chapter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
  gap: 8px;
}

.chapter-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 13px;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.2s;
  overflow: hidden;
}

.chapter-item:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: var(--color-primary-light);
}

.chapter-item.is-selected {
  border-color: var(--color-primary);
  background: var(--color-primary-light);
}

.chapter-item.is-cached {
  border-color: #16a34a;
}

.chapter-item.is-caching {
  border-color: #d97706;
}

.chapter-item.is-error {
  border-color: #dc2626;
}

.chapter-item.is-read:not(.is-cached):not(.is-latest-read) {
  border-color: rgba(22, 163, 74, 0.45);
}

.chapter-item.is-reading:not(.is-caching):not(.is-latest-read) {
  border-color: rgba(217, 119, 6, 0.45);
}

.chapter-item.is-latest-read:not(.is-selected) {
  border-color: var(--color-primary);
  background: var(--color-primary-light);
}

.ep-link {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  color: inherit;
  text-decoration: none;
}

.ep-checkbox {
  flex-shrink: 0;
}

.ep-sort {
  font-weight: 600;
  color: var(--color-primary);
  flex-shrink: 0;
}

.ep-body {
  display: flex;
  flex: 1;
  min-width: 0;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}

.ep-title {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ep-reading-tag {
  display: inline-flex;
  align-items: center;
  max-width: 100%;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}

.ep-reading-tag--continue {
  color: var(--color-primary);
  background: var(--color-primary-light);
}

.ep-reading-tag--read {
  color: #15803d;
  background: rgba(22, 163, 74, 0.12);
}

.ep-reading-tag--progress {
  color: #b45309;
  background: rgba(245, 158, 11, 0.12);
}

.ep-reading-tag--visited {
  color: var(--color-text-secondary);
  background: rgba(100, 116, 139, 0.12);
}

.ep-status {
  margin-left: auto;
  flex-shrink: 0;
}

.status-icon {
  font-size: 11px;
  font-weight: 700;
}

.status-ready {
  color: #16a34a;
}

.status-error {
  color: #dc2626;
}

.status-loading {
  color: #d97706;
  font-size: 10px;
}

.cache-summary {
  font-size: 12px;
  color: var(--color-text-muted);
  padding: 5px 0;
}

.skeleton-detail {
  display: flex;
  gap: 28px;
}

.skeleton-cover {
  width: 220px;
  aspect-ratio: 3 / 4;
  border-radius: var(--radius-md);
  background: var(--color-border);
  flex-shrink: 0;
}

.skeleton-info {
  flex: 1;
  padding-top: 8px;
}

.sk-line {
  background: var(--color-border);
  border-radius: 4px;
}

.sk-title {
  height: 24px;
  width: 60%;
}

.sk-meta {
  height: 16px;
  width: 40%;
  margin-top: 14px;
}

.sk-desc {
  height: 60px;
  width: 90%;
  margin-top: 14px;
}

.shimmer {
  background: linear-gradient(90deg, var(--color-border) 25%, var(--color-shimmer-highlight) 50%, var(--color-border) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% {
    background-position: 200% 0;
  }

  100% {
    background-position: -200% 0;
  }
}

.error-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--color-text-secondary);
}

.retry-btn {
  margin-top: 16px;
  padding: 8px 24px;
  background: var(--color-primary);
  color: #fff;
  border-radius: var(--radius-sm);
  font-weight: 500;
  cursor: pointer;
}

@media (max-width: 640px) {
  .detail-header {
    flex-direction: column;
    align-items: center;
    text-align: center;
  }

  .cover-box {
    width: 180px;
  }

  .meta-row {
    justify-content: center;
  }

  .actions,
  .reading-overview {
    justify-content: center;
  }

  .comic-title {
    font-size: 19px;
  }

  .chapter-grid {
    grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  }

  .chapter-heading {
    width: 100%;
  }
}
</style>
