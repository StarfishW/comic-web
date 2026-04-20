<script setup>
import { computed, onMounted, ref } from 'vue'
import { createAdminUser, getAdminUsers } from '../api'
import { authState } from '../utils/auth'

const loading = ref(false)
const submitting = ref(false)
const error = ref('')
const success = ref('')
const users = ref([])
const form = ref({
  username: '',
  password: '',
  is_admin: false,
})

const operatorName = computed(() => authState.user?.displayName || authState.user?.username || '当前管理员')

function formatDate(value) {
  if (!value) return '未提供'
  const numeric = Number(value)
  const date = Number.isFinite(numeric)
    ? new Date(numeric < 1e12 ? numeric * 1000 : numeric)
    : new Date(value)

  if (Number.isNaN(date.getTime())) {
    return String(value)
  }

  return date.toLocaleString('zh-CN', { hour12: false })
}

function normalizeUsers(payload) {
  const rawItems = Array.isArray(payload?.items)
    ? payload.items
    : Array.isArray(payload)
      ? payload
      : []

  return rawItems.map((item, index) => ({
    key: item.id || item.username || index,
    id: item.id || '-',
    username: item.username || `user-${index + 1}`,
    isAdmin: Boolean(item.is_admin || item.isAdmin),
    createdAt: formatDate(item.created_at || item.createdAt),
  }))
}

async function fetchUsers() {
  try {
    loading.value = true
    error.value = ''
    const response = await getAdminUsers()
    users.value = normalizeUsers(response)
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || '加载用户失败'
  } finally {
    loading.value = false
  }
}

function resetForm() {
  form.value = {
    username: '',
    password: '',
    is_admin: false,
  }
}

async function handleSubmit() {
  const username = form.value.username.trim()
  const password = form.value.password

  if (!username || !password) {
    error.value = '请填写用户名和密码'
    success.value = ''
    return
  }

  try {
    submitting.value = true
    error.value = ''
    success.value = ''
    await createAdminUser({
      username,
      password,
      is_admin: form.value.is_admin,
    })
    success.value = form.value.is_admin
      ? `管理员 ${username} 已创建`
      : `用户 ${username} 已创建`
    resetForm()
    await fetchUsers()
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || '创建用户失败'
    success.value = ''
  } finally {
    submitting.value = false
  }
}

onMounted(fetchUsers)
</script>

<template>
  <div class="admin-users-view">
    <div class="container">
      <section class="hero">
        <div>
          <p class="eyebrow">Admin Console</p>
          <h1 class="page-title">用户管理</h1>
          <p class="page-desc">管理员可以在这里创建站内普通用户或新的管理员账号。</p>
        </div>
        <div class="hero-meta">
          <span class="meta-pill">当前操作人：{{ operatorName }}</span>
          <button class="refresh-btn" :disabled="loading" @click="fetchUsers">
            {{ loading ? '刷新中...' : '刷新列表' }}
          </button>
        </div>
      </section>

      <div class="layout">
        <section class="panel">
          <div class="panel-head">
            <div>
              <h2 class="panel-title">现有用户</h2>
              <p class="panel-desc">当前所有可登录站内账号。</p>
            </div>
            <span class="count-badge">{{ users.length }}</span>
          </div>

          <div v-if="error" class="notice error">{{ error }}</div>
          <div v-else-if="loading && !users.length" class="skeleton-list">
            <div v-for="item in 3" :key="item" class="skeleton-card"></div>
          </div>
          <div v-else-if="users.length" class="user-list">
            <article v-for="user in users" :key="user.key" class="user-card">
              <div class="user-row">
                <div>
                  <h3 class="user-name">@{{ user.username }}</h3>
                  <p class="user-meta">ID: {{ user.id }}</p>
                </div>
                <span :class="['role-badge', { 'role-badge--admin': user.isAdmin }]">
                  {{ user.isAdmin ? '管理员' : '普通用户' }}
                </span>
              </div>
              <p class="created-at">创建时间：{{ user.createdAt }}</p>
            </article>
          </div>
          <div v-else class="empty-state">暂无用户数据</div>
        </section>

        <section class="panel">
          <div class="panel-head">
            <div>
              <h2 class="panel-title">创建用户</h2>
              <p class="panel-desc">默认创建普通用户，勾选后可直接创建管理员账号。</p>
            </div>
          </div>

          <div v-if="success" class="notice success">{{ success }}</div>
          <div v-if="error" class="notice error">{{ error }}</div>

          <form class="form" @submit.prevent="handleSubmit">
            <div class="field">
              <label for="username" class="label">用户名</label>
              <input
                id="username"
                v-model="form.username"
                type="text"
                class="input"
                autocomplete="off"
                placeholder="例如 user01"
              />
            </div>

            <div class="field">
              <label for="password" class="label">密码</label>
              <input
                id="password"
                v-model="form.password"
                type="password"
                class="input"
                autocomplete="new-password"
                placeholder="至少 6 位"
              />
            </div>

            <label class="checkbox-row">
              <input v-model="form.is_admin" type="checkbox" />
              <span>创建为管理员</span>
            </label>

            <button type="submit" class="submit-btn" :disabled="submitting">
              {{ submitting ? '创建中...' : '创建账号' }}
            </button>
          </form>
        </section>
      </div>
    </div>
  </div>
</template>

<style scoped>
.admin-users-view {
  padding: 24px 0 40px;
}

.container {
  max-width: 1180px;
  margin: 0 auto;
  padding: 0 20px;
}

.hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  padding: 28px;
  border: 1px solid var(--color-border);
  border-radius: 24px;
  background:
    radial-gradient(circle at top right, rgba(59, 130, 246, 0.16), transparent 32%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.95), var(--color-surface));
  box-shadow: var(--shadow-md);
}

[data-theme='dark'] .hero {
  background:
    radial-gradient(circle at top right, rgba(96, 165, 250, 0.2), transparent 32%),
    linear-gradient(180deg, rgba(28, 31, 38, 0.98), var(--color-surface));
}

.eyebrow {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--color-primary);
}

.page-title {
  margin-top: 8px;
  font-size: 32px;
  line-height: 1.15;
}

.page-desc {
  margin-top: 10px;
  max-width: 520px;
  font-size: 14px;
  color: var(--color-text-secondary);
}

.hero-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.meta-pill,
.count-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 36px;
  padding: 0 14px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
  background: var(--color-primary-light);
}

.count-badge {
  min-width: 36px;
}

.layout {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(320px, 0.85fr);
  gap: 20px;
  margin-top: 20px;
}

.panel {
  padding: 24px;
  border: 1px solid var(--color-border);
  border-radius: 22px;
  background: var(--color-surface);
  box-shadow: var(--shadow-sm);
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.panel-title {
  font-size: 20px;
  font-weight: 700;
}

.panel-desc {
  margin-top: 6px;
  font-size: 13px;
  color: var(--color-text-muted);
}

.notice {
  margin-bottom: 16px;
  padding: 12px 14px;
  border-radius: 12px;
  font-size: 13px;
  color: var(--color-text-secondary);
  background: var(--color-primary-light);
}

.notice.error {
  color: #b91c1c;
  background: rgba(225, 29, 72, 0.1);
}

.notice.success {
  color: #166534;
  background: rgba(16, 185, 129, 0.12);
}

.refresh-btn,
.submit-btn {
  min-height: 42px;
  padding: 0 16px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 700;
  transition: transform 0.2s, box-shadow 0.2s, opacity 0.2s;
}

.refresh-btn {
  color: var(--color-primary);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
}

.submit-btn {
  color: #fff;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-hover));
  box-shadow: 0 14px 24px rgba(37, 99, 235, 0.2);
}

.refresh-btn:hover:not(:disabled),
.submit-btn:hover:not(:disabled) {
  transform: translateY(-1px);
}

.refresh-btn:disabled,
.submit-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.user-list,
.skeleton-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.user-card {
  padding: 18px;
  border: 1px solid var(--color-border);
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(59, 130, 246, 0.05), transparent 60%);
}

.user-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.user-name {
  font-size: 17px;
  font-weight: 700;
}

.user-meta,
.created-at {
  margin-top: 6px;
  font-size: 13px;
  color: var(--color-text-muted);
}

.role-badge {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  color: var(--color-text-secondary);
  background: var(--color-bg);
}

.role-badge--admin {
  color: var(--color-primary);
  background: var(--color-primary-light);
}

.skeleton-card {
  height: 112px;
  border-radius: 18px;
  background: linear-gradient(90deg, var(--color-border) 25%, var(--color-shimmer-highlight) 50%, var(--color-border) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite linear;
}

@keyframes shimmer {
  0% {
    background-position: 200% 0;
  }

  100% {
    background-position: -200% 0;
  }
}

.empty-state {
  padding: 36px 20px;
  text-align: center;
  font-size: 14px;
  color: var(--color-text-muted);
  border: 1px dashed var(--color-border);
  border-radius: 16px;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.input {
  width: 100%;
  padding: 12px 14px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: var(--color-bg);
  color: var(--color-text);
  transition: border-color 0.2s, box-shadow 0.2s;
}

.input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.12);
}

.checkbox-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  color: var(--color-text-secondary);
}

@media (max-width: 900px) {
  .hero,
  .layout {
    grid-template-columns: 1fr;
  }

  .hero {
    align-items: flex-start;
    flex-direction: column;
  }

  .hero-meta {
    justify-content: flex-start;
  }
}

@media (max-width: 640px) {
  .admin-users-view {
    padding-top: 16px;
  }

  .container {
    padding: 0 16px;
  }

  .hero,
  .panel {
    padding: 20px;
    border-radius: 18px;
  }

  .page-title {
    font-size: 28px;
  }

  .user-row,
  .panel-head {
    flex-direction: column;
  }
}
</style>
