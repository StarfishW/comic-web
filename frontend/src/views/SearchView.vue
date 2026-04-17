<script setup>
defineOptions({ name: 'SearchView' })
import { ref, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { searchComics } from '../api'
import ComicCard from '../components/ComicCard.vue'
import SkeletonGrid from '../components/SkeletonGrid.vue'
import { usePagedList } from '../composables/usePagedList'

const route = useRoute()
const keyword = ref('')

const CONCURRENCY = 4
const loadedCount = ref(0)
const loadableCount = computed(() => loadedCount.value + CONCURRENCY)

function onImageReady() {
  loadedCount.value++
}

const mainTag = ref(0)
const searchTypes = [
  { value: 0, label: '综合' },
  { value: 1, label: '作品' },
  { value: 2, label: '作者' },
  { value: 3, label: '标签' },
  { value: 4, label: '角色' },
]

const {
  items: comics,
  loading,
  error,
  total,
  hasMore,
  loadingMore,
  refresh,
  loadMore,
  reset,
} = usePagedList({
  fetchPage: ({ page }) => searchComics(keyword.value, {
    page,
    main_tag: mainTag.value,
  }),
  getErrorMessage: () => '搜索失败，请稍后重试',
  initialLoading: false,
})

async function doSearch(q, tag = null) {
  if (!q) {
    keyword.value = ''
    loadedCount.value = 0
    reset()
    return
  }

  keyword.value = q
  if (tag !== null) {
    mainTag.value = tag
  }

  loadedCount.value = 0
  await refresh()
}

watch(
  () => route.query,
  (query) => {
    if (query.q) {
      doSearch(query.q, query.main_tag !== undefined ? Number(query.main_tag) : null)
      return
    }

    keyword.value = ''
    reset()
  },
  { immediate: true },
)
</script>

<template>
  <div class="search-view">
    <div class="container">
      <h1 class="page-title" v-if="keyword">
        搜索 "<span class="keyword">{{ keyword }}</span>"
        <span v-if="total" class="total-count">共 {{ total }} 条结果</span>
      </h1>

      <div class="type-tabs" v-if="keyword">
        <button
          v-for="t in searchTypes"
          :key="t.value"
          :class="['tab', { active: mainTag === t.value }]"
          @click="doSearch(keyword, t.value)"
        >{{ t.label }}</button>
      </div>

      <SkeletonGrid v-if="loading" :count="12" />

      <div v-else-if="error" class="empty-state">
        <p>{{ error }}</p>
        <button class="load-more-btn" @click="doSearch(keyword, mainTag)">重试</button>
      </div>

      <div v-else-if="keyword && !comics.length" class="empty-state">
        <p>没有找到 "{{ keyword }}" 的相关结果</p>
        <p class="empty-hint">试试其他关键词或切换搜索类型</p>
      </div>

      <div v-else-if="!keyword" class="empty-state">
        <p>输入关键词搜索漫画</p>
      </div>

      <div v-else class="comic-grid">
        <ComicCard
          v-for="(c, index) in comics"
          :key="c.id"
          :comic="c"
          :shouldLoad="index < loadableCount"
          @imageReady="onImageReady"
        />
      </div>

      <div v-if="!loading && hasMore" class="load-more">
        <button class="load-more-btn" :disabled="loadingMore" @click="loadMore()">
          {{ loadingMore ? '加载中...' : '加载更多' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.search-view {
  padding: 20px 0 40px;
}

.container {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 20px;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 16px;
  color: var(--color-text-secondary);
}

.keyword {
  color: var(--color-text);
  font-weight: 700;
}

.total-count {
  font-size: 13px;
  color: var(--color-text-muted);
  font-weight: 400;
  margin-left: 8px;
}

.type-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 20px;
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

.empty-state {
  text-align: center;
  padding: 80px 20px;
  color: var(--color-text-muted);
}

.empty-hint {
  font-size: 14px;
  margin-top: 8px;
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

@media (max-width: 640px) {
  .comic-grid {
    grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
    gap: 10px;
  }
}
</style>
