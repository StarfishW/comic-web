<script setup>
import { ref, onMounted } from 'vue'
import { getFavorites } from '../api'
import ComicCard from '../components/ComicCard.vue'
import SkeletonGrid from '../components/SkeletonGrid.vue'

const comics = ref([])
const folders = ref([])
const loading = ref(true)
const error = ref(null)
const page = ref(1)
const hasMore = ref(false)
const loadingMore = ref(false)
const currentFolder = ref('0')
const pageCount = ref(0)

async function fetchFavorites() {
  try {
    loading.value = true
    error.value = null
    page.value = 1
    const data = await getFavorites({ page: 1, folder_id: currentFolder.value })
    comics.value = data.items || []
    folders.value = data.folders || []
    pageCount.value = data.page_count || 0
    hasMore.value = page.value < pageCount.value
  } catch (e) {
    error.value = '请先登录后再查看收藏'
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
    const data = await getFavorites({ page: page.value, folder_id: currentFolder.value })
    comics.value.push(...(data.items || []))
    hasMore.value = page.value < (data.page_count || 0)
  } catch {
    page.value--
  } finally {
    loadingMore.value = false
  }
}

function changeFolder(fid) {
  currentFolder.value = fid
  fetchFavorites()
}

onMounted(fetchFavorites)
</script>

<template>
  <div class="favorites-view">
    <div class="container">
      <h1 class="page-title">我的收藏</h1>

      <!-- Folder tabs -->
      <div class="folder-tabs" v-if="folders.length">
        <button
          :class="['tab', { active: currentFolder === '0' }]"
          @click="changeFolder('0')"
        >全部</button>
        <button
          v-for="f in folders"
          :key="f.id"
          :class="['tab', { active: currentFolder === f.id }]"
          @click="changeFolder(f.id)"
        >{{ f.name }}</button>
      </div>

      <SkeletonGrid v-if="loading" :count="8" />

      <div v-else-if="error" class="error-state">
        <p>{{ error }}</p>
        <router-link to="/login" class="btn-primary">去登录</router-link>
      </div>

      <div v-else-if="!comics.length" class="empty-state">
        <p>收藏夹为空</p>
        <router-link to="/" class="link-home">去首页看看</router-link>
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
</template>

<style scoped>
.favorites-view { padding: 20px 0 40px; }

.container {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 20px;
}

.page-title {
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 16px;
}

.folder-tabs {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
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
}
</style>
