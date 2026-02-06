<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { pingDomains, switchDomain } from '../api'

const router = useRouter()
const loading = ref(false)
const switching = ref('')
const results = ref([])
const currentDomains = ref([])
const error = ref('')

const activeDomain = computed(() => currentDomains.value[0] || '')

async function fetchPing() {
  try {
    loading.value = true
    error.value = ''
    const data = await pingDomains()
    results.value = data.results || []
    currentDomains.value = data.current || []
  } catch (e) {
    error.value = '获取域名延迟失败: ' + (e.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

async function handleSwitch(domain) {
  if (switching.value || domain === activeDomain.value) return
  try {
    switching.value = domain
    const data = await switchDomain(domain)
    currentDomains.value = data.domains || []
  } catch (e) {
    error.value = '切换失败: ' + (e.response?.data?.detail || e.message)
  } finally {
    switching.value = ''
  }
}

function handleLogout() {
  localStorage.removeItem('auth_token')
  localStorage.removeItem('is_authenticated')
  router.push('/login')
}

function latencyColor(latency) {
  if (latency < 0) return 'latency-error'
  if (latency < 300) return 'latency-fast'
  if (latency < 800) return 'latency-medium'
  return 'latency-slow'
}

function latencyLabel(latency) {
  if (latency < 0) return '超时'
  return latency + 'ms'
}

onMounted(fetchPing)
</script>

<template>
  <div class="settings-view">
    <div class="container">
      <div class="section">
        <div class="section-header">
          <h1 class="page-title">域名管理</h1>
          <button class="refresh-btn" :disabled="loading" @click="fetchPing">
            <svg :class="['refresh-icon', { spinning: loading }]" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 2v6h-6" /><path d="M3 12a9 9 0 0 1 15-6.7L21 8" />
              <path d="M3 22v-6h6" /><path d="M21 12a9 9 0 0 1-15 6.7L3 16" />
            </svg>
            {{ loading ? '检测中...' : '刷新延迟' }}
          </button>
        </div>
        <p class="section-desc">检测所有可用域名的延迟，选择最快的域名进行连接。</p>

        <div v-if="error" class="error-msg">{{ error }}</div>

        <!-- Loading skeleton -->
        <div v-if="loading && !results.length" class="domain-list">
          <div v-for="i in 4" :key="i" class="domain-card skeleton">
            <div class="skeleton-bar" style="width:60%"></div>
            <div class="skeleton-bar short"></div>
          </div>
        </div>

        <!-- Domain list -->
        <div v-else-if="results.length" class="domain-list">
          <div
            v-for="item in results"
            :key="item.domain"
            :class="['domain-card', { active: item.domain === activeDomain }]"
          >
            <div class="domain-info">
              <div class="domain-name">
                {{ item.domain }}
                <span v-if="item.domain === activeDomain" class="badge-current">当前</span>
              </div>
              <div :class="['domain-latency', latencyColor(item.latency)]">
                <span class="dot"></span>
                {{ latencyLabel(item.latency) }}
              </div>
            </div>
            <div class="domain-bar-wrap">
              <div
                v-if="item.latency > 0"
                :class="['domain-bar', latencyColor(item.latency)]"
                :style="{ width: Math.min(item.latency / 20, 100) + '%' }"
              ></div>
            </div>
            <button
              v-if="item.domain !== activeDomain && item.latency > 0"
              class="switch-btn"
              :disabled="switching === item.domain"
              @click="handleSwitch(item.domain)"
            >
              {{ switching === item.domain ? '切换中...' : '切换' }}
            </button>
            <span v-else-if="item.domain === activeDomain" class="switch-active">使用中</span>
            <span v-else class="switch-disabled">不可用</span>
          </div>
        </div>

        <div v-else class="empty-state">
          <p>暂无域名数据，点击刷新延迟进行检测</p>
        </div>
      </div>

      <!-- Logout Section -->
      <div class="section logout-section">
        <h2 class="section-title">账户</h2>
        <p class="section-desc">退出登录后需要重新输入密码才能访问网站。</p>
        <button class="logout-btn" @click="handleLogout">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
            <polyline points="16 17 21 12 16 7" />
            <line x1="21" y1="12" x2="9" y2="12" />
          </svg>
          退出登录
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.settings-view {
  padding: 20px 0 40px;
}

.container {
  max-width: 720px;
  margin: 0 auto;
  padding: 0 20px;
}

.section {
  background: var(--color-surface);
  border-radius: var(--radius-md);
  padding: 24px;
  box-shadow: var(--shadow-sm);
  margin-bottom: 20px;
}

.logout-section {
  margin-top: 20px;
}

.section-title {
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 8px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.page-title {
  font-size: 20px;
  font-weight: 700;
}

.section-desc {
  font-size: 14px;
  color: var(--color-text-muted);
  margin: 8px 0 20px;
}

.refresh-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
  background: var(--color-bg);
  transition: all 0.2s;
}

.refresh-btn:hover:not(:disabled) {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.refresh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.refresh-icon {
  flex-shrink: 0;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-msg {
  background: #fef2f2;
  color: #dc2626;
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  margin-bottom: 16px;
}

.domain-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.domain-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  transition: all 0.2s;
}

.domain-card.active {
  border-color: var(--color-primary);
  background: rgba(59, 130, 246, 0.04);
}

.domain-card.skeleton {
  padding: 20px 16px;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
}

.skeleton-bar {
  height: 14px;
  background: var(--color-border);
  border-radius: 4px;
  width: 60%;
  animation: shimmer 1.5s infinite;
  background: linear-gradient(90deg, var(--color-border) 25%, #f1f5f9 50%, var(--color-border) 75%);
  background-size: 200% 100%;
}

.skeleton-bar.short {
  width: 30%;
  height: 12px;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.domain-info {
  flex: 1;
  min-width: 0;
}

.domain-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
  display: flex;
  align-items: center;
  gap: 8px;
  word-break: break-all;
}

.badge-current {
  font-size: 11px;
  font-weight: 600;
  background: var(--color-primary);
  color: #fff;
  padding: 1px 6px;
  border-radius: 8px;
  flex-shrink: 0;
}

.domain-latency {
  font-size: 13px;
  font-weight: 500;
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.latency-fast { color: #16a34a; }
.latency-fast .dot { background: #16a34a; }

.latency-medium { color: #d97706; }
.latency-medium .dot { background: #d97706; }

.latency-slow { color: #ea580c; }
.latency-slow .dot { background: #ea580c; }

.latency-error { color: #dc2626; }
.latency-error .dot { background: #dc2626; }

.domain-bar-wrap {
  width: 80px;
  height: 6px;
  background: var(--color-border);
  border-radius: 3px;
  overflow: hidden;
  flex-shrink: 0;
}

.domain-bar {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s ease;
}

.domain-bar.latency-fast { background: #16a34a; }
.domain-bar.latency-medium { background: #d97706; }
.domain-bar.latency-slow { background: #ea580c; }

.switch-btn {
  padding: 5px 14px;
  border: 1px solid var(--color-border);
  border-radius: 16px;
  font-size: 12px;
  font-weight: 500;
  color: var(--color-text-secondary);
  background: var(--color-bg);
  transition: all 0.2s;
  flex-shrink: 0;
}

.switch-btn:hover:not(:disabled) {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.switch-btn:disabled {
  opacity: 0.6;
}

.switch-active {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-primary);
  flex-shrink: 0;
}

.switch-disabled {
  font-size: 12px;
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: var(--color-text-muted);
  font-size: 14px;
}

.logout-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  border: 1px solid #dc2626;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 500;
  color: #dc2626;
  background: transparent;
  transition: all 0.2s;
}

.logout-btn:hover {
  background: #dc2626;
  color: #fff;
}

.logout-btn svg {
  flex-shrink: 0;
}

@media (max-width: 640px) {
  .section {
    padding: 16px;
  }

  .domain-card {
    flex-wrap: wrap;
    gap: 8px;
  }

  .domain-bar-wrap {
    width: 100%;
    order: 3;
  }

  .switch-btn,
  .switch-active,
  .switch-disabled {
    margin-left: auto;
  }
}
</style>
