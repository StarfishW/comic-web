# JMComic-Crawler-Python 项目分析

## 项目概述

| 属性 | 说明 |
|------|------|
| **项目名称** | JMComic-Crawler-Python (jmcomic) |
| **版本** | 2.6.13 |
| **作者** | hect0x7 |
| **许可证** | MIT |
| **语言** | Python 3.7+ |
| **用途** | JMComic (禁漫天堂) 漫画下载工具库，提供 API 调用和命令行两种使用方式 |

### 核心特性

- 绕过 Cloudflare 反爬机制
- 实现 JMComic APP API 加解密 (v1.6.3)
- 同时支持网页端 (HTML) 和移动端 (APP API) 两种客户端
- 多线程并发下载
- 可扩展的插件系统
- YAML 配置驱动

---

## 目录结构

```
jmcomic/
├── .github/                        # GitHub 配置
│   ├── ISSUE_TEMPLATE/             #   Issue 模板 (bug/feature/help)
│   ├── workflows/                  #   GitHub Actions 工作流
│   ├── release.py                  #   发布自动化脚本
│   └── release.yml                 #   发布配置
├── assets/
│   ├── docs/                       # MkDocs 文档源文件
│   │   ├── mkdocs.yml
│   │   └── sources/                #   API 文档、教程、图片
│   └── option/                     # 配置文件示例
│       ├── option_test_api.yml
│       ├── option_test_html.yml
│       ├── option_workflow_download.yml
│       └── option_workflow_export_favorites.yml
├── src/jmcomic/                    # 核心源码包
│   ├── __init__.py                 #   模块初始化与版本定义
│   ├── api.py                      #   公共 API 入口
│   ├── cl.py                       #   命令行接口 (JmcomicUI)
│   ├── jm_client_interface.py      #   客户端抽象接口与响应类
│   ├── jm_client_impl.py          #   客户端具体实现 (HTML / API)
│   ├── jm_config.py                #   全局模块配置注册表
│   ├── jm_downloader.py            #   下载器核心逻辑
│   ├── jm_entity.py                #   数据模型 (Album/Photo/Image)
│   ├── jm_exception.py             #   异常体系
│   ├── jm_option.py                #   配置对象 (JmOption)
│   ├── jm_plugin.py                #   插件系统及内置插件
│   └── jm_toolkit.py               #   工具类 (文本解析/图片处理)
├── tests/test_jmcomic/             # 单元测试
│   ├── test_jm_api.py
│   ├── test_jm_client.py
│   └── test_jm_custom.py
├── usage/                          # 使用示例
│   ├── workflow_download.py
│   └── workflow_export_favorites.py
├── setup.py                        # setuptools 配置
├── pyproject.toml                  # PEP 621 项目元数据
├── requirements-dev.txt            # 开发依赖
├── README.md                       # 项目说明 (中文)
└── LICENSE                         # MIT 许可证
```

---

## 架构设计

### 模块依赖链

```
config ← entity ← toolkit ← client ← option ← downloader ← api
```

### 分层架构

| 层级 | 模块 | 职责 |
|------|------|------|
| **API 层** | `api.py` | 对外公共接口 (`download_album`, `download_photo`, `download_batch`) |
| **CLI 层** | `cl.py` | 命令行交互 (`JmcomicUI`) |
| **下载层** | `jm_downloader.py` | 下载编排、成功/失败追踪、生命周期回调 |
| **配置层** | `jm_option.py` | 配置对象 (`JmOption`)、缓存策略、路径规则、插件集成 |
| **客户端层** | `jm_client_impl.py` | HTTP 通信、域名管理、响应处理 |
| **工具层** | `jm_toolkit.py` | 文本解析、正则匹配、图片解密与格式转换 |
| **配置注册层** | `jm_config.py` | 全局组件注册 (客户端、插件、异常监听) |
| **数据模型层** | `jm_entity.py` | Album / Photo / Image 实体 |

### 数据模型

```
JmBaseEntity
  └── DetailEntity
        ├── JmAlbumDetail (本子/专辑)
        │   ├── id, name, author, description
        │   ├── page_count, tags, views, likes
        │   └── photos[] → JmPhotoDetail
        └── JmPhotoDetail (章节/话)
            ├── id, name, album_id, index
            └── images[] → JmImageDetail
                             ├── id, url, img_url
                             ├── scramble_id
                             └── download_url
```

---

## 客户端实现

### 双客户端架构

| 客户端 | 类名 | 方式 | 特点 |
|--------|------|------|------|
| **网页端** | `JmHtmlClient` | HTML 解析 | 正则提取数据，处理 Cloudflare 保护 |
| **APP 端** | `JmApiClient` | 加密 API | AES 加解密，模拟移动端请求 |

**公共基类** `AbstractJmClient` 提供：
- 域名管理与自动切换
- curl-cffi HTTP 请求 (TLS 指纹模拟)
- 可配置的重试机制
- 响应缓存

### 响应类体系

| 类 | 用途 |
|----|------|
| `JmResp` | 基础响应封装 |
| `JmImageResp` | 图片响应，支持解密 |
| `JmJsonResp` | JSON 数据解析 |
| `JmApiResp` | APP API 专用响应 |

---

## 插件系统

基类 `JmOptionPlugin`，通过 YAML 配置启用。内置插件包括：

| 插件 | 功能 |
|------|------|
| 压缩插件 | 将下载内容打包为 ZIP |
| PDF 转换 | 将图片合并为 PDF |
| 长图拼接 | 将多页拼接为长图 |
| 重复检测 | 避免重复下载 |
| 文件复制 | 下载后复制到指定位置 |
| Web Viewer | 提供网页浏览服务 |
| 邮件通知 | 下载完成后 QQ 邮箱通知 |

---

## 依赖说明

### 核心依赖

| 包 | 用途 |
|----|------|
| `commonx` (>=0.6.38) | 通用工具与线程管理 |
| `curl-cffi` | 带 TLS 指纹的 HTTP 客户端 (绕过 Cloudflare) |
| `pillow` | 图片处理与格式转换 |
| `pycryptodome` | APP API 的 AES 加解密 |
| `pyyaml` | YAML 配置文件解析 |

### 开发依赖

| 包 | 用途 |
|----|------|
| `psutil` | 系统监控 |
| `requests` | 备用 HTTP 库 |
| `plugin_jm_server` | 可选服务端插件 |
| `zhconv` | 简繁体中文转换 |

---

## 使用方式

### 命令行

```bash
# 安装
pip install jmcomic

# 下载本子
jmcomic 123

# 下载本子 + 指定章节
jmcomic 123 p456

# 使用配置文件
jmcomic 123 --option="D:/config.yml"
```

### 编程调用

```python
import jmcomic

# 下载整本
jmcomic.download_album(album_id, option)

# 下载单章
jmcomic.download_photo(photo_id, option)

# 批量下载
jmcomic.download_batch(api, id_list, option)

# 从文件加载配置
option = jmcomic.create_option_by_file('config.yml')
```

**入口点定义** (`setup.py`):

```python
entry_points = {
    'console_scripts': [
        'jmcomic = jmcomic.cl:main'
    ]
}
```

---

## CI/CD 工作流

| 工作流文件 | 用途 |
|-----------|------|
| `download.yml` | 通过 GitHub 界面触发下载 |
| `download_dispatch.yml` | 手动 Dispatch 下载 |
| `export_favorites.yml` | 导出收藏夹 |
| `test_api.yml` | API 客户端功能测试 |
| `test_html.yml` | HTML 客户端功能测试 |
| `release.yml` | 发布自动化 |
| `release_auto.yml` | 自动发布流水线 |

---

## 核心源码统计

| 文件 | 行数 | 说明 |
|------|------|------|
| `jm_plugin.py` | 1333 | 插件系统 (最大文件) |
| `jm_client_impl.py` | 1207 | 客户端实现 |
| `jm_toolkit.py` | 1019 | 工具类 |
| `jm_entity.py` | 697 | 数据模型 |
| `jm_option.py` | 665 | 配置对象 |
| `jm_client_interface.py` | 631 | 客户端接口 |
| `jm_config.py` | 511 | 模块配置 |
| `jm_downloader.py` | 350 | 下载器 |
| `jm_exception.py` | 191 | 异常体系 |
| `api.py` | 131 | 公共 API |
| `cl.py` | 121 | 命令行 |
| **合计** | **~6,885** | |
