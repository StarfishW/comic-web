import { ref } from 'vue'

const STORAGE_KEY = 'view_mode'

export const viewMode = ref(localStorage.getItem(STORAGE_KEY) || 'direct')
// 'direct'  = 直接观看（当前默认行为）
// 'cache'   = 缓存后观看
// 'pdf'     = 生成 PDF 并下载

export function setViewMode(mode) {
  viewMode.value = mode
  localStorage.setItem(STORAGE_KEY, mode)
}
