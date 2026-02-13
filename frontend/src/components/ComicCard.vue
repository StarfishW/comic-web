<script setup>
import { getCoverUrl } from '../api'
import LazyImage from './LazyImage.vue'

const props = defineProps({
  comic: { type: Object, required: true },
})
</script>

<template>
  <router-link :to="`/comic/${comic.id}`" class="comic-card" :aria-label="comic.title">
    <div class="cover-wrap">
      <LazyImage
        :src="getCoverUrl(comic.id)"
        :alt="comic.title"
        class="cover"
      />
    </div>
    <div class="info">
      <h3 class="title">{{ comic.title }}</h3>
      <p v-if="comic.author" class="author">{{ comic.author }}</p>
      <div v-if="comic.tags && comic.tags.length" class="tags">
        <span v-for="tag in comic.tags.slice(0, 3)" :key="tag" class="tag">{{ tag }}</span>
      </div>
    </div>
  </router-link>
</template>

<style scoped>
.comic-card {
  display: block;
  background: var(--color-surface);
  border-radius: var(--radius-md);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  transition: transform 0.2s, box-shadow 0.2s;
  cursor: pointer;
}

.comic-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-md);
}

.cover-wrap {
  position: relative;
  aspect-ratio: 3 / 4;
  overflow: hidden;
  background: var(--color-border);
}

.cover :deep(.lazy-image-wrapper) {
  width: 100%;
  height: 100%;
}

.cover :deep(.lazy-image) {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s;
}

.comic-card:hover .cover :deep(.lazy-image) {
  transform: scale(1.03);
}

.info {
  padding: 10px 12px 12px;
}

.title {
  font-size: 13px;
  font-weight: 600;
  line-height: 1.4;
  color: var(--color-text);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.author {
  font-size: 12px;
  color: var(--color-text-muted);
  margin-top: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  margin-top: 6px;
}

.tag {
  font-size: 11px;
  padding: 1px 6px;
  background: var(--color-primary-light);
  color: var(--color-primary);
  border-radius: 4px;
  white-space: nowrap;
}
</style>
