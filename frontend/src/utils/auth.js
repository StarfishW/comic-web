import { reactive, readonly } from 'vue'
import * as api from '../api'

const AUTH_FLAG_KEY = 'is_authenticated'
const AUTH_TOKEN_KEY = 'auth_token'
const AUTH_USER_KEY = 'auth_user'

const state = reactive({
  user: readStoredUser(),
  ready: false,
  loading: false,
})

let initPromise = null

function readStoredUser() {
  if (typeof window === 'undefined') {
    return null
  }

  try {
    const raw = localStorage.getItem(AUTH_USER_KEY)
    if (!raw) {
      return null
    }
    return normalizeUser(JSON.parse(raw))
  } catch {
    localStorage.removeItem(AUTH_USER_KEY)
    return null
  }
}

function persistUser(user, token) {
  if (typeof window === 'undefined') {
    return
  }

  localStorage.setItem(AUTH_FLAG_KEY, 'true')
  localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user))

  if (token) {
    localStorage.setItem(AUTH_TOKEN_KEY, token)
  }
}

function clearStoredAuth() {
  if (typeof window === 'undefined') {
    return
  }

  localStorage.removeItem(AUTH_FLAG_KEY)
  localStorage.removeItem(AUTH_TOKEN_KEY)
  localStorage.removeItem(AUTH_USER_KEY)
}

function normalizeUser(rawUser) {
  if (!rawUser || typeof rawUser !== 'object') {
    return null
  }

  const username = rawUser.username || rawUser.user_name || rawUser.account || rawUser.login || ''
  const displayName = rawUser.display_name || rawUser.displayName || rawUser.nickname || rawUser.name || username

  return {
    ...rawUser,
    username,
    displayName,
  }
}

function extractUser(payload) {
  if (!payload) {
    return null
  }

  if (payload.user) {
    return payload.user
  }

  if (payload.currentUser) {
    return payload.currentUser
  }

  if (payload.data?.user) {
    return payload.data.user
  }

  if (typeof payload === 'object') {
    return payload
  }

  return null
}

function setUser(user, options = {}) {
  const normalizedUser = normalizeUser(user)

  if (!normalizedUser) {
    clearAuthState()
    return null
  }

  state.user = normalizedUser
  state.ready = true
  persistUser(normalizedUser, options.token)
  return normalizedUser
}

function clearAuthState() {
  state.user = null
  state.ready = true
  clearStoredAuth()
}

function syncFromStorage() {
  state.user = readStoredUser()
  state.ready = true
}

function isUnauthorizedError(error) {
  const status = error?.response?.status
  return status === 401 || status === 403
}

export const authState = readonly(state)

export function isAdminUser(user = state.user) {
  if (!user) {
    return false
  }

  const roles = []

  if (Array.isArray(user.roles)) {
    roles.push(...user.roles)
  }

  if (user.role) {
    roles.push(user.role)
  }

  if (user.user_role) {
    roles.push(user.user_role)
  }

  const normalizedRoles = roles
    .filter(Boolean)
    .map((item) => String(item).toLowerCase())

  return Boolean(
    user.is_admin ||
    user.isAdmin ||
    user.admin ||
    normalizedRoles.includes('admin') ||
    normalizedRoles.includes('super_admin') ||
    normalizedRoles.includes('superadmin'),
  )
}

export function getUserLabel(user = state.user) {
  if (!user) {
    return ''
  }

  return user.displayName || user.username || '当前用户'
}

export function setAuthUser(user, options = {}) {
  return setUser(user, options)
}

export async function initAuth(options = {}) {
  const { force = false } = options

  if (state.ready && !force) {
    return state.user
  }

  if (initPromise && !force) {
    return initPromise
  }

  if (typeof api.getCurrentUser !== 'function') {
    state.ready = true
    return state.user
  }

  initPromise = (async () => {
    state.loading = true

    try {
      const response = await api.getCurrentUser()
      const user = extractUser(response)

      if (!user) {
        clearAuthState()
        return null
      }

      return setUser(user)
    } catch (error) {
      if (isUnauthorizedError(error) || !state.user) {
        clearAuthState()
        return null
      }

      state.ready = true
      return state.user
    } finally {
      state.loading = false
      initPromise = null
    }
  })()

  return initPromise
}

export async function loginWithPassword(username, password) {
  const trimmedUsername = username.trim()

  if (!trimmedUsername || !password) {
    throw new Error('请输入用户名和密码')
  }

  if (typeof api.login !== 'function') {
    throw new Error('登录接口未接入')
  }

  state.loading = true

  try {
    const response = await (api.login.length >= 2
      ? api.login(trimmedUsername, password)
      : api.login(password))

    const responseUser = extractUser(response)
    const fallbackUser = responseUser || { username: trimmedUsername, displayName: trimmedUsername }
    const optimisticUser = setUser(fallbackUser, { token: response?.token })

    if (typeof api.getCurrentUser === 'function') {
      try {
        const refreshedUser = await initAuth({ force: true })

        if (!refreshedUser && optimisticUser) {
          setUser(optimisticUser, { token: response?.token })
        }
      } catch {
        // Keep the optimistic user state when the current-user endpoint is not ready yet.
        if (optimisticUser) {
          setUser(optimisticUser, { token: response?.token })
        }
      }
    }

    return state.user
  } finally {
    state.loading = false
  }
}

export async function logoutUser() {
  try {
    if (typeof api.logout === 'function') {
      await api.logout()
    }
  } finally {
    clearAuthState()
  }
}

if (typeof window !== 'undefined') {
  window.addEventListener('storage', (event) => {
    if (![AUTH_FLAG_KEY, AUTH_USER_KEY, AUTH_TOKEN_KEY].includes(event.key)) {
      return
    }

    syncFromStorage()
  })

  window.addEventListener('auth:changed', syncFromStorage)
}
