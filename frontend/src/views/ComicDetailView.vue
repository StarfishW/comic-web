<script setup>
import { ref, onMounted, watch } from 'vue'
import { getCoverUrl, getComicDetail, addFavorite } from '../api'

const props = defineProps({ id: { type: String, required: true } })

const comic = ref(null)
const loading = ref(true)
const error = ref(null)
const favoriteLoading = ref(false)

async function fetchComic() {
  try {
    loading.value = true
    error.value = null
    comic.value = await getComicDetail(props.id)
  } catch (e) {
    error.value = '加载失败: ' + (e.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

async function handleFavorite() {
  if (favoriteLoading.value) return
  try {
    favoriteLoading.value = true
    await addFavorite(props.id)
    alert('收藏成功')
  } catch {
    alert('收藏失败，请先登录')
  } finally {
    favoriteLoading.value = false
  }
}

watch(() => props.id, fetchComic)
onMounted(fetchComic)
</script>

<template>
  <div class="detail-view">
    <div class="container">
      <!-- Loading skeleton -->
      <div v-if="loading" class="skeleton-detail">
        <div class="skeleton-cover shimmer"></div>
        <div class="skeleton-info">
          <div class="sk-line sk-title shimmer"></div>
          <div class="sk-line sk-meta shimmer"></div>
          <div class="sk-line sk-desc shimmer"></div>
        </div>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="error-state">
        <p>{{ error }}</p>
        <button class="retry-btn" @click="fetchComic">重试</button>
      </div>

      <!-- Content -->
      <template v-else-if="comic">
        <div class="detail-header">
          <div class="cover-box">
            <img :src="getCoverUrl(comic.id)" :alt="comic.title" class="cover-img" />
          </div>
          <div class="meta-box">
            <h1 class="comic-title">{{ comic.title }}</h1>
            <div class="meta-row">
              <span class="meta-label">作者</span>
              <router-link
                v-for="a in (comic.authors || [comic.author])"
                :key="a"
                :to="{ name: 'Search', query: { q: a, main_tag: 2 } }"
                class="meta-link"
              >{{ a }}</router-link>
            </div>
            <div v-if="comic.tags && comic.tags.length" class="meta-row">
              <span class="meta-label">标签</span>
              <div class="tag-list">
                <router-link
                  v-for="t in comic.tags"
                  :key="t"
                  :to="{ name: 'Search', query: { q: t, main_tag: 3 } }"
                  class="tag"
                >{{ t }}</router-link>
              </div>
            </div>
            <div class="stats">
              <span v-if="comic.views">浏览 {{ comic.views }}</span>
              <span v-if="comic.likes">喜欢 {{ comic.likes }}</span>
              <span v-if="comic.page_count">{{ comic.page_count }} 页</span>
            </div>
            <p v-if="comic.description" class="description">{{ comic.description }}</p>
            <div class="actions">
              <router-link
                v-if="comic.episodes && comic.episodes.length"
                :to="{ name: 'Reader', params: { photoId: comic.episodes[0].id } }"
                class="btn-primary"
              >开始阅读</router-link>
              <button class="btn-outline" :disabled="favoriteLoading" @click="handleFavorite">
                {{ favoriteLoading ? '...' : '收藏' }}
              </button>
            </div>
          </div>
        </div>

        <!-- Chapter List -->
        <section v-if="comic.episodes && comic.episodes.length" class="chapter-section">
          <h2 class="section-title">章节列表 ({{ comic.episodes.length }})</h2>
          <div class="chapter-grid">
            <router-link
              v-for="ep in comic.episodes"
              :key="ep.id"
              :to="{ name: 'Reader', params: { photoId: ep.id } }"
              class="chapter-item"
            >
              <span class="ep-sort">{{ ep.sort }}</span>
              <span class="ep-title">{{ ep.title || `第${ep.sort}话` }}</span>
            </router-link>
          </div>
        </section>
      </template>
    </div>
  </div>
</template>

<style scoped>
.detail-view {
  padding: 20px 0 40px;
}

.container {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 20px;
}

.detail-header {
  display: flex;
  gap: 28px;
  align-items: flex-start;
}

.cover-box {
  flex-shrink: 0;
  width: 220px;
  border-radius: var(--radius-md);
  overflow: hidden;
  box-shadow: var(--shadow-md);
}

.cover-img {
  width: 100%;
  aspect-ratio: 3 / 4;
  object-fit: cover;
}

.meta-box {
  flex: 1;
  min-width: 0;
}

.comic-title {
  font-size: 22px;
  font-weight: 700;
  line-height: 1.3;
  color: var(--color-text);
  margin-bottom: 14px;
}

.meta-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.meta-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-muted);
  flex-shrink: 0;
  min-width: 36px;
  padding-top: 2px;
}

.meta-link {
  font-size: 14px;
  color: var(--color-primary);
  cursor: pointer;
}

.meta-link:hover {
  text-decoration: underline;
}

.tag-list {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.tag {
  font-size: 12px;
  padding: 2px 10px;
  background: var(--color-primary-light);
  color: var(--color-primary);
  border-radius: 12px;
  cursor: pointer;
  transition: background 0.2s;
}

.tag:hover {
  background: var(--color-primary);
  color: #fff;
}

.stats {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: var(--color-text-muted);
  margin: 12px 0;
}

.description {
  font-size: 14px;
  line-height: 1.7;
  color: var(--color-text-secondary);
  margin: 12px 0 16px;
}

.actions {
  display: flex;
  gap: 10px;
  margin-top: 16px;
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  padding: 10px 28px;
  background: var(--color-primary);
  color: #fff;
  border-radius: var(--radius-sm);
  font-weight: 600;
  font-size: 14px;
  transition: background 0.2s;
  cursor: pointer;
}

.btn-primary:hover {
  background: var(--color-primary-hover);
}

.btn-outline {
  padding: 10px 24px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-weight: 500;
  font-size: 14px;
  color: var(--color-text-secondary);
  transition: all 0.2s;
}

.btn-outline:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

/* Chapter section */
.chapter-section {
  margin-top: 36px;
}

.section-title {
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 16px;
  color: var(--color-text);
}

.chapter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 8px;
}

.chapter-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 13px;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.2s;
  overflow: hidden;
}

.chapter-item:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: var(--color-primary-light);
}

.ep-sort {
  font-weight: 600;
  color: var(--color-primary);
  flex-shrink: 0;
}

.ep-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Skeleton */
.skeleton-detail {
  display: flex;
  gap: 28px;
}

.skeleton-cover {
  width: 220px;
  aspect-ratio: 3 / 4;
  border-radius: var(--radius-md);
  background: var(--color-border);
  flex-shrink: 0;
}

.skeleton-info {
  flex: 1;
  padding-top: 8px;
}

.sk-line {
  background: var(--color-border);
  border-radius: 4px;
}

.sk-title {
  height: 24px;
  width: 60%;
}

.sk-meta {
  height: 16px;
  width: 40%;
  margin-top: 14px;
}

.sk-desc {
  height: 60px;
  width: 90%;
  margin-top: 14px;
}

.shimmer {
  background: linear-gradient(90deg, var(--color-border) 25%, #f1f5f9 50%, var(--color-border) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
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
  cursor: pointer;
}

@media (max-width: 640px) {
  .detail-header {
    flex-direction: column;
    align-items: center;
    text-align: center;
  }

  .cover-box {
    width: 180px;
  }

  .meta-row {
    justify-content: center;
  }

  .actions {
    justify-content: center;
  }

  .comic-title {
    font-size: 19px;
  }

  .chapter-grid {
    grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  }
}
</style>
