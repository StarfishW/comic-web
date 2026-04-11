<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import IconSearch from './icons/IconSearch.vue'
import IconMenu from './icons/IconMenu.vue'
import IconX from './icons/IconX.vue'
import { queueItems, activeCount, groupedQueue, initQueue, refreshQueue, clearCompleted, isPolling } from '../utils/cacheQueue'
import { theme, toggleTheme } from '../utils/theme'

const router = useRouter()
const keyword = ref('')
const mobileMenuOpen = ref(false)
const showCachePanel = ref(false)
function toggleCachePanel() {
  showCachePanel.value = !showCachePanel.value
  if (showCachePanel.value) refreshQueue()
}

function handleSearch() {
  const q = keyword.value.trim()
  if (!q) return
  router.push({ name: 'Search', query: { q } })
  mobileMenuOpen.value = false
}

function toggleMenu() {
  mobileMenuOpen.value = !mobileMenuOpen.value
}

onMounted(() => { initQueue() })
</script>

<template>
  <header class="header">
    <div class="header-inner" @click="showCachePanel = false">
      <router-link to="/" class="logo" aria-label="Home">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
          <rect width="24" height="24" rx="6" fill="var(--color-primary)" />
          <path d="M7 4h2v16H7zM15 4h2v16h-2z" fill="#fff" opacity="0.9"/>
          <path d="M9 6h6v2H9zM9 16h6v2H9z" fill="#fff" opacity="0.6"/>
        </svg>
        <span class="logo-text">JMComic</span>
      </router-link>

      <nav class="nav-desktop">
        <router-link to="/" class="nav-link">首页</router-link>
        <router-link to="/ranking" class="nav-link">排行榜</router-link>
        <router-link to="/favorites" class="nav-link">收藏</router-link>
        <router-link to="/history" class="nav-link">历史</router-link>
        <router-link to="/cache" class="nav-link">缓存库</router-link>
        <router-link to="/settings" class="nav-link">设置</router-link>
      </nav>

      <!-- 缓存队列按钮 -->
      <div class="cache-btn-wrap" @click.stop>
        <button class="cache-btn" @click.stop="toggleCachePanel" :class="{ active: showCachePanel }" title="缓存队列">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          <span v-if="activeCount > 0" class="cache-badge">{{ activeCount }}</span>
        </button>

        <!-- 缓存面板 -->
        <transition name="panel-fade">
          <div v-if="showCachePanel" class="cache-panel" @click.stop>
            <div class="panel-header">
              <span class="panel-title">缓存队列</span>
              <div class="panel-actions">
                <span v-if="isPolling" class="polling-dot"></span>
                <button class="panel-clear" @click="clearCompleted">清除已完成</button>
              </div>
            </div>

            <div v-if="!queueItems.length" class="panel-empty">暂无缓存任务</div>

            <div v-else class="panel-list">
              <div v-for="group in groupedQueue" :key="group.albumId" class="group-item">
                <div class="group-title">{{ group.albumTitle }}</div>
                <div v-for="ch in group.chapters" :key="ch.photo_id" class="chapter-row">
                  <span class="ch-title">{{ ch.chapterTitle || ch.photo_id }}</span>
                  <div class="ch-right">
                    <div v-if="ch.status === 'downloading'" class="ch-bar-wrap">
                      <div class="ch-bar" :style="{ width: ch.progress + '%' }"></div>
                    </div>
                    <span :class="['ch-status', `ch-${ch.status}`]">
                      {{ ch.status === 'ready' ? '✓' : ch.status === 'error' ? '✕' : ch.status === 'downloading' ? ch.progress + '%' : '等待' }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
            <div class="panel-footer">
              <router-link to="/cache" class="panel-library-link" @click="showCachePanel = false">
                查看缓存库 →
              </router-link>
            </div>
          </div>
        </transition>
      </div>

      <form class="search-bar" @submit.prevent="handleSearch" role="search">
        <IconSearch class="search-icon" />
        <input
          v-model="keyword"
          type="search"
          placeholder="搜索漫画、作者、标签..."
          aria-label="搜索漫画"
          class="search-input"
        />
      </form>

      <router-link to="/login" class="login-link nav-link">登录</router-link>

      <!-- 主题切换 -->
      <button class="theme-btn" @click.stop="toggleTheme" :title="theme === 'dark' ? '切换为亮色' : '切换为暗色'">
        <svg v-if="theme === 'light'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
        </svg>
        <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="5"/>
          <line x1="12" y1="1" x2="12" y2="3"/>
          <line x1="12" y1="21" x2="12" y2="23"/>
          <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
          <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
          <line x1="1" y1="12" x2="3" y2="12"/>
          <line x1="21" y1="12" x2="23" y2="12"/>
          <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
          <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
        </svg>
      </button>

      <button
        class="menu-toggle"
        @click="toggleMenu"
        :aria-label="mobileMenuOpen ? '关闭菜单' : '打开菜单'"
      >
        <IconX v-if="mobileMenuOpen" />
        <IconMenu v-else />
      </button>
    </div>

    <transition name="slide">
      <div v-if="mobileMenuOpen" class="mobile-menu">
        <nav class="mobile-nav">
          <router-link to="/" class="mobile-link" @click="mobileMenuOpen = false">首页</router-link>
          <router-link to="/ranking" class="mobile-link" @click="mobileMenuOpen = false">排行榜</router-link>
          <router-link to="/favorites" class="mobile-link" @click="mobileMenuOpen = false">收藏</router-link>
          <router-link to="/history" class="mobile-link" @click="mobileMenuOpen = false">历史</router-link>
          <router-link to="/cache" class="mobile-link" @click="mobileMenuOpen = false">缓存库</router-link>
          <router-link to="/settings" class="mobile-link" @click="mobileMenuOpen = false">设置</router-link>
          <router-link to="/login" class="mobile-link" @click="mobileMenuOpen = false">登录</router-link>
        </nav>
        <form class="mobile-search" @submit.prevent="handleSearch" role="search">
          <IconSearch class="search-icon" />
          <input
            v-model="keyword"
            type="search"
            placeholder="搜索漫画..."
            aria-label="搜索漫画"
            class="search-input"
          />
        </form>
      </div>
    </transition>
  </header>
</template>

<style scoped>
.header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 50;
  background: var(--color-header-bg);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--color-border);
}

.header-inner {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 20px;
  height: 64px;
  display: flex;
  align-items: center;
  gap: 20px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  cursor: pointer;
}

.logo-text {
  font-weight: 700;
  font-size: 18px;
  color: var(--color-text);
}

.nav-desktop {
  display: flex;
  gap: 4px;
}

.nav-link {
  padding: 6px 14px;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-secondary);
  transition: color 0.2s, background 0.2s;
  cursor: pointer;
}

.nav-link:hover,
.nav-link.router-link-active {
  color: var(--color-primary);
  background: var(--color-primary-light);
}

.login-link {
  flex-shrink: 0;
}

.search-bar {
  flex: 1;
  max-width: 360px;
  margin-left: auto;
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 12px;
  width: 18px;
  height: 18px;
  color: var(--color-text-muted);
  pointer-events: none;
}

.search-input {
  width: 100%;
  padding: 8px 12px 8px 38px;
  border: 1px solid var(--color-border);
  border-radius: 20px;
  background: var(--color-bg);
  color: var(--color-text);
  font-size: 14px;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.search-input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.menu-toggle {
  display: none;
  width: 40px;
  height: 40px;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  color: var(--color-text);
  margin-left: auto;
}

.menu-toggle:hover {
  background: var(--color-primary-light);
}

.mobile-menu {
  padding: 12px 20px 20px;
  border-top: 1px solid var(--color-border);
  background: var(--color-surface);
}

.mobile-nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.mobile-link {
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  font-size: 15px;
  font-weight: 500;
  color: var(--color-text-secondary);
  cursor: pointer;
}

.mobile-link:hover,
.mobile-link.router-link-active {
  color: var(--color-primary);
  background: var(--color-primary-light);
}

.mobile-search {
  position: relative;
  display: flex;
  align-items: center;
  margin-top: 12px;
}

.mobile-search .search-input {
  width: 100%;
}

.slide-enter-active,
.slide-leave-active {
  transition: max-height 0.25s ease, opacity 0.2s ease;
  overflow: hidden;
}

.slide-enter-from,
.slide-leave-to {
  max-height: 0;
  opacity: 0;
}

.slide-enter-to {
  max-height: 300px;
  opacity: 1;
}

@media (max-width: 768px) {
  .nav-desktop,
  .search-bar,
  .login-link {
    display: none;
  }

  .menu-toggle {
    display: flex;
  }
}

/* 缓存队列按钮 */
.cache-btn-wrap {
  position: relative;
  flex-shrink: 0;
}

.cache-btn {
  position: relative;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  transition: all 0.2s;
}

.cache-btn:hover,
.cache-btn.active {
  color: var(--color-primary);
  background: var(--color-primary-light);
}

.cache-badge {
  position: absolute;
  top: 2px;
  right: 2px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  background: var(--color-primary);
  color: #fff;
  border-radius: 8px;
  font-size: 10px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

/* 缓存面板 */
.cache-panel {
  position: fixed;
  top: 68px;
  right: 16px;
  width: 320px;
  max-height: 480px;
  display: flex;
  flex-direction: column;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  z-index: 200;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
}

.panel-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.polling-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-primary);
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.panel-clear {
  font-size: 12px;
  color: var(--color-text-muted);
  cursor: pointer;
  transition: color 0.2s;
}

.panel-clear:hover { color: var(--color-primary); }

.panel-empty {
  padding: 32px 16px;
  text-align: center;
  color: var(--color-text-muted);
  font-size: 13px;
}

.panel-list {
  overflow-y: auto;
  flex: 1;
}

.group-item {
  border-bottom: 1px solid var(--color-border);
  padding: 10px 16px;
}

.group-item:last-child { border-bottom: none; }

.group-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-muted);
  margin-bottom: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chapter-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 4px 0;
}

.ch-title {
  font-size: 13px;
  color: var(--color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.ch-right {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.ch-bar-wrap {
  width: 60px;
  height: 4px;
  background: var(--color-border);
  border-radius: 2px;
  overflow: hidden;
}

.ch-bar {
  height: 100%;
  background: var(--color-primary);
  border-radius: 2px;
  transition: width 0.3s ease;
}

.ch-status {
  font-size: 12px;
  font-weight: 600;
  min-width: 28px;
  text-align: right;
}

.ch-ready { color: #16a34a; }
.ch-error { color: #dc2626; }
.ch-downloading { color: var(--color-primary); }
.ch-pending { color: var(--color-text-muted); }

/* 面板动画 */
.panel-fade-enter-active,
.panel-fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.panel-fade-enter-from,
.panel-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

@media (max-width: 768px) {
  .cache-btn-wrap { display: none; }
  /* .theme-btn 保持可见，不需要 display: none */
}

.theme-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  flex-shrink: 0;
  transition: color 0.2s, background 0.2s;
}

.theme-btn:hover {
  color: var(--color-primary);
  background: var(--color-primary-light);
}

.panel-footer {
  border-top: 1px solid var(--color-border);
  padding: 10px 16px;
  flex-shrink: 0;
}
.panel-library-link {
  font-size: 13px;
  color: var(--color-primary);
  font-weight: 500;
}
.panel-library-link:hover { text-decoration: underline; }
</style>
