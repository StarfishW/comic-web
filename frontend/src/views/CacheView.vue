<script setup>
import { ref, computed, onMounted } from 'vue'
import { getCacheLibrary, deleteChapterCache, deleteAlbumCache, getCoverUrl } from '../api'
import LazyImage from '../components/LazyImage.vue'

const STORAGE_KEY = 'cache_meta'
const localMeta = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}')

function getAlbumTitle(albumId, albumInfo) {
  if (albumInfo?.album_title) return albumInfo.album_title
  const entry = Object.values(localMeta).find(m => m.albumId === albumId)
  return entry?.albumTitle || albumId
}
function getAlbumAuthor(albumId, albumInfo) {
  if (albumInfo?.author) return albumInfo.author
  const entry = Object.values(localMeta).find(m => m.albumId === albumId)
  return entry?.author || ''
}
function getChapterTitle(photoId, chapterInfo) {
  if (chapterInfo?.chapter_title) return chapterInfo.chapter_title
  return localMeta[photoId]?.chapterTitle || photoId
}

const library = ref({})
const totalSize = ref(0)
const loading = ref(true)
const error = ref(null)
const expandedAlbums = ref(new Set())

async function loadLibrary() {
  try {
    loading.value = true
    error.value = null
    const data = await getCacheLibrary()
    library.value = data.albums || {}
    totalSize.value = data.total_size_bytes || 0
  } catch {
    error.value = '加载失败'
  } finally {
    loading.value = false
  }
}

function toggleAlbum(albumId) {
  const s = new Set(expandedAlbums.value)
  s.has(albumId) ? s.delete(albumId) : s.add(albumId)
  expandedAlbums.value = s
}

async function removeChapter(albumId, photoId) {
  if (!confirm('确定删除该章节缓存？')) return
  try {
    await deleteChapterCache(albumId, photoId)
    const album = library.value[albumId]
    if (album) {
      const chapters = { ...album.chapters }
      const size = chapters[photoId]?.size_bytes || 0
      delete chapters[photoId]
      if (!Object.keys(chapters).length) {
        const newLib = { ...library.value }
        delete newLib[albumId]
        library.value = newLib
      } else {
        library.value = {
          ...library.value,
          [albumId]: { ...album, chapters, chapter_count: Object.keys(chapters).length, total_size_bytes: album.total_size_bytes - size }
        }
      }
      totalSize.value -= size
    }
  } catch { alert('删除失败') }
}

async function removeAlbum(albumId) {
  if (!confirm('确定删除该漫画的全部缓存？')) return
  try {
    await deleteAlbumCache(albumId)
    const size = library.value[albumId]?.total_size_bytes || 0
    const newLib = { ...library.value }
    delete newLib[albumId]
    library.value = newLib
    totalSize.value -= size
  } catch { alert('删除失败') }
}

function formatSize(bytes) {
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}
function formatTime(ts) {
  const d = new Date(ts * 1000)
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`
}

const albumList = computed(() => Object.entries(library.value).map(([id, info]) => ({ id, ...info })))

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
        <p class="empty-hint">在漫画目录页选择章节并缓存后，内容将在此显示</p>
      </div>

      <div v-else class="album-list">
        <div v-for="album in albumList" :key="album.id" class="album-card">
          <!-- 专辑主体 -->
          <div class="album-main">
            <!-- 封面 -->
            <router-link :to="{ name: 'ComicDetail', params: { id: album.id } }" class="cover-wrap">
              <LazyImage
                :src="getCoverUrl(album.id)"
                :alt="getAlbumTitle(album.id, album)"
                class="cover-img"
              />
            </router-link>

            <!-- 信息 -->
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
                <button
                  class="toggle-btn"
                  @click="toggleAlbum(album.id)"
                >
                  {{ expandedAlbums.has(album.id) ? '收起章节' : '查看章节' }}
                  <svg
                    :class="['chevron', { expanded: expandedAlbums.has(album.id) }]"
                    width="14" height="14" viewBox="0 0 24 24" fill="none"
                    stroke="currentColor" stroke-width="2"
                  ><polyline points="6 9 12 15 18 9"/></svg>
                </button>
                <button class="del-btn" @click="removeAlbum(album.id)">删除全部</button>
              </div>
            </div>
          </div>

          <!-- 章节列表 -->
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
                <button class="action-del" @click="removeChapter(album.id, photoId)">删除</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.cache-view { padding: 20px 0 40px; }
.container { max-width: 900px; margin: 0 auto; padding: 0 20px; }

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 24px;
  gap: 12px;
}
.page-title { font-size: 22px; font-weight: 700; color: var(--color-text); }
.page-sub { font-size: 13px; color: var(--color-text-muted); margin-top: 4px; }

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
.refresh-btn:hover:not(:disabled) { border-color: var(--color-primary); color: var(--color-primary); }
.refresh-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.loading-state {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 60px 0;
  justify-content: center;
  color: var(--color-text-muted);
}
.spinner {
  width: 20px; height: 20px;
  border: 2px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.empty-state { text-align: center; padding: 80px 20px; color: var(--color-text-muted); }
.empty-hint { font-size: 13px; margin-top: 8px; }

.album-list { display: flex; flex-direction: column; gap: 16px; }

.album-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}

/* 主体区域：封面 + 信息 */
.album-main {
  display: flex;
  gap: 16px;
  padding: 16px;
}

/* 封面 */
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

/* 信息区 */
.album-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.album-top { flex: 1; }

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
.album-title:hover { color: var(--color-primary); }

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
.toggle-btn:hover { background: var(--color-primary); color: #fff; }

.chevron { transition: transform 0.2s; }
.chevron.expanded { transform: rotate(180deg); }

.del-btn {
  font-size: 12px;
  color: #dc2626;
  border: 1px solid #dc2626;
  border-radius: 12px;
  padding: 3px 10px;
  cursor: pointer;
  transition: all 0.2s;
}
.del-btn:hover { background: #dc2626; color: #fff; }

/* 章节列表 */
.chapter-list { border-top: 1px solid var(--color-border); }

.chapter-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--color-border);
  transition: background 0.15s;
}
.chapter-row:last-child { border-bottom: none; }
.chapter-row:hover { background: rgba(0,0,0,0.02); }

.ch-info { flex: 1; min-width: 0; }
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

.ch-actions { display: flex; gap: 6px; flex-shrink: 0; }

.action-link {
  font-size: 12px;
  color: var(--color-primary);
  padding: 3px 10px;
  border: 1px solid var(--color-primary);
  border-radius: 12px;
  transition: all 0.2s;
}
.action-link:hover { background: var(--color-primary); color: #fff; }

.action-del {
  font-size: 12px;
  color: #dc2626;
  padding: 3px 10px;
  border: 1px solid #dc2626;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}
.action-del:hover { background: #dc2626; color: #fff; }

@media (max-width: 480px) {
  .cover-wrap { width: 64px; }
  .album-title { font-size: 14px; }
}
</style>
