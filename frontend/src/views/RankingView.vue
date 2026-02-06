<script setup>
import { ref, onMounted } from 'vue'
import { getRanking } from '../api'
import ComicCard from '../components/ComicCard.vue'
import SkeletonGrid from '../components/SkeletonGrid.vue'

const comics = ref([])
const loading = ref(true)
const page = ref(1)
const hasMore = ref(false)
const loadingMore = ref(false)
const rankType = ref('day')
const category = ref('0')
const pageCount = ref(0)

const rankTypes = [
  { value: 'all', label: '总榜' },
  { value: 'day', label: '日榜' },
  { value: 'week', label: '周榜' },
  { value: 'month', label: '月榜' },
]

const categories = [
  { value: '0', label: '全部' },
  { value: 'doujin', label: '同人' },
  { value: 'single', label: '单本' },
  { value: 'short', label: '短篇' },
  { value: 'hanman', label: '韩漫' },
  { value: 'meiman', label: '美漫' },
  { value: 'doujin_cosplay', label: 'Cosplay' },
  { value: '3D', label: '3D' },
  { value: 'english_site', label: '英文站' },
  { value: 'another', label: '其他' },
]

async function fetchRanking() {
  try {
    loading.value = true
    page.value = 1
    const data = await getRanking(rankType.value, { page: 1, category: category.value })
    comics.value = data.items || []
    pageCount.value = data.page_count || 0
    hasMore.value = page.value < pageCount.value
  } catch {
    comics.value = []
  } finally {
    loading.value = false
  }
}

async function loadMore() {
  if (loadingMore.value || !hasMore.value) return
  try {
    loadingMore.value = true
    page.value++
    const data = await getRanking(rankType.value, { page: page.value, category: category.value })
    comics.value.push(...(data.items || []))
    hasMore.value = page.value < (data.page_count || 0)
  } catch {
    page.value--
  } finally {
    loadingMore.value = false
  }
}

function changeType(val) {
  rankType.value = val
  fetchRanking()
}

function changeCategory(val) {
  category.value = val
  fetchRanking()
}

onMounted(fetchRanking)
</script>

<template>
  <div class="ranking-view">
    <div class="container">
      <div class="layout">
        <!-- Left: Category sidebar -->
        <aside class="sidebar">
          <h3 class="sidebar-title">类别</h3>
          <nav class="cat-nav">
            <button
              v-for="c in categories"
              :key="c.value"
              :class="['cat-item', { active: category === c.value }]"
              @click="changeCategory(c.value)"
            >{{ c.label }}</button>
          </nav>
        </aside>

        <!-- Right: Main content -->
        <div class="main">
          <div class="toolbar">
            <h1 class="page-title">排行榜</h1>
            <div class="type-tabs">
              <button
                v-for="t in rankTypes"
                :key="t.value"
                :class="['tab', { active: rankType === t.value }]"
                @click="changeType(t.value)"
              >{{ t.label }}</button>
            </div>
          </div>

          <!-- Mobile category chips -->
          <div class="mobile-cats">
            <button
              v-for="c in categories"
              :key="c.value"
              :class="['tab', { active: category === c.value }]"
              @click="changeCategory(c.value)"
            >{{ c.label }}</button>
          </div>

          <SkeletonGrid v-if="loading" :count="12" />

          <div v-else-if="!comics.length" class="empty-state">
            <p>暂无排行数据</p>
          </div>

          <div v-else class="comic-grid">
            <ComicCard v-for="c in comics" :key="c.id" :comic="c" />
          </div>

          <div v-if="!loading && hasMore" class="load-more">
            <button class="load-more-btn" :disabled="loadingMore" @click="loadMore">
              {{ loadingMore ? '加载中...' : '加载更多' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ranking-view { padding: 20px 0 40px; }

.container {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 20px;
}

.layout {
  display: flex;
  gap: 24px;
  align-items: flex-start;
}

/* Sidebar */
.sidebar {
  width: 140px;
  flex-shrink: 0;
  position: sticky;
  top: 84px;
  background: var(--color-surface);
  border-radius: var(--radius-md);
  padding: 16px 0;
  box-shadow: var(--shadow-sm);
}

.sidebar-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-muted);
  padding: 0 16px 10px;
  border-bottom: 1px solid var(--color-border);
  margin-bottom: 4px;
}

.cat-nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 4px 8px;
}

.cat-item {
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-secondary);
  text-align: left;
  transition: all 0.2s;
}

.cat-item:hover {
  color: var(--color-primary);
  background: var(--color-primary-light);
}

.cat-item.active {
  color: var(--color-primary);
  background: var(--color-primary-light);
  font-weight: 600;
}

/* Main content */
.main {
  flex: 1;
  min-width: 0;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 12px;
}

.page-title {
  font-size: 20px;
  font-weight: 700;
}

.type-tabs {
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

.mobile-cats {
  display: none;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.comic-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--color-text-muted);
}

.load-more {
  text-align: center;
  padding: 32px 0;
}

.load-more-btn {
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

@media (max-width: 768px) {
  .sidebar {
    display: none;
  }

  .mobile-cats {
    display: flex;
  }

  .comic-grid {
    grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
    gap: 10px;
  }
}
</style>
