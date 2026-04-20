<script setup>
import { computed, onMounted, ref } from 'vue'
import ComicCard from '../components/ComicCard.vue'
import * as api from '../api'
import { usePagedList } from '../composables/usePagedList'

const confirmState = ref(null)
const mutating = ref(false)

function toTimestamp(value) {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value > 1e12 ? value : value > 1e9 ? value * 1000 : value
  }
  if (typeof value === 'string' && value.trim()) {
    const numeric = Number(value)
    if (Number.isFinite(numeric)) {
      return numeric > 1e12 ? numeric : numeric > 1e9 ? numeric * 1000 : numeric
    }
    const parsed = Date.parse(value)
    return Number.isFinite(parsed) ? parsed : 0
  }
  return 0
}

function resolveItems(data) {
  if (Array.isArray(data)) return data

  return [
    data?.items,
    data?.records,
    data?.list,
    data?.history,
    data?.results,
  ].find(Array.isArray) || []
}

function resolvePageCount(data) {
  if (Array.isArray(data)) return 1
  return Number(data?.page_count || data?.pages || data?.last_page || 1)
}

function resolveTotal(data) {
  if (Array.isArray(data)) return data.length
  return Number(data?.total || data?.count || resolveItems(data).length || 0)
}

function normalizeHistoryItem(item) {
  const id = item?.id ?? item?.album_id ?? item?.albumId
  const authors = Array.isArray(item?.authors) ? item.authors.filter(Boolean).join(', ') : ''
  const currentPage = Number(item?.current_page || item?.page || item?.last_page || 0)
  const totalPages = Number(item?.total_pages || item?.page_count || 0)
  const progress = Number(item?.progress_percent || item?.progress || 0)

  return {
    ...item,
    id: id === undefined || id === null ? '' : String(id),
    title: item?.title || item?.album_title || item?.name || 'Untitled',
    author: item?.author || authors || item?.artist || '',
    tags: Array.isArray(item?.tags) ? item.tags : [],
    photoId: item?.photo_id || item?.photoId || item?.current_photo_id || item?.last_photo_id || '',
    chapterTitle: item?.chapter_title || item?.episode_title || item?.last_photo_title || '',
    currentPage,
    totalPages,
    progress,
    visitedAt: toTimestamp(item?.visited_at || item?.updated_at || item?.last_read_at || item?.timestamp),
  }
}

const {
  items: records,
  loading,
  error,
  total,
  hasMore,
  loadingMore,
  refresh,
  loadMore,
} = usePagedList({
  fetchPage: ({ page }) => api.getHistory({ page }),
  getItems: (data) => resolveItems(data).map(normalizeHistoryItem).filter((item) => item.id),
  getPageCount: resolvePageCount,
  getTotal: resolveTotal,
  getErrorMessage: () => '请先登录后再查看历史',
})

const hasRecords = computed(() => records.value.length > 0)

async function fetchHistory() {
  await refresh()
}

function handleClear() {
  confirmState.value = { mode: 'clear' }
}

function handleRemove(id) {
  confirmState.value = { mode: 'remove', id }
}

async function doConfirm() {
  const state = confirmState.value
  if (!state || mutating.value) return

  confirmState.value = null
  mutating.value = true

  try {
    if (state.mode === 'clear') {
      await api.clearHistory()
      records.value = []
      return
    }

    await api.removeHistory(state.id)
    records.value = records.value.filter((record) => record.id !== state.id)
  } finally {
    mutating.value = false
  }
}

function formatTime(ts) {
  if (!ts) return '最近'

  const now = Date.now()
  const diff = now - ts
  const day = 86400000

  if (diff < day) {
    const date = new Date(ts)
    return `今天 ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
  }
  if (diff < day * 2) return '昨天'
  if (diff < day * 7) return `${Math.floor(diff / day)} 天前`

  const date = new Date(ts)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

function formatProgress(record) {
  if (record.progress > 0) return `${record.progress}%`
  if (record.currentPage > 0 && record.totalPages > 0) {
    return `${record.currentPage}/${record.totalPages} 页`
  }
  return '已打开'
}

onMounted(fetchHistory)
</script>

<template>
  <div class="history-view">
    <div class="container">
      <div class="toolbar">
        <div>
          <h2 class="section-title">观看历史</h2>
          <p class="section-subtitle">
            {{ total ? `共 ${total} 条记录` : '服务端阅读历史' }}
          </p>
        </div>
        <button v-if="hasRecords" class="clear-btn" :disabled="mutating" @click="handleClear">
          清空
        </button>
      </div>

      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <p>加载中...</p>
      </div>

      <div v-else-if="error" class="error-state">
        <p>{{ error }}</p>
        <button class="retry-btn" @click="fetchHistory">重试</button>
      </div>

      <div v-else-if="hasRecords" class="comic-grid">
        <div v-for="record in records" :key="record.id" class="card-wrap">
          <ComicCard :comic="record" />
          <div class="card-meta">
            <span class="visit-time">{{ formatTime(record.visitedAt) }}</span>
            <button class="remove-btn" :disabled="mutating" @click="handleRemove(record.id)" title="移除">
              ×
            </button>
          </div>
          <div v-if="record.photoId || record.chapterTitle" class="history-extra">
            <span class="history-chapter">
              {{ record.chapterTitle || '继续阅读' }}
            </span>
            <span class="history-progress">{{ formatProgress(record) }}</span>
          </div>
          <router-link
            v-if="record.photoId"
            :to="{ name: 'Reader', params: { photoId: record.photoId } }"
            class="resume-link"
          >
            继续阅读
          </router-link>
        </div>
      </div>

      <div v-else class="empty-state">
        <p>暂无观看记录</p>
      </div>

      <div v-if="!loading && hasMore" class="load-more">
        <button class="load-more-btn" :disabled="loadingMore" @click="loadMore()">
          {{ loadingMore ? '加载中...' : '加载更多' }}
        </button>
      </div>
    </div>

    <transition name="modal-fade">
      <div v-if="confirmState" class="modal-mask" @click.self="confirmState = null">
        <div class="modal-box">
          <div class="modal-icon">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#dc2626" stroke-width="1.5">
              <polyline points="3 6 5 6 21 6" />
              <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
              <path d="M10 11v6M14 11v6" />
              <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
            </svg>
          </div>
          <template v-if="confirmState.mode === 'clear'">
            <h3 class="modal-title">清空观看历史</h3>
            <p class="modal-desc">将删除全部 {{ records.length }} 条历史记录，此操作不可撤销。</p>
          </template>
          <template v-else>
            <h3 class="modal-title">移除记录</h3>
            <p class="modal-desc">
              确定从历史中移除「{{ records.find((item) => item.id === confirmState?.id)?.title || confirmState?.id }}」？
            </p>
          </template>
          <div class="modal-actions">
            <button class="modal-cancel" :disabled="mutating" @click="confirmState = null">取消</button>
            <button class="modal-confirm" :disabled="mutating" @click="doConfirm">
              {{ confirmState.mode === 'clear' ? '清空' : '移除' }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.history-view {
  padding: 20px 0 40px;
}

.container {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 20px;
}

.toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 20px;
}

.section-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 6px;
}

.section-subtitle {
  font-size: 13px;
  color: var(--color-text-muted);
}

.clear-btn {
  padding: 5px 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 13px;
  color: var(--color-text-secondary);
  transition: all 0.2s;
}

.clear-btn:hover:not(:disabled) {
  border-color: #dc2626;
  color: #dc2626;
}

.comic-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px;
}

.card-wrap {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.card-meta,
.history-extra {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 0 2px;
}

.visit-time,
.history-progress {
  font-size: 11px;
  color: var(--color-text-muted);
}

.history-chapter {
  flex: 1;
  font-size: 12px;
  color: var(--color-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.resume-link {
  width: fit-content;
  padding: 0 2px;
  font-size: 12px;
  color: var(--color-primary);
  font-weight: 500;
}

.remove-btn {
  font-size: 16px;
  line-height: 1;
  color: var(--color-text-muted);
  padding: 0 4px;
  transition: color 0.2s;
}

.remove-btn:hover:not(:disabled) {
  color: #dc2626;
}

.loading-state,
.error-state,
.empty-state {
  text-align: center;
  padding: 80px 20px;
  color: var(--color-text-muted);
  font-size: 15px;
}

.spinner {
  width: 26px;
  height: 26px;
  margin: 0 auto 12px;
  border: 3px solid rgba(0, 0, 0, 0.08);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

.retry-btn {
  margin-top: 16px;
  padding: 10px 24px;
  background: var(--color-primary);
  color: #fff;
  border-radius: var(--radius-sm);
  font-weight: 500;
}

.load-more {
  text-align: center;
  padding: 32px 0;
}

.load-more-btn {
  padding: 10px 32px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-secondary);
  transition: all 0.2s;
}

.load-more-btn:hover:not(:disabled) {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 500;
  padding: 20px;
}

.modal-box {
  background: var(--color-surface);
  border-radius: var(--radius-md);
  padding: 32px 28px 24px;
  width: 100%;
  max-width: 360px;
  text-align: center;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}

.modal-icon {
  display: flex;
  justify-content: center;
  margin-bottom: 16px;
}

.modal-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 8px;
}

.modal-desc {
  font-size: 14px;
  color: var(--color-text-muted);
  line-height: 1.6;
  margin-bottom: 24px;
}

.modal-actions {
  display: flex;
  gap: 10px;
}

.modal-cancel {
  flex: 1;
  padding: 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-secondary);
  background: var(--color-bg);
  cursor: pointer;
  transition: all 0.2s;
}

.modal-cancel:hover:not(:disabled) {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.modal-confirm {
  flex: 1;
  padding: 10px;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  background: #dc2626;
  cursor: pointer;
  transition: background 0.2s;
}

.modal-confirm:hover:not(:disabled) {
  background: #b91c1c;
}

.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.2s ease;
}

.modal-fade-enter-active .modal-box,
.modal-fade-leave-active .modal-box {
  transition: transform 0.2s ease, opacity 0.2s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.modal-fade-enter-from .modal-box,
.modal-fade-leave-to .modal-box {
  transform: scale(0.95);
  opacity: 0;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 640px) {
  .comic-grid {
    grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
    gap: 10px;
  }
}
</style>
