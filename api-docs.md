# JMComic API 接口文档

> 后端基于 FastAPI，端口 `8000`，前端通过 Vite 代理 `/api` 转发。

---

## 接口总览

共 **17** 个接口，分为 7 个模块：

| # | 模块 | 方法 | 路径 | 说明 |
|---|------|------|------|------|
| 1 | 浏览 | GET | `/api/comics` | 漫画列表（分类筛选） |
| 2 | 排行 | GET | `/api/ranking/{ranking_type}` | 排行榜 |
| 3 | 搜索 | GET | `/api/search` | 搜索漫画 |
| 4 | 详情 | GET | `/api/comics/{album_id}` | 漫画详情 |
| 5 | 详情 | GET | `/api/comics/{album_id}/cover` | 漫画封面代理 |
| 6 | 章节 | GET | `/api/chapters/{photo_id}` | 章节详情（图片列表） |
| 7 | 章节 | GET | `/api/chapters/{photo_id}/images/{index}` | 漫画图片（解密后） |
| 8 | 认证 | POST | `/api/auth/login` | 用户登录 |
| 9 | 收藏 | GET | `/api/favorites` | 获取收藏列表 |
| 10 | 收藏 | POST | `/api/favorites` | 添加收藏 |
| 11 | 评论 | POST | `/api/comments` | 发表评论/回复 |
| 12 | 域名 | GET | `/api/domains` | 获取当前域名列表 |
| 13 | 域名 | PUT | `/api/domains` | 设置域名列表 |
| 14 | 域名 | GET | `/api/domains/discover` | 发现所有可用域名 |
| 15 | 域名 | GET | `/api/domains/ping` | 检测所有域名延迟 |
| 16 | 域名 | POST | `/api/domains/switch` | 切换到指定域名 |

> 注：第 7 个接口返回二进制图片，其余返回 JSON。

---

## 1. 浏览 / 分类

### GET `/api/comics`

漫画列表，支持分类、排序、时间筛选。

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page` | int | `1` | 页码（>=1） |
| `order_by` | string | `"mr"` | 排序：`mr`=最新, `mv`=最多观看, `mp`=最多图片, `tf`=最多喜欢 |
| `time` | string | `"a"` | 时间范围：`a`=全部, `m`=月, `w`=周, `t`=今天 |
| `category` | string | `"0"` | 分类：`0`=全部, `doujin`=同人, `single`=单本, `short`=短篇, `hanman`=韩漫, `meiman`=美漫, `doujin_cosplay`=Cosplay, `3D`, `english_site`=英文站, `another`=其他 |

**返回：**

```json
{
  "items": [
    {
      "id": "441923",
      "title": "漫画标题",
      "tags": ["标签1", "标签2"],
      "author": "作者",
      "cover": "https://..."
    }
  ],
  "total": 1000,
  "page_count": 50
}
```

---

## 2. 排行榜

### GET `/api/ranking/{ranking_type}`

获取排行榜数据。

**路径参数：**

| 参数 | 说明 |
|------|------|
| `ranking_type` | `all`=总榜, `day`=日榜, `week`=周榜, `month`=月榜 |

**查询参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page` | int | `1` | 页码 |
| `category` | string | `"0"` | 分类（同上） |

**返回：** 同 `/api/comics`

---

## 3. 搜索

### GET `/api/search`

搜索漫画。

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `q` | string | 必填 | 搜索关键词 |
| `page` | int | `1` | 页码 |
| `main_tag` | int | `0` | 搜索类型：`0`=综合, `1`=作品, `2`=作者, `3`=标签, `4`=角色 |
| `order_by` | string | `"mr"` | 排序（同上） |
| `time` | string | `"a"` | 时间范围（同上） |
| `category` | string | `"0"` | 分类（同上） |

**返回：** 同 `/api/comics`

---

## 4. 漫画详情

### GET `/api/comics/{album_id}`

获取漫画完整详情。

**路径参数：**

| 参数 | 说明 |
|------|------|
| `album_id` | 漫画 ID |

**返回：**

```json
{
  "id": "441923",
  "title": "漫画标题",
  "author": "作者",
  "authors": ["作者1", "作者2"],
  "description": "简介",
  "tags": ["标签"],
  "actors": ["角色"],
  "works": ["作品系列"],
  "likes": "1234",
  "views": "56789",
  "comment_count": 100,
  "pub_date": "2024-01-01",
  "update_date": "2024-06-01",
  "page_count": 20,
  "episodes": [
    { "id": "441923", "sort": 1, "title": "第1话" }
  ],
  "cover": "https://...",
  "related_list": [
    { "id": "333718", "name": "推荐漫画", "author": "作者", "description": "", "image": "" }
  ]
}
```

---

## 5. 漫画封面

### GET `/api/comics/{album_id}/cover`

代理获取漫画封面图片，返回二进制图片数据。

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `size` | string | `""` | 封面尺寸（可选） |

**返回：** `image/jpeg` | `image/png` | `image/webp`

---

## 6. 章节详情

### GET `/api/chapters/{photo_id}`

获取章节信息及图片列表。

**路径参数：**

| 参数 | 说明 |
|------|------|
| `photo_id` | 章节 ID |

**返回：**

```json
{
  "id": "441923",
  "title": "第1话",
  "album_id": "441920",
  "album_index": 0,
  "page_count": 25,
  "scramble_id": "220980",
  "tags": [],
  "images": [
    { "index": 0, "filename": "00001.jpg", "url": "/api/chapters/441923/images/0" }
  ]
}
```

---

## 7. 漫画图片

### GET `/api/chapters/{photo_id}/images/{index}`

获取解密后的漫画图片。服务端自动处理图片分段解密。

**路径参数：**

| 参数 | 说明 |
|------|------|
| `photo_id` | 章节 ID |
| `index` | 图片索引（从 0 开始） |

**返回：** `image/jpeg` | `image/png` | `image/gif` | `image/webp`

---

## 8. 用户登录

### POST `/api/auth/login`

**请求体：**

```json
{
  "username": "用户名",
  "password": "密码"
}
```

**返回：**

```json
{ "ok": true, "message": "Login successful" }
```

**错误：** 401（登录失败）

---

## 9. 获取收藏

### GET `/api/favorites`

获取用户收藏的漫画列表（需先登录）。

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page` | int | `1` | 页码 |
| `folder_id` | string | `"0"` | 收藏夹 ID，`0`=全部 |
| `order_by` | string | `"mr"` | 排序 |

**返回：**

```json
{
  "items": [ ... ],
  "total": 100,
  "page_count": 5,
  "folders": [
    { "id": "0", "name": "全部" },
    { "id": "1", "name": "自定义收藏夹" }
  ]
}
```

---

## 10. 添加收藏

### POST `/api/favorites`

**请求体：**

```json
{
  "album_id": "441923",
  "folder_id": "0"
}
```

**返回：** `{ "ok": true }`

---

## 11. 发表评论

### POST `/api/comments`

**请求体：**

```json
{
  "video_id": "441923",
  "comment": "评论内容",
  "comment_id": null
}
```

| 字段 | 说明 |
|------|------|
| `video_id` | 漫画 ID |
| `comment` | 评论内容 |
| `comment_id` | 回复的评论 ID（为 null 则为新评论） |

**返回：** `{ "ok": true }`

---

## 12. 获取当前域名

### GET `/api/domains`

获取客户端当前使用的域名列表。

**返回：**

```json
{
  "domains": ["www.cdnaspa.vip", "www.cdnplaystation6.vip"]
}
```

---

## 13. 设置域名

### PUT `/api/domains`

手动设置域名列表。

**请求体：**

```json
{
  "domains": ["domain1.com", "domain2.com"]
}
```

**返回：**

```json
{ "ok": true, "domains": ["domain1.com", "domain2.com"] }
```

---

## 14. 发现域名

### GET `/api/domains/discover`

自动发现所有可用域名。

**返回：**

```json
{
  "current": "18comic.vip",
  "available": ["18comic.vip", "18comic.org", "..."]
}
```

---

## 15. 域名延迟检测

### GET `/api/domains/ping`

并发检测所有已知域名的延迟，使用 `curl_cffi` 模拟 Chrome TLS 指纹。

**返回：**

```json
{
  "current": ["www.cdnaspa.vip"],
  "results": [
    { "domain": "www.cdnaspa.vip", "latency": 156, "status": "ok" },
    { "domain": "www.cdnaspa.club", "latency": 320, "status": "ok" },
    { "domain": "example.com", "latency": -1, "status": "error", "error": "timeout" }
  ]
}
```

> `latency` 单位为毫秒（ms），`-1` 表示超时/不可用。结果按延迟从低到高排序。

---

## 16. 切换域名

### POST `/api/domains/switch`

切换到指定域名（将其置为域名列表首位）。

**请求体：**

```json
{
  "domain": "www.cdnaspa.vip"
}
```

**返回：**

```json
{ "ok": true, "domains": ["www.cdnaspa.vip", "..."] }
```

---

## 通用说明

### 分类值对照表

| 值 | 说明 |
|----|------|
| `0` | 全部 |
| `doujin` | 同人 |
| `single` | 单本 |
| `short` | 短篇 |
| `hanman` | 韩漫 |
| `meiman` | 美漫 |
| `doujin_cosplay` | Cosplay |
| `3D` | 3D |
| `english_site` | 英文站 |
| `another` | 其他 |

### 排序值对照表

| 值 | 说明 |
|----|------|
| `mr` | 最新 |
| `mv` | 最多观看 |
| `mp` | 最多图片 |
| `tf` | 最多喜欢 |

### 错误格式

所有接口错误返回 HTTP 状态码 + JSON：

```json
{ "detail": "错误信息" }
```

| 状态码 | 说明 |
|--------|------|
| 400 | 参数错误 |
| 401 | 认证失败 |
| 404 | 资源不存在 |
| 500 | 服务端错误 |
