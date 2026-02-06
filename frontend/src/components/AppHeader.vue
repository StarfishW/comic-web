<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import IconSearch from './icons/IconSearch.vue'
import IconMenu from './icons/IconMenu.vue'
import IconX from './icons/IconX.vue'

const router = useRouter()
const keyword = ref('')
const mobileMenuOpen = ref(false)

function handleSearch() {
  const q = keyword.value.trim()
  if (!q) return
  router.push({ name: 'Search', query: { q } })
  mobileMenuOpen.value = false
}

function toggleMenu() {
  mobileMenuOpen.value = !mobileMenuOpen.value
}
</script>

<template>
  <header class="header">
    <div class="header-inner">
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
      </nav>

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
  background: rgba(255, 255, 255, 0.85);
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
</style>
