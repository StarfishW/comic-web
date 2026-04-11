import { ref, watch } from 'vue'

const STORAGE_KEY = 'theme'

function getInitialTheme() {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored === 'dark' || stored === 'light') return stored
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export const theme = ref(getInitialTheme())

export const isDark = () => theme.value === 'dark'

export function toggleTheme() {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
}

function apply(t) {
  document.documentElement.setAttribute('data-theme', t)
  localStorage.setItem(STORAGE_KEY, t)
}

// 立即应用，并监听变化
apply(theme.value)
watch(theme, apply)

// 监听系统主题变化（仅当用户未手动设置时）
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
  if (!localStorage.getItem(STORAGE_KEY)) {
    theme.value = e.matches ? 'dark' : 'light'
  }
})
