import { createRouter, createWebHistory } from 'vue-router'
import { authState, initAuth, isAdminUser } from '../utils/auth'

function protectedRoute(route, meta = {}) {
  return {
    ...route,
    meta: {
      requiresAuth: true,
      ...meta,
      ...(route.meta || {}),
    },
  }
}

const routes = [
  protectedRoute({
    path: '/',
    name: 'Home',
    component: () => import('../views/HomeView.vue'),
  }),
  protectedRoute({
    path: '/comic/:id',
    name: 'ComicDetail',
    component: () => import('../views/ComicDetailView.vue'),
    props: true,
  }),
  protectedRoute({
    path: '/reader/:photoId',
    name: 'Reader',
    component: () => import('../views/ReaderView.vue'),
    props: true,
  }),
  protectedRoute({
    path: '/search',
    name: 'Search',
    component: () => import('../views/SearchView.vue'),
  }),
  protectedRoute({
    path: '/ranking',
    name: 'Ranking',
    component: () => import('../views/RankingView.vue'),
  }),
  protectedRoute({
    path: '/favorites',
    name: 'Favorites',
    component: () => import('../views/FavoritesView.vue'),
  }),
  protectedRoute({
    path: '/history',
    name: 'History',
    component: () => import('../views/HistoryView.vue'),
  }),
  protectedRoute({
    path: '/cache',
    name: 'Cache',
    component: () => import('../views/CacheView.vue'),
  }),
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue'),
    meta: {
      guestOnly: true,
    },
  },
  protectedRoute({
    path: '/settings',
    name: 'Settings',
    component: () => import('../views/SettingsView.vue'),
  }),
  protectedRoute(
    {
      path: '/admin/users',
      name: 'AdminUsers',
      component: () => import('../views/AdminUsersView.vue'),
    },
    {
      requiresAdmin: true,
    },
  ),
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    }

    return { top: 0 }
  },
})

router.beforeEach(async (to) => {
  await initAuth()

  const requiresAuth = to.matched.some((record) => record.meta.requiresAuth)
  const guestOnly = to.matched.some((record) => record.meta.guestOnly)
  const requiresAdmin = to.matched.some((record) => record.meta.requiresAdmin)

  if (requiresAuth && !authState.user) {
    return {
      name: 'Login',
      query: {
        redirect: to.fullPath,
      },
    }
  }

  if (guestOnly && authState.user) {
    const redirect = typeof to.query.redirect === 'string' && to.query.redirect.startsWith('/')
      ? to.query.redirect
      : '/'

    return redirect
  }

  if (requiresAdmin && !isAdminUser(authState.user)) {
    return { name: 'Home' }
  }

  return true
})

export default router
