import { ref, computed } from 'vue'
import http from '../api'

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

function readMeta() {
  try {
    return JSON.parse(localStorage.getItem(getStorageKey()) || '{}')
  } catch {
    return {}
  }
}

function writeMeta(value) {
  localStorage.setItem(getStorageKey(), JSON.stringify(value))
}

// 本地元数据：{ [photoId]: { albumId, albumTitle, chapterTitle } }
const meta = ref(readMeta())

// 队列条目（从后端拉取后与元数据合并）
export const queueItems = ref([])

export const activeCount = computed(() =>
  queueItems.value.filter(i => i.status === 'pending' || i.status === 'downloading').length
)

// 按 albumId 分组
export const groupedQueue = computed(() => {
  const groups = {}
  queueItems.value.forEach(item => {
    const key = item.albumId || item.album_id || 'unknown'
    if (!groups[key]) {
      groups[key] = {
        albumId: key,
        albumTitle: item.albumTitle || key,
        chapters: [],
      }
    }
    groups[key].chapters.push(item)
  })
  return Object.values(groups)
})

// 注册元数据（开始缓存时调用）
export function registerMeta(photoId, { albumId, albumTitle, chapterTitle }) {
  meta.value[photoId] = { albumId, albumTitle, chapterTitle }
  writeMeta(meta.value)
}

async function fetchQueue() {
  try {
    const data = await http.get('/cache/queue')
    queueItems.value = (data.queue || []).map(item => ({
      ...item,
      ...(meta.value[item.photo_id] || {}),
    }))
    return queueItems.value
  } catch {
    return []
  }
}

let pollerTimer = null
export const isPolling = ref(false)

export async function startPolling() {
  if (isPolling.value) return
  isPolling.value = true

  const tick = async () => {
    const items = await fetchQueue()
    const hasActive = items.some(i => i.status === 'pending' || i.status === 'downloading')
    if (hasActive && isPolling.value) {
      pollerTimer = setTimeout(tick, 2000)
    } else {
      isPolling.value = false
      pollerTimer = null
    }
  }
  await tick()
}

export function stopPolling() {
  isPolling.value = false
  if (pollerTimer) { clearTimeout(pollerTimer); pollerTimer = null }
}

// 主动刷新一次队列数据，并在有活跃任务时启动轮询
export async function refreshQueue() {
  const items = await fetchQueue()
  if (items.some(i => i.status === 'pending' || i.status === 'downloading')) {
    startPolling()
  }
  return items
}

// 页面初始化时调用
export async function initQueue() {
  await refreshQueue()
}

// 清除已完成的记录（前端 + 后端）
export async function clearCompleted() {
  try {
    await http.delete('/cache/queue/completed')
    await fetchQueue()
    // 清理本地元数据中已不在队列中的条目
    const activeIds = new Set(queueItems.value.map(i => i.photo_id))
    const newMeta = {}
    Object.entries(meta.value).forEach(([id, m]) => {
      if (activeIds.has(id)) newMeta[id] = m
    })
    meta.value = newMeta
    writeMeta(newMeta)
  } catch { /* silent */ }
}
