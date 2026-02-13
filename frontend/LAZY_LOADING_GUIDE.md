# 图片懒加载使用快速指南

## 已实现的功能

✅ **自动懒加载** - 所有图片组件已自动应用懒加载
✅ **顺序加载** - 阅读器滚动模式下图片按顺序加载
✅ **智能预加载** - 翻页模式下预加载相邻页面
✅ **加载状态显示** - 占位符、加载动画、错误重试

## 受影响的页面

### 1. 漫画阅读器 (ReaderView)

**滚动模式：**
- 图片从上到下按顺序加载
- 每张图片间隔 100ms 加载
- 显示加载进度（可在代码中启用）

**翻页模式：**
- 自动预加载当前页、上一页、下一页
- 翻页时立即显示（已预加载）

### 2. 列表页 (HomeView, SearchView, RankingView, FavoritesView)

- 只加载可见区域的封面图片
- 滚动时自动加载新图片
- 提前 100px 开始预加载（无缝体验）

### 3. 详情页 (ComicDetailView)

- 大封面图片懒加载
- 显示加载状态

## 自定义配置

### 修改并发数

编辑 `frontend/src/views/ReaderView.vue`:

```javascript
const imageLoader = new ImageLoader({
  maxConcurrent: 3,    // 改为 1-5 之间的值
  sequential: true
})
```

### 修改预加载距离

编辑 `frontend/src/components/LazyImage.vue`:

```javascript
observer = new IntersectionObserver(
  (entries) => { /* ... */ },
  {
    rootMargin: '200px',  // 改为更大的值（如 200px, 300px）
    threshold: 0.01,
  }
)
```

### 禁用顺序加载

编辑 `frontend/src/views/ReaderView.vue`:

```vue
<!-- 将 :sequential="true" 改为 false -->
<LazyImage
  :src="getImageSrc(i)"
  :sequential="false"  <!-- 改为 false -->
  ...
/>
```

## 测试懒加载效果

1. 打开浏览器开发者工具 (F12)
2. 切换到 Network 标签
3. 启用网络节流：Throttling → Slow 3G
4. 打开漫画阅读器
5. 观察图片按顺序加载

## 性能对比

### 之前（普通加载）：
- 所有图片同时请求
- 初始加载时间长
- 可能导致服务器过载

### 现在（智能加载）：
- 只加载可见图片
- 顺序加载控制并发
- 初始加载时间短
- 服务器压力小

## 常见问题

**Q: 为什么第一张图片加载比较慢？**
A: 第一张图片需要等待章节信息加载完成。可以在 `fetchChapter` 中添加预加载逻辑。

**Q: 如何显示加载进度条？**
A: 在 `ReaderView.vue` 的 toolbar 中添加：
```vue
<div v-if="loadingProgress > 0 && loadingProgress < 100" class="progress-bar">
  <div class="progress-fill" :style="{ width: loadingProgress + '%' }"></div>
</div>
```

**Q: 如何禁用懒加载？**
A: 将所有 `<LazyImage>` 替换回 `<img>` 标签。

## 更多信息

详细文档请查看：`frontend/IMAGE_LOADING.md`
