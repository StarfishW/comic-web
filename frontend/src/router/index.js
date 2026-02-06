import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('../views/HomeView.vue'),
  },
  {
    path: '/comic/:id',
    name: 'ComicDetail',
    component: () => import('../views/ComicDetailView.vue'),
    props: true,
  },
  {
    path: '/reader/:photoId',
    name: 'Reader',
    component: () => import('../views/ReaderView.vue'),
    props: true,
  },
  {
    path: '/search',
    name: 'Search',
    component: () => import('../views/SearchView.vue'),
  },
  {
    path: '/ranking',
    name: 'Ranking',
    component: () => import('../views/RankingView.vue'),
  },
  {
    path: '/favorites',
    name: 'Favorites',
    component: () => import('../views/FavoritesView.vue'),
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue'),
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../views/SettingsView.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  },
})

// Navigation guard - require authentication for all routes except login
router.beforeEach((to, from, next) => {
  const isAuthenticated = localStorage.getItem('is_authenticated') === 'true'

  if (to.name !== 'Login' && !isAuthenticated) {
    // Redirect to login if not authenticated
    next({ name: 'Login' })
  } else if (to.name === 'Login' && isAuthenticated) {
    // Redirect to home if already authenticated
    next({ name: 'Home' })
  } else {
    next()
  }
})

export default router
