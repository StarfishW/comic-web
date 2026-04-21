<script setup>
defineOptions({ name: 'CommentSection' })

import { computed, ref, watch } from 'vue'
import * as api from '../api'
import { authState, isAdminUser } from '../utils/auth'

const PAGE_SIZE = 10
const MAX_REPLY_INDENT = 3

const props = defineProps({
  albumId: {
    type: String,
    required: true,
  },
  title: {
    type: String,
    default: '',
  },
})

const comments = ref([])
const loading = ref(false)
const loadingMore = ref(false)
const refreshing = ref(false)
const postingRoot = ref(false)
const postingReply = ref(false)
const deletingIds = ref(new Set())
const page = ref(1)
const pageCount = ref(0)
const total = ref(0)
const hasMore = ref(false)
const error = ref('')
const notice = ref('')
const noticeType = ref('info')
const rootDraft = ref('')
const replyDraft = ref('')
const replyTarget = ref(null)
const hasLoadedOnce = ref(false)

let requestId = 0

const currentUser = computed(() => authState.user)
const canPost = computed(() => Boolean(currentUser.value))
const visibleCount = computed(() => {
  if (!hasLoadedOnce.value) return null
  return total.value || countComments(comments.value) || 0
})
const sectionSubtitle = computed(() => (
  props.title ? `《${props.title}》的站内评论` : '站内评论'
))

function setNotice(message = '', type = 'info') {
  notice.value = message
  noticeType.value = type
}

function normalizeId(value) {
  if (value === null || value === undefined || value === '') return ''
  return String(value)
}

function resolveDate(value) {
  if (!value) return null
  const numeric = Number(value)
  const date = Number.isFinite(numeric)
    ? new Date(numeric < 1e12 ? numeric * 1000 : numeric)
    : new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

function formatTime(value) {
  const date = resolveDate(value)
  if (!date) return '刚刚'

  const diff = Date.now() - date.getTime()
  const minute = 60 * 1000
  const hour = 60 * minute
  const day = 24 * hour

  if (diff < minute) return '刚刚'
  if (diff < hour) return `${Math.floor(diff / minute)} 分钟前`
  if (diff < day) return `${Math.floor(diff / hour)} 小时前`
  if (diff < day * 7) return `${Math.floor(diff / day)} 天前`

  return date.toLocaleString('zh-CN', {
    hour12: false,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function normalizeComment(item) {
  const user = item?.user || {}
  return {
    id: normalizeId(item?.id),
    parentId: normalizeId(item?.parent_id),
    content: item?.is_deleted ? '该评论已删除' : String(item?.content || '').trim(),
    deleted: Boolean(item?.is_deleted),
    createdAt: item?.created_at || item?.updated_at || '',
    authorId: normalizeId(user?.id),
    authorName: user?.username || '匿名用户',
    avatarUrl: user?.avatar_url || '',
    isAdmin: Boolean(user?.is_admin),
    canDelete: Boolean(item?.can_delete),
    replies: Array.isArray(item?.replies) ? item.replies.map(normalizeComment) : [],
  }
}

function normalizeComments(payload) {
  const items = Array.isArray(payload?.items) ? payload.items : []
  return items.map(normalizeComment).filter((item) => item.id)
}

function countComments(list) {
  return list.reduce((sum, item) => sum + 1 + countComments(item.replies || []), 0)
}

function flattenReplies(replies, parentName = '', depth = 1) {
  return replies.flatMap((reply) => {
    const current = {
      ...reply,
      depth,
      replyToName: parentName,
    }
    return [current, ...flattenReplies(reply.replies || [], reply.authorName, depth + 1)]
  })
}

function getFlatReplies(comment) {
  return flattenReplies(comment.replies || [], comment.authorName, 1)
}

function getReplyIndent(depth) {
  return `${Math.min(depth, MAX_REPLY_INDENT) * 18}px`
}

function setDeleting(commentId, active) {
  const next = new Set(deletingIds.value)
  if (active) next.add(commentId)
  else next.delete(commentId)
  deletingIds.value = next
}

function canDeleteComment(comment) {
  if (!currentUser.value || comment.deleted) return false
  if (comment.canDelete) return true
  return comment.authorId === normalizeId(currentUser.value.id) || isAdminUser(currentUser.value)
}

function getErrorMessage(err, fallback) {
  if (err?.response?.status === 401) {
    return '请先登录后再操作'
  }
  return err?.response?.data?.detail || err?.message || fallback
}

async function loadComments(targetPage = 1, append = false, options = {}) {
  if (!props.albumId) return

  const { soft = false } = options
  const currentRequestId = ++requestId

  if (append) {
    loadingMore.value = true
  } else if (soft) {
    refreshing.value = true
  } else {
    loading.value = true
    error.value = ''
  }

  try {
    const payload = await api.getComments(props.albumId, {
      page: targetPage,
      page_size: PAGE_SIZE,
    })
    if (currentRequestId !== requestId) return

    const normalized = normalizeComments(payload)
    comments.value = append ? [...comments.value, ...normalized] : normalized
    page.value = targetPage
    pageCount.value = Number(payload?.page_count || 0)
    total.value = Number(payload?.total || countComments(comments.value))
    hasMore.value = pageCount.value > 0 ? targetPage < pageCount.value : normalized.length >= PAGE_SIZE
    hasLoadedOnce.value = true
  } catch (err) {
    if (currentRequestId !== requestId) return

    if (!append && !soft) {
      comments.value = []
      page.value = 1
      pageCount.value = 0
      total.value = 0
      hasMore.value = false
      hasLoadedOnce.value = false
      error.value = getErrorMessage(err, '评论加载失败，请稍后重试')
    } else {
      setNotice(getErrorMessage(err, soft ? '刷新评论失败，请稍后重试' : '加载更多评论失败'), 'error')
    }
  } finally {
    if (currentRequestId === requestId) {
      if (append) loadingMore.value = false
      else if (soft) refreshing.value = false
      else loading.value = false
    }
  }
}

async function refreshComments(options = {}) {
  const soft = options.soft === true && comments.value.length > 0
  await loadComments(1, false, { soft })
}

async function loadMore() {
  if (loading.value || loadingMore.value || !hasMore.value) return
  await loadComments(page.value + 1, true)
}

function toggleReply(comment) {
  if (!canPost.value) return
  if (replyTarget.value?.id === comment.id) {
    replyTarget.value = null
    replyDraft.value = ''
    return
  }
  replyTarget.value = comment
  replyDraft.value = ''
}

function cancelReply() {
  replyTarget.value = null
  replyDraft.value = ''
}

async function submitRootComment() {
  const content = rootDraft.value.trim()
  if (!content || postingRoot.value) return

  try {
    postingRoot.value = true
    setNotice('')
    await api.postComment(props.albumId, content, null)
    rootDraft.value = ''
    await refreshComments({ soft: true })
    setNotice('评论已发布', 'success')
  } catch (err) {
    setNotice(getErrorMessage(err, '评论发布失败，请稍后重试'), 'error')
  } finally {
    postingRoot.value = false
  }
}

async function submitReply() {
  const content = replyDraft.value.trim()
  if (!content || !replyTarget.value?.id || postingReply.value) return

  try {
    postingReply.value = true
    setNotice('')
    await api.postComment(props.albumId, content, Number(replyTarget.value.id))
    replyDraft.value = ''
    replyTarget.value = null
    await refreshComments({ soft: true })
    setNotice('回复已发布', 'success')
  } catch (err) {
    setNotice(getErrorMessage(err, '回复发布失败，请稍后重试'), 'error')
  } finally {
    postingReply.value = false
  }
}

async function handleDelete(comment) {
  if (!comment?.id || deletingIds.value.has(comment.id)) return
  if (!window.confirm('确定删除这条评论吗？')) return

  try {
    setDeleting(comment.id, true)
    setNotice('')
    await api.deleteComment(comment.id)
    if (replyTarget.value?.id === comment.id) {
      cancelReply()
    }
    await refreshComments({ soft: true })
    setNotice('评论已删除', 'success')
  } catch (err) {
    setNotice(getErrorMessage(err, '删除评论失败，请稍后重试'), 'error')
  } finally {
    setDeleting(comment.id, false)
  }
}

watch(
  () => props.albumId,
  () => {
    comments.value = []
    rootDraft.value = ''
    replyDraft.value = ''
    replyTarget.value = null
    page.value = 1
    pageCount.value = 0
    total.value = 0
    hasMore.value = false
    error.value = ''
    hasLoadedOnce.value = false
    setNotice('')
    void refreshComments()
  },
  { immediate: true },
)
</script>

<template>
  <section class="comment-section">
    <div class="section-head">
      <div>
        <h2 class="section-title">
          评论
          <span v-if="visibleCount !== null" class="count-badge">{{ visibleCount }}</span>
        </h2>
        <p class="section-subtitle">{{ sectionSubtitle }}</p>
      </div>

      <button
        class="refresh-btn"
        :disabled="loading || loadingMore || refreshing"
        @click="refreshComments({ soft: true })"
      >
        <span :class="['refresh-icon', { spinning: refreshing }]">↻</span>
        {{ refreshing ? '刷新中' : '更新评论' }}
      </button>
    </div>

    <div class="composer-card">
      <div class="composer-head">
        <div>
          <p class="composer-title">发表评论</p>
          <p class="composer-desc">
            {{ canPost ? '支持 Ctrl + Enter 快速发布' : '登录后可以参与评论和回复' }}
          </p>
        </div>
        <router-link v-if="!canPost" to="/login" class="login-link">去登录</router-link>
      </div>

      <textarea
        v-model="rootDraft"
        class="composer-input"
        rows="4"
        maxlength="2000"
        :disabled="!canPost || postingRoot"
        placeholder="写下你的看法，理性讨论。"
        @keydown.ctrl.enter.prevent="submitRootComment"
      ></textarea>

      <div class="composer-footer">
        <span class="draft-count">{{ rootDraft.trim().length }}/2000</span>
        <button
          class="submit-btn"
          :disabled="!canPost || !rootDraft.trim() || postingRoot"
          @click="submitRootComment"
        >
          {{ postingRoot ? '发布中...' : '发布评论' }}
        </button>
      </div>
    </div>

    <div v-if="notice" :class="['notice', `notice--${noticeType}`]">
      {{ notice }}
    </div>

    <div v-if="loading" class="loading-list">
      <div v-for="item in 3" :key="item" class="comment-skeleton"></div>
    </div>

    <div v-else-if="error" class="state-card state-card--error">
      <p>{{ error }}</p>
      <button class="retry-btn" @click="refreshComments">重新加载</button>
    </div>

    <div v-else-if="!comments.length" class="state-card">
      <p>还没有评论，来发第一条吧。</p>
    </div>

    <div v-else class="comment-list">
      <article v-for="comment in comments" :key="comment.id" class="comment-card">
        <div class="comment-main">
          <div class="avatar">
            <img v-if="comment.avatarUrl" :src="comment.avatarUrl" :alt="comment.authorName" class="avatar-image" />
            <span v-else>{{ comment.authorName.slice(0, 1) }}</span>
          </div>

          <div class="comment-body">
            <div class="comment-meta">
              <span class="author-name">{{ comment.authorName }}</span>
              <span v-if="comment.isAdmin" class="meta-pill">管理员</span>
              <span class="comment-time">{{ formatTime(comment.createdAt) }}</span>
            </div>

            <p class="comment-content">{{ comment.content }}</p>

            <div class="comment-actions">
              <button class="action-btn" :disabled="!canPost" @click="toggleReply(comment)">
                {{ replyTarget?.id === comment.id ? '收起回复' : '回复' }}
              </button>
              <button
                v-if="canDeleteComment(comment)"
                class="action-btn action-btn--danger"
                :disabled="deletingIds.has(comment.id)"
                @click="handleDelete(comment)"
              >
                {{ deletingIds.has(comment.id) ? '删除中...' : '删除' }}
              </button>
            </div>

            <div v-if="replyTarget?.id === comment.id" class="reply-box">
              <p class="reply-title">回复 {{ comment.authorName }}</p>
              <textarea
                v-model="replyDraft"
                class="composer-input composer-input--reply"
                rows="3"
                maxlength="2000"
                :disabled="postingReply"
                :placeholder="`回复 @${comment.authorName}`"
                @keydown.ctrl.enter.prevent="submitReply"
              ></textarea>
              <div class="composer-footer">
                <button class="text-btn" :disabled="postingReply" @click="cancelReply">取消</button>
                <div class="reply-actions">
                  <span class="draft-count">{{ replyDraft.trim().length }}/2000</span>
                  <button class="submit-btn" :disabled="!replyDraft.trim() || postingReply" @click="submitReply">
                    {{ postingReply ? '发送中...' : '发送回复' }}
                  </button>
                </div>
              </div>
            </div>

            <div v-if="comment.replies?.length" class="reply-list">
              <article
                v-for="reply in getFlatReplies(comment)"
                :key="reply.id"
                class="reply-card"
                :style="{ '--reply-indent': getReplyIndent(reply.depth) }"
              >
                <div class="reply-meta">
                  <span class="author-name">{{ reply.authorName }}</span>
                  <span v-if="reply.replyToName" class="reply-to">回复 @{{ reply.replyToName }}</span>
                  <span v-if="reply.isAdmin" class="meta-pill">管理员</span>
                  <span class="comment-time">{{ formatTime(reply.createdAt) }}</span>
                </div>

                <p class="comment-content">{{ reply.content }}</p>

                <div class="comment-actions">
                  <button class="action-btn" :disabled="!canPost" @click="toggleReply(reply)">
                    {{ replyTarget?.id === reply.id ? '收起回复' : '回复' }}
                  </button>
                  <button
                    v-if="canDeleteComment(reply)"
                    class="action-btn action-btn--danger"
                    :disabled="deletingIds.has(reply.id)"
                    @click="handleDelete(reply)"
                  >
                    {{ deletingIds.has(reply.id) ? '删除中...' : '删除' }}
                  </button>
                </div>

                <div v-if="replyTarget?.id === reply.id" class="reply-box reply-box--nested">
                  <p class="reply-title">回复 {{ reply.authorName }}</p>
                  <textarea
                    v-model="replyDraft"
                    class="composer-input composer-input--reply"
                    rows="3"
                    maxlength="2000"
                    :disabled="postingReply"
                    :placeholder="`回复 @${reply.authorName}`"
                    @keydown.ctrl.enter.prevent="submitReply"
                  ></textarea>
                  <div class="composer-footer">
                    <button class="text-btn" :disabled="postingReply" @click="cancelReply">取消</button>
                    <div class="reply-actions">
                      <span class="draft-count">{{ replyDraft.trim().length }}/2000</span>
                      <button class="submit-btn" :disabled="!replyDraft.trim() || postingReply" @click="submitReply">
                        {{ postingReply ? '发送中...' : '发送回复' }}
                      </button>
                    </div>
                  </div>
                </div>
              </article>
            </div>
          </div>
        </div>
      </article>
    </div>

    <div v-if="!loading && hasMore" class="load-more">
      <button class="load-more-btn" :disabled="loadingMore" @click="loadMore">
        {{ loadingMore ? '加载中...' : '加载更多评论' }}
      </button>
    </div>
  </section>
</template>

<style scoped>
.comment-section {
  margin-top: 36px;
  padding: 24px;
  border: 1px solid var(--color-border);
  border-radius: 24px;
  background:
    radial-gradient(circle at top right, rgba(59, 130, 246, 0.08), transparent 28%),
    var(--color-surface);
  box-shadow: var(--shadow-sm);
}

.section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text);
}

.count-badge,
.meta-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  color: var(--color-primary);
  background: var(--color-primary-light);
}

.section-subtitle {
  margin-top: 6px;
  font-size: 13px;
  color: var(--color-text-muted);
}

.refresh-btn,
.submit-btn,
.retry-btn,
.load-more-btn,
.login-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 40px;
  padding: 0 16px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 700;
  transition: transform 0.2s, opacity 0.2s, border-color 0.2s, color 0.2s, background 0.2s;
}

.refresh-btn,
.retry-btn,
.load-more-btn {
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  background: var(--color-bg);
}

.refresh-btn:hover:not(:disabled),
.retry-btn:hover:not(:disabled),
.load-more-btn:hover:not(:disabled) {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: var(--color-primary-light);
}

.refresh-icon {
  display: inline-block;
  font-size: 15px;
  line-height: 1;
}

.refresh-icon.spinning {
  animation: spin 0.8s linear infinite;
}

.submit-btn {
  color: #fff;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-hover));
  box-shadow: 0 14px 28px rgba(37, 99, 235, 0.18);
}

.login-link {
  color: var(--color-primary);
  background: var(--color-primary-light);
}

.refresh-btn:hover:not(:disabled),
.submit-btn:hover:not(:disabled),
.retry-btn:hover:not(:disabled),
.load-more-btn:hover:not(:disabled),
.login-link:hover {
  transform: translateY(-1px);
}

.refresh-btn:disabled,
.submit-btn:disabled,
.retry-btn:disabled,
.load-more-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.composer-card,
.comment-card,
.state-card {
  border: 1px solid var(--color-border);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.75);
}

[data-theme='dark'] .composer-card,
[data-theme='dark'] .comment-card,
[data-theme='dark'] .state-card {
  background: rgba(17, 24, 39, 0.68);
}

.composer-card {
  padding: 18px;
}

.composer-head,
.composer-footer,
.comment-meta,
.comment-actions,
.reply-meta,
.reply-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.composer-title,
.reply-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--color-text);
}

.composer-desc {
  margin-top: 4px;
  font-size: 12px;
  color: var(--color-text-muted);
}

.composer-input {
  width: 100%;
  margin-top: 16px;
  padding: 14px 16px;
  border: 1px solid var(--color-border);
  border-radius: 16px;
  background: var(--color-bg);
  color: var(--color-text);
  line-height: 1.6;
  resize: vertical;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.composer-input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.12);
}

.composer-input--reply {
  margin-top: 10px;
}

.draft-count {
  font-size: 12px;
  color: var(--color-text-muted);
}

.notice {
  margin-top: 16px;
  padding: 12px 14px;
  border-radius: 14px;
  font-size: 13px;
}

.notice--info {
  color: var(--color-text-secondary);
  background: var(--color-primary-light);
}

.notice--success {
  color: #166534;
  background: rgba(16, 185, 129, 0.12);
}

.notice--error {
  color: #b91c1c;
  background: rgba(225, 29, 72, 0.12);
}

.loading-list,
.comment-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-top: 16px;
}

.comment-skeleton {
  height: 132px;
  border-radius: 20px;
  background: linear-gradient(90deg, var(--color-border) 25%, var(--color-shimmer-highlight) 50%, var(--color-border) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite linear;
}

.comment-card {
  padding: 18px;
}

.comment-main {
  display: flex;
  gap: 14px;
}

.avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: 999px;
  flex-shrink: 0;
  overflow: hidden;
  font-size: 15px;
  font-weight: 700;
  color: var(--color-primary);
  background: var(--color-primary-light);
}

.avatar-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.comment-body {
  flex: 1;
  min-width: 0;
}

.author-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--color-text);
}

.comment-time,
.reply-to {
  font-size: 12px;
  color: var(--color-text-muted);
}

.reply-to {
  margin-left: auto;
}

.comment-content {
  margin-top: 10px;
  font-size: 14px;
  line-height: 1.75;
  color: var(--color-text-secondary);
  white-space: pre-wrap;
  word-break: break-word;
}

.comment-actions {
  justify-content: flex-start;
  margin-top: 12px;
}

.action-btn,
.text-btn {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-muted);
  transition: color 0.2s, opacity 0.2s;
}

.action-btn:hover:not(:disabled),
.text-btn:hover:not(:disabled) {
  color: var(--color-primary);
}

.action-btn--danger:hover:not(:disabled) {
  color: #dc2626;
}

.action-btn:disabled,
.text-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.reply-box {
  margin-top: 14px;
  padding: 14px;
  border-radius: 16px;
  background: rgba(59, 130, 246, 0.06);
}

.reply-box--nested {
  margin-left: 0;
}

.reply-list {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.reply-card {
  margin-left: var(--reply-indent);
  padding: 14px 16px;
  border-left: 2px solid rgba(59, 130, 246, 0.18);
  border-radius: 0 16px 16px 16px;
  background: rgba(59, 130, 246, 0.05);
}

.state-card {
  margin-top: 16px;
  padding: 32px 20px;
  text-align: center;
  color: var(--color-text-muted);
}

.state-card--error {
  color: #b91c1c;
}

.load-more {
  margin-top: 18px;
  text-align: center;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 768px) {
  .comment-section {
    padding: 18px;
    border-radius: 20px;
  }

  .section-head,
  .composer-head,
  .comment-meta,
  .reply-meta,
  .composer-footer {
    align-items: flex-start;
    flex-direction: column;
  }

  .reply-actions {
    width: 100%;
    justify-content: space-between;
  }
}

@media (max-width: 640px) {
  .comment-main {
    gap: 12px;
  }

  .avatar {
    width: 36px;
    height: 36px;
    font-size: 14px;
  }

  .reply-card {
    margin-left: 0;
  }
}
</style>
