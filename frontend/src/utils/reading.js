function isObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function asObject(value) {
  return isObject(value) ? value : {}
}

function toId(value) {
  if (value === 0 || value === '0') return '0'
  if (value === null || value === undefined || value === '') return ''
  return String(value)
}

function toNumber(value) {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

function toInteger(value) {
  const parsed = toNumber(value)
  return parsed === null ? null : Math.trunc(parsed)
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max)
}

function pickFirst(items, predicate = (value) => value !== null && value !== undefined && value !== '') {
  return items.find(predicate)
}

function pickNumber(...items) {
  return pickFirst(items.map(toNumber), (value) => value !== null)
}

function pickId(...items) {
  return pickFirst(items.map(toId), (value) => value !== '')
}

function pickBoolean(...items) {
  for (const item of items) {
    if (typeof item === 'boolean') return item
    if (item === 1 || item === '1') return true
    if (item === 0 || item === '0') return false
    if (typeof item === 'string') {
      const normalized = item.trim().toLowerCase()
      if (['true', 'yes', 'y', 'on'].includes(normalized)) return true
      if (['false', 'no', 'n', 'off'].includes(normalized)) return false
    }
  }
  return false
}

function toTimestamp(value) {
  const numeric = toNumber(value)
  if (numeric !== null) {
    return numeric > 1e12 ? numeric : numeric > 1e9 ? numeric * 1000 : numeric
  }
  if (typeof value === 'string' && value.trim()) {
    const parsed = Date.parse(value)
    return Number.isFinite(parsed) ? parsed : 0
  }
  return 0
}

function unwrapPayload(value) {
  if (!isObject(value)) return {}
  if (isObject(value.data)) return value.data
  if (isObject(value.item)) return value.item
  return value
}

function normalizeTotalPages(entry) {
  const images = Array.isArray(entry.images) ? entry.images.length : null
  const total = pickNumber(
    entry.total_pages,
    entry.totalPages,
    entry.page_total,
    entry.page_count,
    entry.image_count,
    images,
  )
  return total && total > 0 ? Math.trunc(total) : 0
}

function normalizePageInfo(entry, totalPages) {
  const explicitIndex = pickNumber(
    entry.page_index,
    entry.current_page_index,
    entry.currentIndex,
    entry.index_zero_based,
  )
  const explicitPage = pickNumber(
    entry.last_page,
    entry.current_page,
    entry.page,
    entry.page_no,
    entry.pageNumber,
    entry.current,
  )

  let pageIndex = explicitIndex
  let currentPage = explicitPage

  if (pageIndex === null && explicitPage !== null) {
    pageIndex = explicitPage <= 0 ? 0 : explicitPage - 1
  }
  if (currentPage === null && pageIndex !== null) {
    currentPage = pageIndex + 1
  }
  if (currentPage === 0) {
    currentPage = 1
  }

  if (totalPages > 0) {
    if (pageIndex !== null) {
      pageIndex = clamp(Math.trunc(pageIndex), 0, Math.max(totalPages - 1, 0))
    }
    if (currentPage !== null) {
      currentPage = clamp(Math.trunc(currentPage), 1, totalPages)
    }
  }

  if (pageIndex === null) {
    pageIndex = currentPage ? Math.max(currentPage - 1, 0) : 0
  }
  if (currentPage === null) {
    currentPage = pageIndex + 1
  }

  return {
    pageIndex,
    currentPage,
  }
}

function normalizeProgress(entry, currentPage, totalPages) {
  const explicit = pickNumber(
    entry.progress,
    entry.progress_percent,
    entry.percent,
    entry.read_percent,
  )

  if (explicit !== null) {
    if (explicit <= 1) {
      return clamp(Math.round(explicit * 100), 0, 100)
    }
    return clamp(Math.round(explicit), 0, 100)
  }

  if (totalPages > 0) {
    return clamp(Math.round((currentPage / totalPages) * 100), 0, 100)
  }

  return 0
}

function normalizeChapterEntry(entry, fallbackAlbumId = '') {
  const raw = asObject(entry)
  const photoId = pickId(raw.photo_id, raw.photoId, raw.chapter_id, raw.chapterId, raw.episode_id, raw.episodeId, raw.id)

  if (!photoId) return null

  const totalPages = normalizeTotalPages(raw)
  const { pageIndex, currentPage } = normalizePageInfo(raw, totalPages)
  const progress = normalizeProgress(raw, currentPage, totalPages)
  const updatedAt = Math.max(
    toTimestamp(raw.updated_at),
    toTimestamp(raw.last_read_at),
    toTimestamp(raw.visited_at),
    toTimestamp(raw.timestamp),
    toTimestamp(raw.created_at),
  )
  const isRead = pickBoolean(raw.is_read, raw.read, raw.completed, raw.finished) || progress >= 99
  const visited = pickBoolean(raw.visited, raw.viewed, raw.seen) || progress > 0 || updatedAt > 0

  return {
    albumId: pickId(raw.album_id, raw.albumId, fallbackAlbumId),
    photoId,
    title: pickFirst([raw.chapter_title, raw.episode_title, raw.title, raw.name], (value) => typeof value === 'string' && value.trim() !== '') || '',
    sort: pickNumber(raw.chapter_sort, raw.sort, raw.album_index, raw.index, raw.order, raw.seq),
    pageIndex,
    currentPage,
    totalPages,
    progress,
    isRead,
    visited,
    updatedAt,
  }
}

function collectChapterCandidates(source) {
  const candidates = [
    source.chapters,
    source.chapter_states,
    source.chapter_progress,
    source.chapter_progresses,
    source.reading_progress,
    source.progress_list,
    source.history_items,
    source.episodes,
    source.records,
    source.items,
    source.history?.chapters,
    source.history?.items,
    source.progress?.chapters,
    source.progress?.items,
  ]

  const match = candidates.find(Array.isArray)
  return match || []
}

function chooseLatestChapter(chapters) {
  if (!chapters.length) return null

  return [...chapters].sort((left, right) => {
    if (right.updatedAt !== left.updatedAt) return right.updatedAt - left.updatedAt
    if (right.progress !== left.progress) return right.progress - left.progress
    return (right.sort || 0) - (left.sort || 0)
  })[0]
}

export function normalizeReadingState(rawState, fallbackAlbumId = '') {
  const source = unwrapPayload(rawState)
  const albumId = pickId(source.album_id, source.albumId, source.id, fallbackAlbumId)
  const chapterMap = {}

  collectChapterCandidates(source).forEach((entry) => {
    const normalized = normalizeChapterEntry(entry, albumId)
    if (!normalized) return

    const existing = chapterMap[normalized.photoId]
    if (!existing) {
      chapterMap[normalized.photoId] = normalized
      return
    }

    if (
      normalized.updatedAt > existing.updatedAt ||
      normalized.progress > existing.progress ||
      normalized.currentPage > existing.currentPage
    ) {
      chapterMap[normalized.photoId] = { ...existing, ...normalized }
    }
  })

  const chapters = Object.values(chapterMap)
  const latestChapter = chooseLatestChapter(chapters)
  const lastReadPhotoId = pickId(
    source.last_read_photo_id,
    source.lastReadPhotoId,
    source.current_photo_id,
    source.currentPhotoId,
    source.photo_id,
    source.photoId,
    source.progress?.photo_id,
    source.history?.photo_id,
    latestChapter?.photoId,
  )
  const lastChapter = (lastReadPhotoId && chapterMap[lastReadPhotoId]) || latestChapter
  const progress = clamp(
    Math.round(
      pickNumber(
        source.progress,
        source.progress_percent,
        source.read_percent,
        lastChapter?.progress,
        0,
      ) || 0,
    ),
    0,
    100,
  )

  return {
    albumId,
    isFavorite: pickBoolean(
      source.is_favorite,
      source.favorite,
      source.favorited,
      source.collected,
      source.in_favorites,
    ),
    lastReadPhotoId,
    lastReadPage: lastChapter?.currentPage || 0,
    lastReadPageIndex: lastChapter?.pageIndex || 0,
    progress,
    updatedAt: lastChapter?.updatedAt || 0,
    chapterMap,
    chapters,
  }
}

export function mergeEpisodesWithReadingState(episodes = [], readingState = null) {
  const chapterMap = readingState?.chapterMap || {}
  const lastReadPhotoId = readingState?.lastReadPhotoId || ''

  return episodes.map((episode) => {
    const reading = chapterMap[toId(episode.id)] || null
    return {
      ...episode,
      reading,
      isLastRead: lastReadPhotoId !== '' && toId(episode.id) === lastReadPhotoId,
    }
  })
}

export function buildReadingProgressPayload({
  albumId,
  photoId,
  currentPageIndex = 0,
  totalPages = 0,
  comicTitle = '',
  chapterTitle = '',
  author = '',
  sort = null,
  mode = '',
} = {}) {
  const safeTotal = Math.max(toInteger(totalPages) || 0, 0)
  const maxIndex = safeTotal > 0 ? safeTotal - 1 : 0
  const pageIndex = clamp(Math.max(toInteger(currentPageIndex) || 0, 0), 0, maxIndex)
  const currentPage = safeTotal > 0 ? pageIndex + 1 : 0
  const progress = safeTotal > 0 ? clamp(Math.round((currentPage / safeTotal) * 100), 0, 100) : 0

  return {
    album_id: toId(albumId),
    photo_id: toId(photoId),
    page_index: pageIndex,
    current_page: currentPage,
    page: currentPage,
    last_page: currentPage,
    total_pages: safeTotal,
    progress,
    progress_percent: progress,
    completed: safeTotal > 0 && currentPage >= safeTotal,
    title: comicTitle,
    comic_title: comicTitle,
    album_title: comicTitle,
    album_author: author,
    chapter_title: chapterTitle,
    episode_title: chapterTitle,
    chapter_sort: sort === null || sort === undefined ? null : sort,
    author,
    sort: sort === null || sort === undefined ? null : sort,
    reader_mode: mode,
    updated_at: new Date().toISOString(),
  }
}

export function buildHistoryPayload(input = {}) {
  const progressPayload = buildReadingProgressPayload(input)

  return {
    ...progressPayload,
    title: progressPayload.comic_title,
    visited_at: progressPayload.updated_at,
  }
}

export function formatEpisodeProgress(state) {
  if (!state) return ''
  if (state.isRead) return '已读'
  if (state.progress > 0) return `${state.progress}%`
  if (state.visited) return '已看'
  return ''
}
