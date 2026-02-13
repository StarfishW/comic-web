# 图片懒加载与顺序加载功能

## 功能概述

本项目已实现高级的图片懒加载和顺序加载功能，用于优化图片加载性能和用户体验。

## 核心组件

### 1. LazyImage 组件 (`src/components/LazyImage.vue`)

一个智能的图片懒加载组件，提供以下功能：

**特性：**
- 使用 Intersection Observer API 监听图片可见性
- 支持占位图显示
- 加载状态指示（加载中、已加载、加载失败）
- 失败后可点击重试
- 平滑淡入动画
- 可配置预加载距离（默认提前 100px）

**Props：**
- `src` (String, 必填) - 图片地址
- `alt` (String) - 图片描述
- `priority` (Number) - 优先级，数字越小越优先
- `sequential` (Boolean) - 是否需要顺序加载
- `placeholder` (String) - 占位图地址

**事件：**
- `visible` - 当图片进入可视区域时触发

**使用示例：**
```vue
<LazyImage
  :src="imageUrl"
  alt="图片描述"
  :sequential="true"
  @visible="handleImageVisible"
/>
```

### 2. ImageLoader 工具类 (`src/utils/imageLoader.js`)

图片加载队列管理器，负责控制图片的加载顺序和并发数。

**特性：**
- 支持顺序加载模式（一张接一张）
- 支持并发加载模式（可配置最大并发数）
- 优先级队列（按 priority 排序）
- 加载进度跟踪
- 已加载图片记录（避免重复加载）

**API：**

```javascript
import ImageLoader from '@/utils/imageLoader'

// 创建实例
const loader = new ImageLoader({
  maxConcurrent: 3,    // 最大并发数
  sequential: false    // 是否顺序加载
})

// 添加单张图片到队列
loader.add(imageUrl, priority, onLoad, onError)

// 预加载图片列表
loader.preloadImages(urls, sequential)

// 获取加载进度
const progress = loader.getProgress() // 返回 0-100

// 清空队列
loader.clear()
```

## 应用场景

### 场景 1: 漫画阅读器 - 顺序加载

在 `ReaderView.vue` 的滚动模式下，图片按照从上到下的顺序依次加载：

**工作流程：**
1. 页面加载时获取章节信息
2. 渲染所有图片占位符
3. 从第一张开始顺序加载图片
4. 每张图片加载完成后延迟 100ms 加载下一张
5. 显示加载进度

**优点：**
- 节省带宽（用户可能不会滚动到底部）
- 防止服务器过载（控制并发请求）
- 提供流畅的加载体验

### 场景 2: 漫画阅读器 - 翻页模式预加载

在翻页模式下，智能预加载当前页和相邻页：

**预加载策略：**
- 当前页（优先级 0）
- 下一页（优先级 1）
- 上一页（优先级 2）

**触发时机：**
- 切换到翻页模式时
- 翻页时自动预加载新的相邻页

### 场景 3: 列表页 - 懒加载

在 `HomeView`, `SearchView`, `RankingView` 等列表页，封面图片使用懒加载：

**行为：**
- 只加载可见区域的图片
- 滚动时自动加载进入视口的图片
- 提前 100px 开始加载（无缝体验）

## 性能优化

### 1. 减少初始加载时间
- 只加载可见区域图片
- 延迟加载屏幕外图片

### 2. 减少带宽消耗
- 用户未滚动到的图片不加载
- 顺序加载防止一次性请求过多

### 3. 改善用户体验
- 占位符和加载动画
- 平滑的淡入效果
- 失败重试功能
- 骨架屏预加载效果

### 4. 并发控制
- 最大并发数限制（默认 2-3 个）
- 防止浏览器连接数耗尽
- 减轻服务器压力

## 配置选项

### 调整并发数

在 `ReaderView.vue` 中：

```javascript
const imageLoader = new ImageLoader({
  maxConcurrent: 2,    // 调整此值控制并发数
  sequential: true     // 是否顺序加载
})
```

**建议值：**
- 顺序模式：1（严格顺序）
- 并发模式：2-5（平衡性能与服务器压力）

### 调整预加载距离

在 `LazyImage.vue` 的 `setupObserver` 方法中：

```javascript
observer = new IntersectionObserver(
  (entries) => { /* ... */ },
  {
    rootMargin: '100px',  // 调整此值（如 '200px'）
    threshold: 0.01,
  }
)
```

## 技术细节

### Intersection Observer API

使用现代浏览器的原生 API 监听元素可见性：

**优点：**
- 性能优异（不依赖 scroll 事件）
- 自动处理节流
- 支持精确的可见性检测

**兼容性：**
- Chrome 51+
- Firefox 55+
- Safari 12.1+
- Edge 15+

### 队列管理算法

1. **优先级队列**：使用数组 + 排序实现
2. **并发控制**：使用 Set 跟踪正在加载的图片
3. **已加载记录**：使用 Set 防止重复加载

### 内存管理

- 加载完成后自动停止 Observer 观察
- 组件卸载时清理 Observer
- 路由切换时清空加载队列

## 浏览器兼容性

- **现代浏览器**：完全支持
- **旧版浏览器**：降级到原生 `loading="lazy"` 属性
- **不支持懒加载的浏览器**：图片立即加载（功能降级）

## 故障处理

### 图片加载失败

- 显示错误图标和提示
- 点击可重试加载
- 失败后继续加载下一张（不阻塞队列）

### 网络慢速

- 显示加载中状态
- 骨架屏占位
- 超时后显示错误提示

## 未来改进方向

1. **响应式图片**：根据设备分辨率加载不同尺寸
2. **IndexedDB 缓存**：缓存已加载图片到本地
3. **预测式预加载**：根据用户行为预测并预加载
4. **WebP 格式支持**：在支持的浏览器使用 WebP
5. **虚拟滚动**：大量图片时使用虚拟列表

## 调试

### 查看加载进度

在控制台中：

```javascript
// 获取全局加载器实例
import { globalImageLoader } from '@/utils/imageLoader'

// 查看进度
console.log(globalImageLoader.getProgress())

// 查看队列状态
console.log({
  queue: globalImageLoader.queue.length,
  loading: globalImageLoader.loading.size,
  loaded: globalImageLoader.loaded.size
})
```

### 模拟慢速网络

Chrome DevTools → Network → Throttling → Slow 3G

观察懒加载和顺序加载的效果。

## 总结

通过 LazyImage 组件和 ImageLoader 工具类，实现了：

✅ 按需加载（只加载可见区域）
✅ 顺序加载（避免并发过多）
✅ 优先级控制（重要图片先加载）
✅ 预加载策略（智能预测）
✅ 加载状态反馈（用户友好）
✅ 失败重试机制（提高成功率）
✅ 性能优化（减少带宽和服务器压力）

这些功能显著提升了图片密集型应用的性能和用户体验。
