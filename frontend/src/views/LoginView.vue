<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { login } from '../api'

const router = useRouter()
const password = ref('')
const loading = ref(false)
const error = ref(null)

async function handleLogin() {
  if (!password.value) {
    error.value = '请输入密码'
    return
  }
  try {
    loading.value = true
    error.value = null
    const result = await login(password.value)
    // Store auth token
    localStorage.setItem('auth_token', result.token || 'authenticated')
    localStorage.setItem('is_authenticated', 'true')
    router.push('/')
  } catch (e) {
    error.value = e.response?.data?.detail || '密码错误'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-view">
    <div class="login-card">
      <h1 class="login-title">网站访问验证</h1>
      <p class="login-desc">请输入访问密码</p>

      <form @submit.prevent="handleLogin" class="login-form">
        <div class="field">
          <label for="password" class="label">访问密码</label>
          <input
            id="password"
            v-model="password"
            type="password"
            autocomplete="current-password"
            placeholder="输入密码"
            class="input"
            autofocus
          />
        </div>

        <div v-if="error" class="error-msg">{{ error }}</div>

        <button type="submit" class="submit-btn" :disabled="loading">
          {{ loading ? '验证中...' : '进入' }}
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.login-view {
  min-height: calc(100vh - 72px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.login-card {
  width: 100%;
  max-width: 380px;
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  padding: 36px 32px;
}

.login-title {
  font-size: 22px;
  font-weight: 700;
  text-align: center;
  color: var(--color-text);
}

.login-desc {
  font-size: 14px;
  color: var(--color-text-muted);
  text-align: center;
  margin-top: 6px;
  margin-bottom: 28px;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.input {
  padding: 10px 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 14px;
  color: var(--color-text);
  background: var(--color-bg);
  transition: border-color 0.2s, box-shadow 0.2s;
}

.input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.error-msg {
  font-size: 13px;
  color: var(--color-accent);
  text-align: center;
}

.submit-btn {
  padding: 11px;
  background: var(--color-primary);
  color: #fff;
  border-radius: var(--radius-sm);
  font-size: 15px;
  font-weight: 600;
  transition: background 0.2s;
  margin-top: 4px;
}

.submit-btn:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
