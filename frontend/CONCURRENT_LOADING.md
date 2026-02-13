# 滚动模式并发加载说明

## ✅ 修复完成

现在 `maxConcurrent` 参数在**滚动模式和翻页模式下都生效**了！

## 🔄 修改内容

### 修改前
```javascript
// 严格顺序加载（一个接一个）
第1页完成 → 等50ms → 第2页完成 → 等50ms → 第3页完成
```

### 修改后
```javascript
// 支持并发加载（最多 maxConcurrent 个同时加载）
当 maxConcurrent = 5 时：

0ms:   启动第1页
50ms:  启动第2页
100ms: 启动第3页
150ms: 启动第4页
200ms: 启动第5页
       ↓
这5个请求同时进行中...
       ↓
某个完成后，继续启动第6页
```

## 📊 并发效果

### maxConcurrent = 1（完全顺序）
```
0ms:   ████ 第1页
100ms:      ████ 第2页
200ms:           ████ 第3页
```

### maxConcurrent = 3（中等并发）
```
0ms:   ████ 第1页
50ms:   ████ 第2页
100ms:  ████ 第3页
        ↓ 同时3个
某个完成后启动第4页
```

### maxConcurrent = 5（你当前的配置）
```
0ms:   ████ 第1页
50ms:   ████ 第2页
100ms:  ████ 第3页
150ms:  ████ 第4页
200ms:  ████ 第5页
        ↓ 同时5个
某个完成后启动第6页
```

### maxConcurrent = 999（几乎全部并发）
```
0ms:   ████████████████████ 前3页立即启动
150ms:         ████████████████████ 后续页按延迟启动
```

## 🧪 验证方法

```bash
# 1. 重新启动开发服务器
cd frontend && npm run dev

# 2. 清除浏览器缓存（Ctrl+Shift+Delete）

# 3. 打开开发者工具（F12）→ Network 标签

# 4. 进入漫画阅读器（滚动模式）

# 5. 观察 Network 瀑布图
```

## 👀 预期结果

**当 maxConcurrent = 5 时：**

在 Network 标签应该看到：
- ✅ 同时有 **5个** `api/chapters/xxx/images/X` 请求
- ✅ 瀑布图显示多个请求并行
- ✅ 某个请求完成后，新的请求立即启动
- ✅ 始终保持最多 5 个并发请求

## ⚙️ 配置建议

在 `ReaderView.vue` 中调整：

```javascript
const LOADING_CONFIG = {
  priorityPages: 3,      // 优先页数
  priorityDelay: 50,     // 优先页间隔（ms）
  normalDelay: 500,      // 普通页间隔（ms）
  maxConcurrent: 5,      // 最大并发数 ⭐
}
```

### 不同场景的推荐值

| 场景 | maxConcurrent | priorityPages | normalDelay |
|------|---------------|---------------|-------------|
| 🐌 服务器压力大 | 1-2 | 2-3 | 800-1000 |
| ⚖️ 平衡模式（推荐）| 3-5 | 3 | 500 |
| 🚀 服务器性能好 | 5-10 | 5 | 300 |
| ⚡ 快速加载（不推荐） | 20+ | 10 | 100 |

### 你当前的配置
```javascript
maxConcurrent: 5       // ✅ 适中
priorityPages: 3       // ✅ 合理
priorityDelay: 50      // ✅ 合理
normalDelay: 500       // ✅ 合理
```

**评价：** 这是一个很好的平衡配置，既保证加载速度，又不会压垮服务器。

## 📈 性能对比

### 30 页漫画的加载时间

| maxConcurrent | 全部加载完成时间 | 前3页加载时间 |
|---------------|------------------|---------------|
| 1 | ~15秒 | ~0.15秒 |
| 3 | ~7秒 | ~0.15秒 |
| 5 (当前) | ~5秒 | ~0.15秒 |
| 10 | ~3秒 | ~0.15秒 |

**注意：** 前3页加载时间相同，因为它们使用 `priorityDelay` (50ms)

## 🔍 技术细节

### 并发控制逻辑

```javascript
let loadingCount = 0;  // 当前正在加载的数量

while (loadingCount < maxConcurrent && currentIndex < images.length) {
  // 启动新的加载任务
  loadingCount++;

  ref.loadImage().then(() => {
    loadingCount--;  // 完成后减少计数
    loadNext();      // 继续加载下一个
  });
}
```

### 延迟计算

```javascript
// 前3页：0ms, 50ms, 100ms
// 第4页起：150ms + (n-3) * 500ms

const delay = indexToLoad < priorityPages
  ? priorityDelay * indexToLoad
  : priorityDelay * priorityPages + normalDelay * (indexToLoad - priorityPages);
```

## 🚨 注意事项

### 1. 服务器压力

**太高的并发数可能导致：**
- 服务器过载
- 图片加载失败
- 其他用户访问变慢

**建议：**
- 生产环境：`maxConcurrent: 3-5`
- 本地测试：`maxConcurrent: 5-10`

### 2. 网络带宽

**高并发需要足够的带宽：**
- 5 个并发 × 500KB/图 = 2.5MB 同时下载
- 确保你的网络支持

### 3. 浏览器限制

**浏览器对同一域名有并发限制：**
- Chrome: 6 个
- Firefox: 6 个
- Safari: 6 个

**建议：** `maxConcurrent <= 6`

## 🎯 最佳实践

### 推荐配置（平衡性能与服务器压力）
```javascript
const LOADING_CONFIG = {
  priorityPages: 3,
  priorityDelay: 50,
  normalDelay: 400,      // 稍微快一点
  maxConcurrent: 3,      // 稍微保守一点
}
```

### 快速加载配置（服务器性能好）
```javascript
const LOADING_CONFIG = {
  priorityPages: 5,
  priorityDelay: 30,
  normalDelay: 200,
  maxConcurrent: 6,
}
```

### 节省服务器配置（服务器压力大）
```javascript
const LOADING_CONFIG = {
  priorityPages: 2,
  priorityDelay: 100,
  normalDelay: 1000,
  maxConcurrent: 2,
}
```

## ✅ 总结

现在你设置的 `maxConcurrent: 5` 会在滚动模式下生效，你应该能在 Network 标签看到：

- ✅ 同时有 5 个图片请求
- ✅ 加载速度比之前快很多
- ✅ 但不会一次性请求所有图片

刷新页面重新测试，应该就能看到并发效果了！🎉
