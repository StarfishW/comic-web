/**
 * 图片加载队列管理器
 * 用于管理图片的顺序加载和并发控制
 */

class ImageLoader {
  constructor(options = {}) {
    this.maxConcurrent = options.maxConcurrent || 3 // 最大并发数
    this.queue = [] // 待加载队列
    this.loading = new Set() // 正在加载的图片
    this.loaded = new Set() // 已加载的图片
    this.sequential = options.sequential || false // 是否顺序加载
  }

  /**
   * 添加图片到加载队列
   * @param {string} src - 图片地址
   * @param {number} priority - 优先级（数字越小越优先）
   * @param {Function} onLoad - 加载完成回调
   * @param {Function} onError - 加载失败回调
   */
  add(src, priority = 0, onLoad, onError) {
    if (this.loaded.has(src) || this.loading.has(src)) {
      return Promise.resolve()
    }

    return new Promise((resolve, reject) => {
      this.queue.push({
        src,
        priority,
        onLoad: () => {
          onLoad?.()
          resolve()
        },
        onError: (err) => {
          onError?.(err)
          reject(err)
        },
      })

      // 按优先级排序
      this.queue.sort((a, b) => a.priority - b.priority)

      // 开始加载
      this.processQueue()
    })
  }

  /**
   * 处理加载队列
   */
  processQueue() {
    // 顺序加载模式：一次只加载一张
    if (this.sequential) {
      if (this.loading.size === 0 && this.queue.length > 0) {
        const item = this.queue.shift()
        this.loadImage(item)
      }
      return
    }

    // 并发加载模式：根据 maxConcurrent 控制并发数
    while (this.loading.size < this.maxConcurrent && this.queue.length > 0) {
      const item = this.queue.shift()
      this.loadImage(item)
    }
  }

  /**
   * 加载单张图片
   */
  loadImage(item) {
    const { src, onLoad, onError } = item

    this.loading.add(src)

    const img = new Image()

    img.onload = () => {
      this.loading.delete(src)
      this.loaded.add(src)
      onLoad?.()
      // 继续处理队列
      this.processQueue()
    }

    img.onerror = (err) => {
      this.loading.delete(src)
      onError?.(err)
      // 继续处理队列
      this.processQueue()
    }

    img.src = src
  }

  /**
   * 预加载图片列表
   * @param {Array<string>} urls - 图片地址列表
   * @param {boolean} sequential - 是否顺序加载
   */
  preloadImages(urls, sequential = false) {
    const oldSequential = this.sequential
    this.sequential = sequential

    const promises = urls.map((url, index) => {
      return this.add(url, index)
    })

    return Promise.allSettled(promises).finally(() => {
      this.sequential = oldSequential
    })
  }

  /**
   * 清空队列
   */
  clear() {
    this.queue = []
    this.loading.clear()
    this.loaded.clear()
  }

  /**
   * 重置队列（保留已加载记录）
   */
  reset() {
    this.queue = []
    this.loading.clear()
  }

  /**
   * 获取加载进度
   */
  getProgress() {
    const total = this.queue.length + this.loading.size + this.loaded.size
    const loaded = this.loaded.size
    return total > 0 ? (loaded / total) * 100 : 0
  }
}

// 导出单例
export const globalImageLoader = new ImageLoader({
  maxConcurrent: 3,
  sequential: false,
})

export default ImageLoader
