import axios from 'axios'

const AUTH_TOKEN_KEY = 'auth_token'
const AUTH_USER_KEY = 'auth_user'
const AUTH_FLAG_KEY = 'is_authenticated'

function getStoredToken() {
  return localStorage.getItem(AUTH_TOKEN_KEY) || ''
}

function clearStoredAuth() {
  localStorage.removeItem(AUTH_TOKEN_KEY)
  localStorage.removeItem(AUTH_USER_KEY)
  localStorage.removeItem(AUTH_FLAG_KEY)
  window.dispatchEvent(new CustomEvent('auth:changed'))
}

const http = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

http.interceptors.request.use((config) => {
  const token = getStoredToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (res) => res.data,
  (err) => {
    if (err.response?.status === 401) {
      clearStoredAuth()
    }
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
export const login = (username, password) =>
  http.post('/auth/login', { username, password })

export const logout = () =>
  http.post('/auth/logout')

export const getCurrentUser = () =>
  http.get('/auth/me')

export const getAdminUsers = () =>
  http.get('/admin/users')

export const createAdminUser = (payload) =>
  http.post('/admin/users', payload)

export const updateAdminUser = (userId, payload) =>
  http.patch(`/admin/users/${userId}`, payload)

export const resetAdminUserPassword = (userId, newPassword) =>
  http.post(`/admin/users/${userId}/reset-password`, { new_password: newPassword })

export const deleteAdminUser = (userId) =>
  http.delete(`/admin/users/${userId}`)

export const changePassword = (payload) =>
  http.post('/auth/change-password', payload)

export const uploadAvatar = (file) => {
  const formData = new FormData()
  formData.append('avatar', file)
  return http.post('/users/me/avatar', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// ---- Favorites ----
export const getFavorites = (params = {}) =>
  http.get('/favorites', { params })

export const getFavoriteStatus = (albumId) =>
  http.get(`/favorites/${albumId}/status`)

export const addFavorite = (albumId, payload = {}) =>
  http.post('/favorites', { album_id: albumId, ...payload })

export const removeFavorite = (albumId) =>
  http.delete(`/favorites/${albumId}`)

// ---- History / Reading ----
export const getHistory = (params = {}) =>
  http.get('/history', { params })

export const upsertHistory = (payload) =>
  http.post('/history', payload)

export const removeHistory = (albumId) =>
  http.delete(`/history/${albumId}`)

export const clearHistory = () =>
  http.delete('/history')

export const saveReadingProgress = (payload) =>
  http.post('/reading/progress', payload)

export const getReadingState = (albumId) =>
  http.get(`/reading/${albumId}`)

// ---- Comment ----
export const getComments = (albumId, params = {}) =>
  http.get(`/comments/${albumId}`, { params })

export const postComment = (albumId, content, parentId = null) =>
  http.post(`/comments/${albumId}`, { content, parent_id: parentId })

export const deleteComment = (commentId) =>
  http.delete(`/comments/${commentId}`)

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
