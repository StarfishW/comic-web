<script setup>
import { ref, onMounted } from 'vue'
import ComicCard from '../components/ComicCard.vue'
import { getHistory, clearHistory, removeHistory } from '../utils/history'

const records = ref([])
const confirmState = ref(null) // { mode: 'clear' | 'remove', id?: string }

function load() {
  records.value = getHistory().map(h => ({
    id: h.id,
    title: h.title,
    author: h.author,
    tags: [],
    visitedAt: h.visitedAt,
  }))
}

function handleClear() {
  confirmState.value = { mode: 'clear' }
}

function handleRemove(id) {
  confirmState.value = { mode: 'remove', id }
}

function doConfirm() {
  const state = confirmState.value
  confirmState.value = null
  if (state?.mode === 'clear') {
    clearHistory()
    records.value = []
  } else if (state?.mode === 'remove') {
    removeHistory(state.id)
    records.value = records.value.filter(r => r.id !== state.id)
  }
}

function formatTime(ts) {
  const now = Date.now()
  const diff = now - ts
  const day = 86400000
  if (diff < day) {
    const d = new Date(ts)
    return `今天 ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  }
  if (diff < day * 2) return '昨天'
  return `${Math.floor(diff / day)} 天前`
}

onMounted(load)
</script>

<template>
  <div class="history-view">
    <div class="container">
      <div class="toolbar">
        <h2 class="section-title">观看历史</h2>
        <button v-if="records.length" class="clear-btn" @click="handleClear">清空</button>
      </div>

      <div v-if="records.length" class="comic-grid">
        <div v-for="r in records" :key="r.id" class="card-wrap">
          <ComicCard :comic="r" />
          <div class="card-meta">
            <span class="visit-time">{{ formatTime(r.visitedAt) }}</span>
            <button class="remove-btn" @click="handleRemove(r.id)" title="移除">×</button>
          </div>
        </div>
      </div>

      <div v-else class="empty-state">
        <p>暂无观看记录</p>
      </div>
    </div>

    <!-- 确认弹窗 -->
    <transition name="modal-fade">
      <div v-if="confirmState" class="modal-mask" @click.self="confirmState = null">
        <div class="modal-box">
          <div class="modal-icon">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#dc2626" stroke-width="1.5">
              <polyline points="3 6 5 6 21 6"/>
              <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
              <path d="M10 11v6M14 11v6"/>
              <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>
            </svg>
          </div>
          <template v-if="confirmState.mode === 'clear'">
            <h3 class="modal-title">清空观看历史</h3>
            <p class="modal-desc">将删除全部 {{ records.length }} 条历史记录，此操作不可撤销。</p>
          </template>
          <template v-else>
            <h3 class="modal-title">移除记录</h3>
            <p class="modal-desc">确定从历史中移除「{{ records.find(r => r.id === confirmState?.id)?.title || confirmState?.id }}」？</p>
          </template>
          <div class="modal-actions">
            <button class="modal-cancel" @click="confirmState = null">取消</button>
            <button class="modal-confirm" @click="doConfirm">
              {{ confirmState.mode === 'clear' ? '清空' : '移除' }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.history-view {
  padding: 20px 0 40px;
}

.container {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 20px;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.section-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--color-text);
}

.clear-btn {
  padding: 5px 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 13px;
  color: var(--color-text-secondary);
  transition: all 0.2s;
}

.clear-btn:hover {
  border-color: #dc2626;
  color: #dc2626;
}

.comic-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px;
}

.card-wrap {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.card-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 2px;
}

.visit-time {
  font-size: 11px;
  color: var(--color-text-muted);
}

.remove-btn {
  font-size: 16px;
  line-height: 1;
  color: var(--color-text-muted);
  padding: 0 4px;
  transition: color 0.2s;
}

.remove-btn:hover {
  color: #dc2626;
}

.empty-state {
  text-align: center;
  padding: 80px 20px;
  color: var(--color-text-muted);
  font-size: 15px;
}

@media (max-width: 640px) {
  .comic-grid {
    grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
    gap: 10px;
  }
}

/* 确认弹窗 */
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 500;
  padding: 20px;
}

.modal-box {
  background: var(--color-surface);
  border-radius: var(--radius-md);
  padding: 32px 28px 24px;
  width: 100%;
  max-width: 360px;
  text-align: center;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}

.modal-icon {
  display: flex;
  justify-content: center;
  margin-bottom: 16px;
}

.modal-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 8px;
}

.modal-desc {
  font-size: 14px;
  color: var(--color-text-muted);
  line-height: 1.6;
  margin-bottom: 24px;
}

.modal-actions {
  display: flex;
  gap: 10px;
}

.modal-cancel {
  flex: 1;
  padding: 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-secondary);
  background: var(--color-bg);
  cursor: pointer;
  transition: all 0.2s;
}
.modal-cancel:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.modal-confirm {
  flex: 1;
  padding: 10px;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  background: #dc2626;
  cursor: pointer;
  transition: background 0.2s;
}
.modal-confirm:hover { background: #b91c1c; }

.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.2s ease;
}
.modal-fade-enter-active .modal-box,
.modal-fade-leave-active .modal-box {
  transition: transform 0.2s ease, opacity 0.2s ease;
}
.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}
.modal-fade-enter-from .modal-box,
.modal-fade-leave-to .modal-box {
  transform: scale(0.95);
  opacity: 0;
}
</style>
