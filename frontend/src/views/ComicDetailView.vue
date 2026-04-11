<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { getCoverUrl, getComicDetail, addFavorite, startChapterCache, getChapterCacheStatus, getAlbumCacheStatus } from '../api'
import { addHistory } from '../utils/history'
import { registerMeta, startPolling as startGlobalPolling } from '../utils/cacheQueue'
import LazyImage from '../components/LazyImage.vue'

const props = defineProps({ id: { type: String, required: true } })

const comic = ref(null)
const loading = ref(true)
const error = ref(null)
const favoriteLoading = ref(false)

// 缓存管理
const cacheMode = ref(false)           // 是否处于缓存选择模式
const selectedIds = ref(new Set())     // 选中的 episode id 集合
const cacheStatusMap = ref({})         // { [photoId]: { status, progress } }
let cachePoller = null

async function fetchComic() {
  try {
    loading.value = true
    error.value = null
    comic.value = await getComicDetail(props.id)
    addHistory({ id: props.id, title: comic.value.title, author: comic.value.author || '' })
    loadCacheStatus()
  } catch (e) {
    error.value = '加载失败: ' + (e.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

async function handleFavorite() {
  if (favoriteLoading.value) return
  try {
    favoriteLoading.value = true
    await addFavorite(props.id)
    alert('收藏成功')
  } catch {
    alert('收藏失败，请先登录')
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
  const s = new Set(selectedIds.value)
  s.has(id) ? s.delete(id) : s.add(id)
  selectedIds.value = s
}

function selectAll() {
  selectedIds.value = new Set((comic.value?.episodes || []).map(ep => ep.id))
}

function clearSelect() {
  selectedIds.value = new Set()
}

async function startCaching() {
  if (!selectedIds.value.size) return
  const albumId = props.id
  const ids = [...selectedIds.value]

  // 注册元数据供顶部缓存队列面板显示
  const albumTitle = comic.value?.title || props.id
  ids.forEach(id => {
    const ep = comic.value?.episodes?.find(e => e.id === id)
    registerMeta(id, {
      albumId: props.id,
      albumTitle,
      chapterTitle: ep ? (ep.title || `第${ep.sort}话`) : id,
    })
  })

  // 初始化状态
  const map = { ...cacheStatusMap.value }
  ids.forEach(id => { map[id] = { status: 'pending', progress: 0 } })
  cacheStatusMap.value = map

  // 并发触发（限制并发为 3）
  const chunks = []
  for (let i = 0; i < ids.length; i += 3) chunks.push(ids.slice(i, i + 3))
  for (const chunk of chunks) {
    await Promise.allSettled(chunk.map(id => {
      const ep = comic.value?.episodes?.find(e => e.id === id)
      return startChapterCache(albumId, id, {
        album_title: comic.value?.title || '',
        author: comic.value?.author || '',
        chapter_title: ep ? (ep.title || `第${ep.sort}话`) : '',
      })
    }))
  }

  // 退出选择模式，开始轮询
  cacheMode.value = false
  selectedIds.value = new Set()
  startPolling(albumId)
  startGlobalPolling() // 触发全局队列面板轮询（无参数，来自 cacheQueue.js）
}

async function loadCacheStatus() {
  try {
    const data = await getAlbumCacheStatus(props.id)
    // data 格式：{ [photoId]: { status, progress } }
    // 只保留有实际状态的章节（not_started 不会出现在结果中）
    const map = {}
    Object.entries(data).forEach(([photoId, info]) => {
      map[photoId] = { status: info.status, progress: info.progress }
    })
    // 合并：不覆盖本次会话已有的更新状态
    cacheStatusMap.value = { ...map, ...cacheStatusMap.value }

    // 如果有正在进行中的任务，启动轮询
    const hasActive = Object.values(cacheStatusMap.value).some(
      v => v.status === 'pending' || v.status === 'downloading'
    )
    if (hasActive) startPolling(props.id)
  } catch {
    // 静默失败，不影响页面正常显示
  }
}

function startPolling(albumId) {
  if (cachePoller) clearInterval(cachePoller)
  cachePoller = setInterval(async () => {
    const pendingIds = Object.entries(cacheStatusMap.value)
      .filter(([, v]) => v.status === 'pending' || v.status === 'downloading')
      .map(([id]) => id)

    if (!pendingIds.length) {
      clearInterval(cachePoller)
      cachePoller = null
      return
    }

    const results = await Promise.allSettled(
      pendingIds.map(id => getChapterCacheStatus(albumId, id))
    )
    const map = { ...cacheStatusMap.value }
    results.forEach((r, i) => {
      if (r.status === 'fulfilled') {
        map[pendingIds[i]] = { status: r.value.status, progress: r.value.progress }
      }
    })
    cacheStatusMap.value = map
  }, 2000)
}

onUnmounted(() => { if (cachePoller) clearInterval(cachePoller) })

watch(() => props.id, fetchComic)
onMounted(fetchComic)
</script>

<template>
  <div class="detail-view">
    <div class="container">
      <!-- Loading skeleton -->
      <div v-if="loading" class="skeleton-detail">
        <div class="skeleton-cover shimmer"></div>
        <div class="skeleton-info">
          <div class="sk-line sk-title shimmer"></div>
          <div class="sk-line sk-meta shimmer"></div>
          <div class="sk-line sk-desc shimmer"></div>
        </div>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="error-state">
        <p>{{ error }}</p>
        <button class="retry-btn" @click="fetchComic">重试</button>
      </div>

      <!-- Content -->
      <template v-else-if="comic">
        <div class="detail-header">
          <div class="cover-box">
            <LazyImage :src="getCoverUrl(comic.id)" :alt="comic.title" class="cover-img" />
          </div>
          <div class="meta-box">
            <h1 class="comic-title">{{ comic.title }}</h1>
            <div class="meta-row">
              <span class="meta-label">作者</span>
              <router-link
                v-for="a in (comic.authors || [comic.author])"
                :key="a"
                :to="{ name: 'Search', query: { q: a, main_tag: 2 } }"
                class="meta-link"
              >{{ a }}</router-link>
            </div>
            <div v-if="comic.tags && comic.tags.length" class="meta-row">
              <span class="meta-label">标签</span>
              <div class="tag-list">
                <router-link
                  v-for="t in comic.tags"
                  :key="t"
                  :to="{ name: 'Search', query: { q: t, main_tag: 3 } }"
                  class="tag"
                >{{ t }}</router-link>
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
                v-if="comic.episodes && comic.episodes.length"
                :to="{ name: 'Reader', params: { photoId: comic.episodes[0].id } }"
                class="btn-primary"
              >开始阅读</router-link>
              <button class="btn-outline" :disabled="favoriteLoading" @click="handleFavorite">
                {{ favoriteLoading ? '...' : '收藏' }}
              </button>
            </div>
          </div>
        </div>

        <!-- Chapter List -->
        <section v-if="comic.episodes && comic.episodes.length" class="chapter-section">
          <div class="chapter-header">
            <h2 class="section-title">章节列表 ({{ comic.episodes.length }})</h2>
            <div class="chapter-actions">
              <template v-if="cacheMode">
                <button class="act-btn" @click="selectAll">全选</button>
                <button class="act-btn" @click="clearSelect">清空</button>
                <button
                  class="act-btn act-btn-primary"
                  :disabled="!selectedIds.size"
                  @click="startCaching"
                >缓存 ({{ selectedIds.size }})</button>
                <button class="act-btn" @click="toggleCacheMode">取消</button>
              </template>
              <button v-else class="act-btn" @click="toggleCacheMode">管理缓存</button>
            </div>
          </div>

          <div class="chapter-grid">
            <div
              v-for="ep in comic.episodes"
              :key="ep.id"
              :class="['chapter-item', {
                'is-selected': cacheMode && selectedIds.has(ep.id),
                'is-cached': cacheStatusMap[ep.id]?.status === 'ready',
                'is-caching': cacheStatusMap[ep.id]?.status === 'downloading' || cacheStatusMap[ep.id]?.status === 'pending',
                'is-error': cacheStatusMap[ep.id]?.status === 'error',
              }]"
              @click="cacheMode ? toggleSelect(ep.id) : null"
            >
              <!-- 缓存模式：复选框 -->
              <span v-if="cacheMode" class="ep-checkbox">
                <svg v-if="selectedIds.has(ep.id)" width="16" height="16" viewBox="0 0 16 16" fill="var(--color-primary)">
                  <rect width="16" height="16" rx="3"/>
                  <path d="M4 8l3 3 5-5" stroke="#fff" stroke-width="1.5" fill="none" stroke-linecap="round"/>
                </svg>
                <svg v-else width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="var(--color-border)" stroke-width="1.5">
                  <rect x="0.75" y="0.75" width="14.5" height="14.5" rx="2.5"/>
                </svg>
              </span>

              <!-- 非缓存模式：点击跳转 -->
              <router-link
                v-if="!cacheMode"
                :to="{ name: 'Reader', params: { photoId: ep.id } }"
                class="ep-link"
              >
                <span class="ep-sort">{{ ep.sort }}</span>
                <span class="ep-title">{{ ep.title || `第${ep.sort}话` }}</span>
                <!-- 缓存状态图标 -->
                <span v-if="cacheStatusMap[ep.id]" class="ep-status">
                  <span v-if="cacheStatusMap[ep.id].status === 'ready'" class="status-icon status-ready">✓</span>
                  <span v-else-if="cacheStatusMap[ep.id].status === 'error'" class="status-icon status-error">✕</span>
                  <span v-else class="status-icon status-loading">{{ cacheStatusMap[ep.id].progress }}%</span>
                </span>
              </router-link>

              <!-- 缓存模式下的内容 -->
              <template v-else>
                <span class="ep-sort">{{ ep.sort }}</span>
                <span class="ep-title">{{ ep.title || `第${ep.sort}话` }}</span>
                <span v-if="cacheStatusMap[ep.id]" class="ep-status">
                  <span v-if="cacheStatusMap[ep.id].status === 'ready'" class="status-icon status-ready">✓</span>
                  <span v-else-if="cacheStatusMap[ep.id].status === 'error'" class="status-icon status-error">✕</span>
                  <span v-else class="status-icon status-loading">{{ cacheStatusMap[ep.id].progress }}%</span>
                </span>
              </template>
            </div>
          </div>
        </section>
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

.btn-outline:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

/* Chapter section */
.chapter-section {
  margin-top: 36px;
}

.section-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text);
}

.chapter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 8px;
}

.chapter-item {
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

.ep-sort {
  font-weight: 600;
  color: var(--color-primary);
  flex-shrink: 0;
}

.ep-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Skeleton */
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
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
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

.chapter-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 8px;
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

/* 章节卡片状态 */
.chapter-item {
  position: relative;
  cursor: pointer;
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

.ep-status {
  margin-left: auto;
  flex-shrink: 0;
}

.status-icon {
  font-size: 11px;
  font-weight: 700;
}

.status-ready { color: #16a34a; }
.status-error { color: #dc2626; }
.status-loading { color: #d97706; font-size: 10px; }

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

  .actions {
    justify-content: center;
  }

  .comic-title {
    font-size: 19px;
  }

  .chapter-grid {
    grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  }
}
</style>
