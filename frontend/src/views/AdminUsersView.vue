<script setup>
import { computed, onMounted, ref } from 'vue'
import {
  createAdminUser,
  deleteAdminUser,
  getAdminUsers,
  resetAdminUserPassword,
  updateAdminUser,
} from '../api'
import { authState } from '../utils/auth'

const loading = ref(false)
const creating = ref(false)
const mutatingIds = ref(new Set())
const error = ref('')
const success = ref('')
const users = ref([])
const passwordDrafts = ref({})
const createForm = ref({
  username: '',
  password: '',
  is_admin: false,
})

const operatorName = computed(() => authState.user?.displayName || authState.user?.username || 'Current admin')

function setMutating(userId, active) {
  const next = new Set(mutatingIds.value)
  if (active) next.add(userId)
  else next.delete(userId)
  mutatingIds.value = next
}

function isMutating(userId) {
  return mutatingIds.value.has(userId)
}

function normalizeUsers(payload) {
  const rawItems = Array.isArray(payload?.items) ? payload.items : []
  return rawItems.map((item) => ({
    id: item.id,
    username: item.username,
    is_admin: Boolean(item.is_admin),
    is_active: item.is_active !== false,
    created_at: item.created_at,
  }))
}

function formatDate(value) {
  if (!value) return 'N/A'
  const numeric = Number(value)
  const date = Number.isFinite(numeric)
    ? new Date(numeric < 1e12 ? numeric * 1000 : numeric)
    : new Date(value)

  if (Number.isNaN(date.getTime())) {
    return String(value)
  }

  return date.toLocaleString('zh-CN', { hour12: false })
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

function resetCreateForm() {
  createForm.value = {
    username: '',
    password: '',
    is_admin: false,
  }
}

async function handleCreate() {
  const username = createForm.value.username.trim()
  const password = createForm.value.password

  if (!username || !password) {
    error.value = '请填写用户名和密码'
    return
  }

  try {
    creating.value = true
    error.value = ''
    success.value = ''
    await createAdminUser({
      username,
      password,
      is_admin: createForm.value.is_admin,
    })
    success.value = createForm.value.is_admin
      ? `管理员 ${username} 已创建`
      : `用户 ${username} 已创建`
    resetCreateForm()
    await fetchUsers()
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || '创建用户失败'
  } finally {
    creating.value = false
  }
}

async function handleToggleActive(user) {
  try {
    setMutating(user.id, true)
    error.value = ''
    success.value = ''
    await updateAdminUser(user.id, { is_active: !user.is_active })
    success.value = !user.is_active
      ? `已启用 ${user.username}`
      : `已禁用 ${user.username}`
    await fetchUsers()
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || '更新用户状态失败'
  } finally {
    setMutating(user.id, false)
  }
}

async function handleToggleAdmin(user) {
  try {
    setMutating(user.id, true)
    error.value = ''
    success.value = ''
    await updateAdminUser(user.id, { is_admin: !user.is_admin })
    success.value = !user.is_admin
      ? `${user.username} 已设为管理员`
      : `${user.username} 已调整为普通用户`
    await fetchUsers()
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || '更新管理员状态失败'
  } finally {
    setMutating(user.id, false)
  }
}

async function handleResetPassword(user) {
  const nextPassword = (passwordDrafts.value[user.id] || '').trim()
  if (!nextPassword) {
    error.value = `请先输入 ${user.username} 的新密码`
    return
  }

  try {
    setMutating(user.id, true)
    error.value = ''
    success.value = ''
    await resetAdminUserPassword(user.id, nextPassword)
    passwordDrafts.value = {
      ...passwordDrafts.value,
      [user.id]: '',
    }
    success.value = `${user.username} 的密码已重置`
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || '重置密码失败'
  } finally {
    setMutating(user.id, false)
  }
}

async function handleDelete(user) {
  if (!window.confirm(`确定删除用户 ${user.username} 吗？`)) return

  try {
    setMutating(user.id, true)
    error.value = ''
    success.value = ''
    await deleteAdminUser(user.id)
    success.value = `${user.username} 已删除`
    await fetchUsers()
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || '删除用户失败'
  } finally {
    setMutating(user.id, false)
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
          <p class="page-desc">在这里创建用户，并管理账号状态、管理员权限和密码。</p>
        </div>
        <div class="hero-meta">
          <span class="meta-pill">当前操作人：{{ operatorName }}</span>
          <button class="refresh-btn" :disabled="loading" @click="fetchUsers">
            {{ loading ? '刷新中...' : '刷新列表' }}
          </button>
        </div>
      </section>

      <div v-if="error" class="notice error">{{ error }}</div>
      <div v-if="success" class="notice success">{{ success }}</div>

      <div class="layout">
        <section class="panel">
          <div class="panel-head">
            <div>
              <h2 class="panel-title">创建用户</h2>
              <p class="panel-desc">默认创建普通用户，勾选后创建管理员。</p>
            </div>
          </div>

          <form class="form" @submit.prevent="handleCreate">
            <div class="field">
              <label for="username" class="label">用户名</label>
              <input id="username" v-model="createForm.username" type="text" class="input" placeholder="例如 user01" />
            </div>

            <div class="field">
              <label for="password" class="label">初始密码</label>
              <input id="password" v-model="createForm.password" type="password" class="input" placeholder="至少 6 位" />
            </div>

            <label class="checkbox-row">
              <input v-model="createForm.is_admin" type="checkbox" />
              <span>创建为管理员</span>
            </label>

            <button type="submit" class="submit-btn" :disabled="creating">
              {{ creating ? '创建中...' : '创建账号' }}
            </button>
          </form>
        </section>

        <section class="panel">
          <div class="panel-head">
            <div>
              <h2 class="panel-title">现有用户</h2>
              <p class="panel-desc">支持启用/禁用、权限调整、密码重置和删除。</p>
            </div>
            <span class="count-badge">{{ users.length }}</span>
          </div>

          <div v-if="loading && !users.length" class="skeleton-list">
            <div v-for="item in 3" :key="item" class="skeleton-card"></div>
          </div>

          <div v-else-if="users.length" class="user-list">
            <article v-for="user in users" :key="user.id" class="user-card">
              <div class="user-row">
                <div>
                  <h3 class="user-name">@{{ user.username }}</h3>
                  <p class="user-meta">创建时间：{{ formatDate(user.created_at) }}</p>
                </div>
                <div class="badge-row">
                  <span :class="['role-badge', { 'role-badge--admin': user.is_admin }]">
                    {{ user.is_admin ? '管理员' : '普通用户' }}
                  </span>
                  <span :class="['status-badge', { 'status-badge--active': user.is_active }]">
                    {{ user.is_active ? '已启用' : '已禁用' }}
                  </span>
                </div>
              </div>

              <div class="action-grid">
                <button class="mini-btn" :disabled="isMutating(user.id)" @click="handleToggleActive(user)">
                  {{ user.is_active ? '禁用账号' : '启用账号' }}
                </button>
                <button class="mini-btn" :disabled="isMutating(user.id)" @click="handleToggleAdmin(user)">
                  {{ user.is_admin ? '撤销管理员' : '设为管理员' }}
                </button>
              </div>

              <div class="reset-box">
                <input
                  v-model="passwordDrafts[user.id]"
                  type="password"
                  class="input"
                  placeholder="输入新密码后重置"
                />
                <button class="mini-btn" :disabled="isMutating(user.id)" @click="handleResetPassword(user)">
                  重置密码
                </button>
                <button class="mini-btn mini-btn--danger" :disabled="isMutating(user.id)" @click="handleDelete(user)">
                  删除用户
                </button>
              </div>
            </article>
          </div>

          <div v-else class="empty-state">暂无用户数据</div>
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
.count-badge,
.role-badge,
.status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 28px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.meta-pill,
.count-badge {
  min-height: 36px;
  color: var(--color-text-secondary);
  background: var(--color-primary-light);
}

.role-badge {
  color: var(--color-text-secondary);
  background: var(--color-bg);
}

.role-badge--admin {
  color: var(--color-primary);
  background: var(--color-primary-light);
}

.status-badge {
  color: #b45309;
  background: rgba(245, 158, 11, 0.12);
}

.status-badge--active {
  color: #15803d;
  background: rgba(22, 163, 74, 0.12);
}

.layout {
  display: grid;
  grid-template-columns: minmax(320px, 0.8fr) minmax(0, 1.2fr);
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
  margin: 16px auto 0;
  max-width: 1180px;
  padding: 12px 14px;
  border-radius: 12px;
  font-size: 13px;
}

.notice.error {
  color: #b91c1c;
  background: rgba(225, 29, 72, 0.1);
}

.notice.success {
  color: #166534;
  background: rgba(16, 185, 129, 0.12);
}

.form,
.user-list,
.skeleton-list {
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

.refresh-btn,
.submit-btn,
.mini-btn {
  min-height: 40px;
  padding: 0 16px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 700;
  transition: transform 0.2s, opacity 0.2s, border-color 0.2s;
}

.refresh-btn,
.mini-btn {
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  background: var(--color-bg);
}

.submit-btn {
  color: #fff;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-hover));
  box-shadow: 0 14px 24px rgba(37, 99, 235, 0.2);
}

.mini-btn--danger {
  color: #b91c1c;
  border-color: rgba(185, 28, 28, 0.2);
}

.refresh-btn:hover:not(:disabled),
.submit-btn:hover:not(:disabled),
.mini-btn:hover:not(:disabled) {
  transform: translateY(-1px);
}

.refresh-btn:disabled,
.submit-btn:disabled,
.mini-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.user-card {
  padding: 18px;
  border: 1px solid var(--color-border);
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(59, 130, 246, 0.05), transparent 60%);
}

.user-row,
.badge-row,
.action-grid,
.reset-box {
  display: flex;
  gap: 10px;
}

.user-row {
  align-items: flex-start;
  justify-content: space-between;
}

.badge-row,
.action-grid {
  flex-wrap: wrap;
}

.user-name {
  font-size: 17px;
  font-weight: 700;
}

.user-meta {
  margin-top: 6px;
  font-size: 13px;
  color: var(--color-text-muted);
}

.action-grid,
.reset-box {
  margin-top: 14px;
}

.reset-box {
  align-items: center;
  flex-wrap: wrap;
}

.reset-box .input {
  flex: 1;
  min-width: 220px;
}

.skeleton-card {
  height: 112px;
  border-radius: 18px;
  background: linear-gradient(90deg, var(--color-border) 25%, var(--color-shimmer-highlight) 50%, var(--color-border) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite linear;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.empty-state {
  padding: 36px 20px;
  text-align: center;
  font-size: 14px;
  color: var(--color-text-muted);
  border: 1px dashed var(--color-border);
  border-radius: 16px;
}

@media (max-width: 960px) {
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
  .reset-box,
  .panel-head {
    flex-direction: column;
  }
}
</style>
