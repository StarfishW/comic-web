<script setup>
import { ref, computed, onMounted } from 'vue'
import { getCacheLibrary, deleteChapterCache, deleteAlbumCache, getCoverUrl } from '../api'
import LazyImage from '../components/LazyImage.vue'

function getStorageKey() {
  try {
    const raw = localStorage.getItem('auth_user')
    const user = raw ? JSON.parse(raw) : null
    const suffix = user?.id || user?.username || 'guest'
    return `cache_meta:${suffix}`
  } catch {
    return 'cache_meta:guest'
  }
}

let localMeta = {}
try {
  localMeta = JSON.parse(localStorage.getItem(getStorageKey()) || '{}')
} catch {
  localMeta = {}
}

function getAlbumTitle(albumId, albumInfo) {
  if (albumInfo?.album_title) return albumInfo.album_title
  const entry = Object.values(localMeta).find(item => item.albumId === albumId)
  return entry?.albumTitle || albumId
}

function getAlbumAuthor(albumId, albumInfo) {
  if (albumInfo?.author) return albumInfo.author
  const entry = Object.values(localMeta).find(item => item.albumId === albumId)
  return entry?.author || ''
}

function getChapterTitle(photoId, chapterInfo) {
  if (chapterInfo?.chapter_title) return chapterInfo.chapter_title
  return localMeta[photoId]?.chapterTitle || photoId
}

const library = ref({})
const totalSize = ref(0)
const loading = ref(true)
const error = ref('')
const expandedAlbums = ref(new Set())
const confirmState = ref(null) // { mode: 'album' | 'chapter', albumId: string, photoId?: string }
const confirmLoading = ref(false)
const confirmError = ref('')

const albumList = computed(() =>
  Object.entries(library.value).map(([id, info]) => ({ id, ...info })),
)

const pendingAlbum = computed(() => {
  const albumId = confirmState.value?.albumId
  if (!albumId || !library.value[albumId]) return null
  return { id: albumId, ...library.value[albumId] }
})

const pendingChapter = computed(() => {
  if (confirmState.value?.mode !== 'chapter') return null
  return pendingAlbum.value?.chapters?.[confirmState.value.photoId] || null
})

const pendingSummary = computed(() => {
  if (!confirmState.value) return ''

  if (confirmState.value.mode === 'album') {
    const chapterCount = pendingAlbum.value?.chapter_count || 0
    const size = formatSize(pendingAlbum.value?.total_size_bytes || 0)
    return `${chapterCount} 个章节 · ${size}`
  }

  const chapter = pendingChapter.value
  if (!chapter) return ''

  const parts = [`${chapter.image_count || 0} 张图片`]
  if (chapter.has_pdf) parts.push('含 PDF')
  parts.push(formatSize(chapter.size_bytes || 0))
  return parts.join(' · ')
})

async function loadLibrary() {
  try {
    loading.value = true
    error.value = ''
    const data = await getCacheLibrary()
    library.value = data.albums || {}
    totalSize.value = data.total_size_bytes || 0
  } catch {
    error.value = '加载失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

function toggleAlbum(albumId) {
  const next = new Set(expandedAlbums.value)
  if (next.has(albumId)) {
    next.delete(albumId)
  } else {
    next.add(albumId)
  }
  expandedAlbums.value = next
}

function openRemoveChapter(albumId, photoId) {
  confirmError.value = ''
  confirmState.value = { mode: 'chapter', albumId, photoId }
}

function openRemoveAlbum(albumId) {
  confirmError.value = ''
  confirmState.value = { mode: 'album', albumId }
}

function closeConfirm() {
  if (confirmLoading.value) return
  confirmState.value = null
  confirmError.value = ''
}

function applyChapterRemoval(albumId, photoId) {
  const album = library.value[albumId]
  if (!album) return

  const chapters = { ...album.chapters }
  const size = chapters[photoId]?.size_bytes || 0
  delete chapters[photoId]

  if (!Object.keys(chapters).length) {
    const nextLibrary = { ...library.value }
    delete nextLibrary[albumId]
    library.value = nextLibrary
    expandedAlbums.value.delete(albumId)
  } else {
    library.value = {
      ...library.value,
      [albumId]: {
        ...album,
        chapters,
        chapter_count: Object.keys(chapters).length,
        total_size_bytes: Math.max(0, album.total_size_bytes - size),
      },
    }
  }

  totalSize.value = Math.max(0, totalSize.value - size)
}

function applyAlbumRemoval(albumId) {
  const size = library.value[albumId]?.total_size_bytes || 0
  const nextLibrary = { ...library.value }
  delete nextLibrary[albumId]
  library.value = nextLibrary

  const nextExpanded = new Set(expandedAlbums.value)
  nextExpanded.delete(albumId)
  expandedAlbums.value = nextExpanded
  totalSize.value = Math.max(0, totalSize.value - size)
}

async function confirmRemove() {
  const state = confirmState.value
  if (!state || confirmLoading.value) return

  confirmLoading.value = true
  confirmError.value = ''

  try {
    if (state.mode === 'chapter') {
      await deleteChapterCache(state.albumId, state.photoId)
      applyChapterRemoval(state.albumId, state.photoId)
    } else {
      await deleteAlbumCache(state.albumId)
      applyAlbumRemoval(state.albumId)
    }

    confirmState.value = null
  } catch {
    confirmError.value = '删除失败，请稍后重试'
  } finally {
    confirmLoading.value = false
  }
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatTime(ts) {
  const date = new Date(ts * 1000)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

onMounted(loadLibrary)
</script>

<template>
  <div class="cache-view">
    <div class="container">
      <div class="page-header">
        <div>
          <h1 class="page-title">缓存库</h1>
          <p v-if="!loading" class="page-sub">
            共 {{ albumList.length }} 部漫画 · 占用 {{ formatSize(totalSize) }}
          </p>
        </div>
        <button class="refresh-btn" @click="loadLibrary" :disabled="loading">刷新</button>
      </div>

      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <span>加载中...</span>
      </div>

      <div v-else-if="error" class="empty-state">{{ error }}</div>

      <div v-else-if="!albumList.length" class="empty-state">
        <p>暂无缓存内容</p>
        <p class="empty-hint">在漫画详情页缓存章节后，内容会显示在这里。</p>
      </div>

      <div v-else class="album-list">
        <div v-for="album in albumList" :key="album.id" class="album-card">
          <div class="album-main">
            <router-link :to="{ name: 'ComicDetail', params: { id: album.id } }" class="cover-wrap">
              <LazyImage
                :src="getCoverUrl(album.id)"
                :alt="getAlbumTitle(album.id, album)"
                class="cover-img"
              />
            </router-link>

            <div class="album-body">
              <div class="album-top">
                <router-link
                  :to="{ name: 'ComicDetail', params: { id: album.id } }"
                  class="album-title"
                >{{ getAlbumTitle(album.id, album) }}</router-link>
                <p v-if="getAlbumAuthor(album.id, album)" class="album-author">
                  {{ getAlbumAuthor(album.id, album) }}
                </p>
                <p class="album-stats">
                  {{ album.chapter_count }} 个章节 · {{ formatSize(album.total_size_bytes) }}
                </p>
              </div>

              <div class="album-bottom">
                <button class="toggle-btn" @click="toggleAlbum(album.id)">
                  {{ expandedAlbums.has(album.id) ? '收起章节' : '查看章节' }}
                  <svg
                    :class="['chevron', { expanded: expandedAlbums.has(album.id) }]"
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                  ><polyline points="6 9 12 15 18 9"/></svg>
                </button>
                <button class="del-btn" @click="openRemoveAlbum(album.id)">删除全部</button>
              </div>
            </div>
          </div>

          <div v-if="expandedAlbums.has(album.id)" class="chapter-list">
            <div
              v-for="(info, photoId) in album.chapters"
              :key="photoId"
              class="chapter-row"
            >
              <div class="ch-info">
                <span class="ch-title">{{ getChapterTitle(photoId, info) }}</span>
                <span class="ch-meta">
                  {{ info.image_count }} 张
                  <span v-if="info.has_pdf" class="pdf-badge">PDF</span>
                  · {{ formatSize(info.size_bytes) }}
                  · {{ formatTime(info.mtime) }}
                </span>
              </div>
              <div class="ch-actions">
                <router-link :to="{ name: 'Reader', params: { photoId } }" class="action-link">阅读</router-link>
                <button class="action-del" @click="openRemoveChapter(album.id, photoId)">删除</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <transition name="modal-fade">
      <div v-if="confirmState" class="modal-mask" @click.self="closeConfirm">
        <div class="modal-box">
          <div class="modal-icon">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#dc2626" stroke-width="1.5">
              <polyline points="3 6 5 6 21 6"/>
              <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
              <path d="M10 11v6M14 11v6"/>
              <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>
            </svg>
          </div>

          <template v-if="confirmState.mode === 'album'">
            <h3 class="modal-title">删除整本缓存</h3>
            <p class="modal-desc">
              将删除《{{ getAlbumTitle(confirmState.albumId, pendingAlbum) }}》的全部缓存。
            </p>
          </template>
          <template v-else>
            <h3 class="modal-title">删除章节缓存</h3>
            <p class="modal-desc">
              将删除《{{ getAlbumTitle(confirmState.albumId, pendingAlbum) }}》中的
              「{{ getChapterTitle(confirmState.photoId, pendingChapter) }}」。
            </p>
          </template>

          <p v-if="pendingSummary" class="modal-meta">{{ pendingSummary }}</p>
          <p class="modal-warning">此操作不可撤销，已生成的 PDF 也会一并删除。</p>
          <p v-if="confirmError" class="modal-error">{{ confirmError }}</p>

          <div class="modal-actions">
            <button class="modal-cancel" :disabled="confirmLoading" @click="closeConfirm">取消</button>
            <button class="modal-confirm" :disabled="confirmLoading" @click="confirmRemove">
              {{ confirmLoading ? '删除中...' : '确认删除' }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.cache-view {
  padding: 20px 0 40px;
}

.container {
  max-width: 900px;
  margin: 0 auto;
  padding: 0 20px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 24px;
  gap: 12px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text);
}

.page-sub {
  font-size: 13px;
  color: var(--color-text-muted);
  margin-top: 4px;
}

.refresh-btn {
  padding: 7px 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 13px;
  color: var(--color-text-secondary);
  background: var(--color-bg);
  flex-shrink: 0;
  transition: all 0.2s;
}

.refresh-btn:hover:not(:disabled) {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.loading-state {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 60px 0;
  justify-content: center;
  color: var(--color-text-muted);
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.empty-state {
  text-align: center;
  padding: 80px 20px;
  color: var(--color-text-muted);
}

.empty-hint {
  font-size: 13px;
  margin-top: 8px;
}

.album-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.album-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}

.album-main {
  display: flex;
  gap: 16px;
  padding: 16px;
}

.cover-wrap {
  flex-shrink: 0;
  width: 80px;
  border-radius: 6px;
  overflow: hidden;
  aspect-ratio: 3 / 4;
  background: var(--color-border);
}

.cover-img :deep(.lazy-image-wrapper) {
  width: 100%;
  height: 100%;
}

.cover-img :deep(.lazy-image) {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.album-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.album-top {
  flex: 1;
}

.album-title {
  display: block;
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  line-height: 1.4;
  margin-bottom: 4px;
}

.album-title:hover {
  color: var(--color-primary);
}

.album-author {
  font-size: 12px;
  color: var(--color-text-muted);
  margin-bottom: 4px;
}

.album-stats {
  font-size: 12px;
  color: var(--color-text-muted);
}

.album-bottom {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  flex-wrap: wrap;
}

.toggle-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--color-primary);
  border: 1px solid var(--color-primary);
  border-radius: 12px;
  padding: 3px 10px;
  cursor: pointer;
  transition: all 0.2s;
}

.toggle-btn:hover {
  background: var(--color-primary);
  color: #fff;
}

.chevron {
  transition: transform 0.2s;
}

.chevron.expanded {
  transform: rotate(180deg);
}

.del-btn {
  font-size: 12px;
  color: #dc2626;
  border: 1px solid #dc2626;
  border-radius: 12px;
  padding: 3px 10px;
  cursor: pointer;
  transition: all 0.2s;
}

.del-btn:hover {
  background: #dc2626;
  color: #fff;
}

.chapter-list {
  border-top: 1px solid var(--color-border);
}

.chapter-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--color-border);
  transition: background 0.15s;
}

.chapter-row:last-child {
  border-bottom: none;
}

.chapter-row:hover {
  background: rgba(0, 0, 0, 0.02);
}

.ch-info {
  flex: 1;
  min-width: 0;
}

.ch-title {
  font-size: 13px;
  color: var(--color-text);
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ch-meta {
  font-size: 11px;
  color: var(--color-text-muted);
  margin-top: 2px;
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.pdf-badge {
  background: #ef4444;
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  padding: 0 5px;
  border-radius: 3px;
}

.ch-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

.action-link {
  font-size: 12px;
  color: var(--color-primary);
  padding: 3px 10px;
  border: 1px solid var(--color-primary);
  border-radius: 12px;
  transition: all 0.2s;
}

.action-link:hover {
  background: var(--color-primary);
  color: #fff;
}

.action-del {
  font-size: 12px;
  color: #dc2626;
  padding: 3px 10px;
  border: 1px solid #dc2626;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.action-del:hover {
  background: #dc2626;
  color: #fff;
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
  width: 100%;
  max-width: 380px;
  background: var(--color-surface);
  border-radius: var(--radius-md);
  padding: 28px 24px 22px;
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
}

.modal-meta {
  margin-top: 10px;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.modal-warning {
  margin-top: 10px;
  font-size: 13px;
  line-height: 1.6;
  color: #dc2626;
}

.modal-error {
  margin-top: 12px;
  font-size: 13px;
  color: #dc2626;
}

.modal-actions {
  display: flex;
  gap: 10px;
  margin-top: 22px;
}

.modal-cancel,
.modal-confirm {
  flex: 1;
  padding: 10px;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 600;
  transition: all 0.2s;
}

.modal-cancel {
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  background: var(--color-bg);
}

.modal-cancel:hover:not(:disabled) {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.modal-confirm {
  color: #fff;
  background: #dc2626;
}

.modal-confirm:hover:not(:disabled) {
  background: #b91c1c;
}

.modal-cancel:disabled,
.modal-confirm:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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

@media (max-width: 480px) {
  .cover-wrap {
    width: 64px;
  }

  .album-title {
    font-size: 14px;
  }

  .modal-box {
    padding: 24px 20px 20px;
  }
}
</style>
