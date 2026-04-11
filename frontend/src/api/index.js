import axios from 'axios'

const http = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

http.interceptors.response.use(
  (res) => res.data,
  (err) => {
    console.error('[API Error]', err.response?.status, err.message)
    return Promise.reject(err)
  },
)

// ---- Browse / Category ----
export const getComics = (params = {}) =>
  http.get('/comics', { params })

export const getRanking = (type, params = {}) =>
  http.get(`/ranking/${type}`, { params })

// ---- Search ----
export const searchComics = (q, params = {}) =>
  http.get('/search', { params: { q, ...params } })

// ---- Detail ----
export const getComicDetail = (albumId) =>
  http.get(`/comics/${albumId}`)

export const getCoverUrl = (albumId) =>
  `/api/comics/${albumId}/cover`

// ---- Chapter ----
export const getChapterDetail = (photoId) =>
  http.get(`/chapters/${photoId}`)

export const getChapterImageUrl = (photoId, index) =>
  `/api/chapters/${photoId}/images/${index}`

// ---- Auth ----
export const login = (password) =>
  http.post('/auth/login', { password })

// ---- Favorites ----
export const getFavorites = (params = {}) =>
  http.get('/favorites', { params })

export const addFavorite = (albumId, folderId = '0') =>
  http.post('/favorites', { album_id: albumId, folder_id: folderId })

// ---- Comment ----
export const postComment = (videoId, comment, commentId = null) =>
  http.post('/comments', { video_id: videoId, comment, comment_id: commentId })

// ---- Domain Management ----
export const getDomains = () =>
  http.get('/domains')

export const pingDomains = () =>
  http.get('/domains/ping', { timeout: 60000 })

export const switchDomain = (domain) =>
  http.post('/domains/switch', { domain })

// ---- Chapter Cache ----
export const startChapterCache = (albumId, photoId, meta = {}) =>
  http.post(`/chapters/${albumId}/${photoId}/cache`, meta)

export const getChapterCacheStatus = (albumId, photoId) =>
  http.get(`/chapters/${albumId}/${photoId}/cache/status`)

export const getCachedImageUrl = (albumId, photoId, index) =>
  `/api/chapters/${albumId}/${photoId}/cached/${index}`

export const getAlbumCacheStatus = (albumId) =>
  http.get(`/comics/${albumId}/cache/status`)

// ---- Cache Library ----
export const getCacheLibrary = () =>
  http.get('/cache/library')

export const deleteChapterCache = (albumId, photoId) =>
  http.delete(`/cache/${albumId}/${photoId}`)

export const deleteAlbumCache = (albumId) =>
  http.delete(`/cache/${albumId}`)

// ---- Chapter PDF ----
export const startChapterPdf = (albumId, photoId) =>
  http.post(`/chapters/${albumId}/${photoId}/pdf`)

export const getChapterPdfStatus = (albumId, photoId) =>
  http.get(`/chapters/${albumId}/${photoId}/pdf/status`)

export const getChapterPdfDownloadUrl = (albumId, photoId) =>
  `/api/chapters/${albumId}/${photoId}/pdf/download`

export default http
