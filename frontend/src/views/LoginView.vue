<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { authState, loginWithPassword } from '../utils/auth'

const route = useRoute()
const router = useRouter()

const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

const redirectTarget = computed(() => {
  const redirect = route.query.redirect
  if (typeof redirect === 'string' && redirect.startsWith('/')) {
    return redirect
  }
  return '/'
})

async function handleLogin() {
  if (!username.value.trim() || !password.value) {
    error.value = '请输入用户名和密码'
    return
  }

  try {
    loading.value = true
    error.value = ''
    await loginWithPassword(username.value, password.value)
    router.push(redirectTarget.value)
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || '登录失败，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-view">
    <div class="login-card">
      <div class="login-copy">
        <p class="eyebrow">Comic Web</p>
        <h1 class="login-title">账号登录</h1>
        <p class="login-desc">使用站内用户名和密码登录后继续访问内容与管理页面。</p>
      </div>

      <div v-if="authState.user" class="notice success">
        当前已登录为 {{ authState.user.displayName || authState.user.username }}
      </div>
      <div v-else-if="redirectTarget !== '/'" class="notice">
        登录后将跳转到 {{ redirectTarget }}
      </div>

      <form class="login-form" @submit.prevent="handleLogin">
        <div class="field">
          <label for="username" class="label">用户名</label>
          <input
            id="username"
            v-model="username"
            type="text"
            class="input"
            autocomplete="username"
            placeholder="输入用户名"
            autofocus
          />
        </div>

        <div class="field">
          <label for="password" class="label">密码</label>
          <input
            id="password"
            v-model="password"
            type="password"
            class="input"
            autocomplete="current-password"
            placeholder="输入密码"
          />
        </div>

        <div v-if="error" class="notice error">
          {{ error }}
        </div>

        <button type="submit" class="submit-btn" :disabled="loading">
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.login-view {
  min-height: calc(100vh - 72px);
  display: grid;
  place-items: center;
  padding: 24px;
}

.login-card {
  width: 100%;
  max-width: 420px;
  padding: 36px 32px;
  border: 1px solid var(--color-border);
  border-radius: 24px;
  background:
    radial-gradient(circle at top right, rgba(59, 130, 246, 0.16), transparent 30%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.96), var(--color-surface));
  box-shadow: var(--shadow-lg);
}

[data-theme='dark'] .login-card {
  background:
    radial-gradient(circle at top right, rgba(96, 165, 250, 0.18), transparent 30%),
    linear-gradient(180deg, rgba(28, 31, 38, 0.98), var(--color-surface));
}

.login-copy {
  margin-bottom: 24px;
}

.eyebrow {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--color-primary);
}

.login-title {
  margin-top: 10px;
  font-size: 30px;
  line-height: 1.15;
}

.login-desc {
  margin-top: 10px;
  font-size: 14px;
  color: var(--color-text-secondary);
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
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
  transition: border-color 0.2s, box-shadow 0.2s, transform 0.2s;
}

.input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.12);
  transform: translateY(-1px);
}

.notice {
  margin-bottom: 18px;
  padding: 12px 14px;
  border-radius: 12px;
  font-size: 13px;
  color: var(--color-text-secondary);
  background: var(--color-primary-light);
}

.notice.success {
  color: #166534;
  background: rgba(16, 185, 129, 0.12);
}

.notice.error {
  margin-bottom: 0;
  color: #b91c1c;
  background: rgba(225, 29, 72, 0.1);
}

.submit-btn {
  padding: 12px 16px;
  border-radius: 12px;
  color: #fff;
  font-size: 15px;
  font-weight: 700;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-hover));
  box-shadow: 0 12px 24px rgba(37, 99, 235, 0.2);
  transition: transform 0.2s, box-shadow 0.2s, opacity 0.2s;
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 16px 28px rgba(37, 99, 235, 0.24);
}

.submit-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
  box-shadow: none;
}

@media (max-width: 640px) {
  .login-card {
    padding: 28px 20px;
    border-radius: 20px;
  }

  .login-title {
    font-size: 26px;
  }
}
</style>
