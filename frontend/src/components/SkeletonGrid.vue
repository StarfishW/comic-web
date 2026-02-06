<script setup>
defineProps({
  count: { type: Number, default: 8 },
})
</script>

<template>
  <div class="skeleton-grid">
    <div v-for="i in count" :key="i" class="skeleton-card">
      <div class="skeleton-thumb shimmer"></div>
      <div class="skeleton-info">
        <div class="skeleton-line skeleton-title shimmer"></div>
        <div class="skeleton-line skeleton-meta shimmer"></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.skeleton-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px;
}

.skeleton-card {
  background: var(--color-surface);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.skeleton-thumb {
  aspect-ratio: 3 / 4;
  background: var(--color-border);
}

.skeleton-info {
  padding: 12px 14px 14px;
}

.skeleton-line {
  border-radius: 4px;
  background: var(--color-border);
}

.skeleton-title {
  height: 16px;
  width: 80%;
}

.skeleton-meta {
  height: 13px;
  width: 50%;
  margin-top: 8px;
}

.shimmer {
  background: linear-gradient(
    90deg,
    var(--color-border) 25%,
    #f1f5f9 50%,
    var(--color-border) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

@media (max-width: 640px) {
  .skeleton-grid {
    grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
    gap: 10px;
  }
}
</style>
