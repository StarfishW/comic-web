<script setup>
defineOptions({ name: 'FavoritesView' })

import { computed, onMounted, ref } from 'vue'
import * as api from '../api'
import ComicCard from '../components/ComicCard.vue'
import SkeletonGrid from '../components/SkeletonGrid.vue'
import { usePagedList } from '../composables/usePagedList'

const CONCURRENCY = 4

const loadedCount = ref(0)
const loadableCount = computed(() => loadedCount.value + CONCURRENCY)

function onImageReady() {
  loadedCount.value += 1
}

function normalizeComic(item) {
  const authors = Array.isArray(item?.authors) ? item.authors.filter(Boolean).join(', ') : ''
  const id = item?.id ?? item?.album_id ?? item?.albumId

  return {
    ...item,
    id: id === undefined || id === null ? '' : String(id),
    title: item?.title || item?.album_title || item?.name || 'Untitled',
    author: item?.author || authors || item?.artist || '',
    tags: Array.isArray(item?.tags) ? item.tags : [],
  }
}

function resolveItems(data) {
  if (Array.isArray(data)) return data

  return [
    data?.items,
    data?.records,
    data?.list,
    data?.favorites,
    data?.results,
  ].find(Array.isArray) || []
}

function resolvePageCount(data) {
  if (Array.isArray(data)) return 1
  return Number(data?.page_count || data?.pages || data?.last_page || 1)
}

function resolveTotal(data) {
  if (Array.isArray(data)) return data.length
  return Number(data?.total || data?.count || resolveItems(data).length || 0)
}

const {
  items: comics,
  loading,
  error,
  total,
  hasMore,
  loadingMore,
  refresh,
  loadMore,
} = usePagedList({
  fetchPage: ({ page }) => api.getFavorites({ page }),
  getItems: (data) => resolveItems(data).map(normalizeComic).filter((item) => item.id),
  getPageCount: resolvePageCount,
  getTotal: resolveTotal,
  getErrorMessage: () => '请先登录后再查看收藏',
})

async function fetchFavorites() {
  loadedCount.value = 0
  await refresh()
}

onMounted(fetchFavorites)
</script>

<template>
  <div class="favorites-view">
    <div class="container">
      <div class="page-head">
        <div>
          <h1 class="page-title">我的收藏</h1>
          <p class="page-subtitle">
            {{ total ? `共 ${total} 部漫画` : '已接入站内收藏列表' }}
          </p>
        </div>
      </div>

      <SkeletonGrid v-if="loading" :count="8" />

      <div v-else-if="error" class="error-state">
        <p>{{ error }}</p>
        <router-link to="/login" class="btn-primary">去登录</router-link>
      </div>

      <div v-else-if="!comics.length" class="empty-state">
        <p>还没有收藏的漫画</p>
        <router-link to="/" class="link-home">去首页看看</router-link>
      </div>

      <div v-else class="comic-grid">
        <ComicCard
          v-for="(comic, index) in comics"
          :key="comic.id"
          :comic="comic"
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
.favorites-view {
  padding: 20px 0 40px;
}

.container {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 20px;
}

.page-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 20px;
}

.page-title {
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 6px;
}

.page-subtitle {
  font-size: 13px;
  color: var(--color-text-muted);
}

.comic-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px;
}

.error-state,
.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--color-text-muted);
}

.btn-primary {
  display: inline-block;
  margin-top: 16px;
  padding: 10px 28px;
  background: var(--color-primary);
  color: #fff;
  border-radius: var(--radius-sm);
  font-weight: 500;
}

.link-home {
  display: inline-block;
  margin-top: 12px;
  color: var(--color-primary);
  font-weight: 500;
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

  .page-head {
    align-items: flex-start;
  }
}
</style>
