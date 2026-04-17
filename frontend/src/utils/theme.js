import { ref, watch } from 'vue'

const STORAGE_KEY = 'theme'
const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')

function getInitialTheme() {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored === 'dark' || stored === 'light') return stored
  return mediaQuery.matches ? 'dark' : 'light'
}

export const theme = ref(getInitialTheme())

export const isDark = () => theme.value === 'dark'

export function toggleTheme() {
  const nextTheme = theme.value === 'dark' ? 'light' : 'dark'
  localStorage.setItem(STORAGE_KEY, nextTheme)
  theme.value = nextTheme
}

function apply(t) {
  document.documentElement.setAttribute('data-theme', t)
}

apply(theme.value)
watch(theme, apply)

mediaQuery.addEventListener('change', (e) => {
  if (!localStorage.getItem(STORAGE_KEY)) {
    theme.value = e.matches ? 'dark' : 'light'
  }
})
