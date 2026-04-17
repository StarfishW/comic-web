import { ref } from 'vue'

function defaultItems(data) {
  return data?.items || []
}

function defaultPageCount(data) {
  return Number(data?.page_count || 0)
}

function defaultTotal(data) {
  return Number(data?.total || 0)
}

function defaultErrorMessage(error) {
  return error?.response?.data?.detail || error?.message || '加载失败，请稍后重试'
}

export function usePagedList(options) {
  const {
    fetchPage,
    getItems = defaultItems,
    getPageCount = defaultPageCount,
    getTotal = defaultTotal,
    getErrorMessage = defaultErrorMessage,
    initialLoading = true,
  } = options

  const items = ref([])
  const loading = ref(initialLoading)
  const error = ref('')
  const page = ref(1)
  const pageCount = ref(0)
  const total = ref(0)
  const hasMore = ref(false)
  const loadingMore = ref(false)

  let activeRequestId = 0

  function applyPage(data, nextPage, append = false) {
    const nextItems = getItems(data)
    items.value = append ? [...items.value, ...nextItems] : nextItems
    page.value = nextPage
    pageCount.value = getPageCount(data)
    total.value = getTotal(data)
    hasMore.value = nextItems.length > 0 && nextPage < pageCount.value
  }

  function reset({ keepError = false } = {}) {
    activeRequestId += 1
    items.value = []
    loading.value = false
    loadingMore.value = false
    page.value = 1
    pageCount.value = 0
    total.value = 0
    hasMore.value = false
    if (!keepError) {
      error.value = ''
    }
  }

  async function refresh() {
    const requestId = ++activeRequestId
    loading.value = true
    loadingMore.value = false
    error.value = ''

    try {
      const data = await fetchPage({ page: 1 })
      if (requestId !== activeRequestId) return null
      applyPage(data, 1, false)
      return data
    } catch (err) {
      if (requestId !== activeRequestId) return null
      items.value = []
      page.value = 1
      pageCount.value = 0
      total.value = 0
      hasMore.value = false
      error.value = getErrorMessage(err)
      return null
    } finally {
      if (requestId === activeRequestId) {
        loading.value = false
      }
    }
  }

  async function loadMore() {
    if (loading.value || loadingMore.value || !hasMore.value) return null

    const requestId = activeRequestId
    const nextPage = page.value + 1
    loadingMore.value = true

    try {
      const data = await fetchPage({ page: nextPage })
      if (requestId !== activeRequestId) return null
      applyPage(data, nextPage, true)
      return data
    } catch {
      return null
    } finally {
      if (requestId === activeRequestId) {
        loadingMore.value = false
      }
    }
  }

  return {
    items,
    loading,
    error,
    page,
    pageCount,
    total,
    hasMore,
    loadingMore,
    refresh,
    loadMore,
    reset,
  }
}
