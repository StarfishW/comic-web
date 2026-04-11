import { ref, computed } from 'vue'

const STORAGE_KEY = 'placeholder_style'

// 各风格的 SVG data URI
const SVGS = {
  'icon-dark': "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 3 4'%3E%3Crect width='3' height='4' fill='%23262626'/%3E%3Ccircle cx='1.5' cy='1.6' r='0.5' fill='%23555'/%3E%3Cpath d='M0.5 2.8 L1.2 2.1 L1.8 2.5 L2.3 1.9 L2.8 2.8Z' fill='%23555'/%3E%3C/svg%3E",
  'icon-light': "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 3 4'%3E%3Crect width='3' height='4' fill='%23f0f0f0'/%3E%3Ccircle cx='1.5' cy='1.6' r='0.5' fill='%23bbb'/%3E%3Cpath d='M0.5 2.8 L1.2 2.1 L1.8 2.5 L2.3 1.9 L2.8 2.8Z' fill='%23bbb'/%3E%3C/svg%3E",
  'solid-dark': "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1 1'%3E%3Crect width='1' height='1' fill='%23262626'/%3E%3C/svg%3E",
  'solid-light': "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1 1'%3E%3Crect width='1' height='1' fill='%23e5e7eb'/%3E%3C/svg%3E",
}

// 所有可选风格的描述（供 SettingsView 遍历展示）
export const PLACEHOLDER_STYLES = [
  { key: 'icon-dark',   label: '深色图标' },
  { key: 'icon-light',  label: '浅色图标' },
  { key: 'solid-dark',  label: '纯深色'   },
  { key: 'solid-light', label: '纯浅色'   },
  { key: 'shimmer',     label: '渐变动画' },
]

// 当前选中风格（响应式，全局共享）
export const placeholderStyle = ref(localStorage.getItem(STORAGE_KEY) || 'icon-dark')

// 切换风格并持久化
export function setPlaceholderStyle(style) {
  placeholderStyle.value = style
  localStorage.setItem(STORAGE_KEY, style)
}

// 当前风格对应的 src（shimmer 时返回空字符串，由 LazyImage 自行渲染动画）
export const placeholderSrc = computed(() =>
  SVGS[placeholderStyle.value] ?? SVGS['icon-dark']
)

// 是否是 shimmer 风格
export const isShimmerStyle = computed(() => placeholderStyle.value === 'shimmer')
