<script setup>
import { ref, onMounted } from 'vue'
import { getComics } from '../api'
import ComicCard from '../components/ComicCard.vue'
import SkeletonGrid from '../components/SkeletonGrid.vue'

const comics = ref([])
const loading = ref(true)
const error = ref(null)
const page = ref(1)
const hasMore = ref(true)
const loadingMore = ref(false)
const orderBy = ref('mr')

const orderOptions = [
  { value: 'mr', label: '最新' },
  { value: 'mv', label: '最多观看' },
  { value: 'mp', label: '最多图片' },
  { value: 'tf', label: '最多喜欢' },
]

async function fetchData() {
  try {
    loading.value = true
    error.value = null
    page.value = 1
    const data = await getComics({ page: 1, order_by: orderBy.value })
    comics.value = data.items || []
    hasMore.value = comics.value.length > 0 && page.value < (data.page_count || 1)
  } catch (e) {
    error.value = '加载失败，请检查后端是否启动'
  } finally {
    loading.value = false
  }
}

async function loadMore() {
  if (loadingMore.value || !hasMore.value) return
  try {
    loadingMore.value = true
    page.value++
    const data = await getComics({ page: page.value, order_by: orderBy.value })
    const items = data.items || []
    comics.value.push(...items)
    hasMore.value = items.length > 0 && page.value < (data.page_count || 1)
  } catch {
    page.value--
  } finally {
    loadingMore.value = false
  }
}

function changeOrder(val) {
  orderBy.value = val
  fetchData()
}

onMounted(fetchData)
</script>

<template>
  <div class="home">
    <div class="container">
      <div class="toolbar">
        <h2 class="section-title">全部漫画</h2>
        <div class="order-tabs">
          <button
            v-for="opt in orderOptions"
            :key="opt.value"
            :class="['tab', { active: orderBy === opt.value }]"
            @click="changeOrder(opt.value)"
          >
            {{ opt.label }}
          </button>
        </div>
      </div>

      <SkeletonGrid v-if="loading" />

      <div v-else-if="error" class="error-state">
        <p>{{ error }}</p>
        <button class="retry-btn" @click="fetchData">重试</button>
      </div>

      <div v-else class="comic-grid">
        <ComicCard v-for="c in comics" :key="c.id" :comic="c" />
      </div>

      <div v-if="!loading && hasMore" class="load-more">
        <button class="load-more-btn" :disabled="loadingMore" @click="loadMore">
          <span v-if="loadingMore" class="spinner"></span>
          {{ loadingMore ? '加载中...' : '加载更多' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.container {
  max-width: 1280px;
  margin: 0 auto;
  padding: 20px 20px 40px;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 12px;
}

.section-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--color-text);
}

.order-tabs {
  display: flex;
  gap: 4px;
}

.tab {
  padding: 5px 14px;
  border-radius: 16px;
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
  transition: all 0.2s;
}

.tab:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.tab.active {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
}

.comic-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px;
}

.error-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--color-text-secondary);
}

.retry-btn {
  margin-top: 16px;
  padding: 8px 24px;
  background: var(--color-primary);
  color: #fff;
  border-radius: var(--radius-sm);
  font-weight: 500;
  transition: background 0.2s;
}

.retry-btn:hover {
  background: var(--color-primary-hover);
}

.load-more {
  text-align: center;
  padding: 32px 0;
}

.load-more-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 32px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-secondary);
  transition: all 0.2s;
}

.load-more-btn:hover:not(:disabled) {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.load-more-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 640px) {
  .comic-grid {
    grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
    gap: 10px;
  }

  .section-title { font-size: 18px; }
}
</style>
