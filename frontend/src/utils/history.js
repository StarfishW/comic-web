const STORAGE_KEY = 'comic_history'
const MAX_ENTRIES = 100

export function getHistory() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
  } catch {
    return []
  }
}

/**
 * 添加/更新一条历史记录
 * @param {{ id: string, title: string, author: string }} comic
 */
export function addHistory(comic) {
  const history = getHistory().filter(h => h.id !== comic.id)
  history.unshift({ id: comic.id, title: comic.title, author: comic.author || '', visitedAt: Date.now() })
  localStorage.setItem(STORAGE_KEY, JSON.stringify(history.slice(0, MAX_ENTRIES)))
}

export function removeHistory(id) {
  const history = getHistory().filter(h => h.id !== id)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(history))
}

export function clearHistory() {
  localStorage.removeItem(STORAGE_KEY)
}
