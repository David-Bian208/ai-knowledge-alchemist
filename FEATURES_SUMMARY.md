# 知识炼金术 Agent - 功能总结文档

> 版本：V1.0  
> 更新日期：2026-05-17  
> 仓库：`ai-knowledge-alchemist`

---

## 📋 一、项目概述

知识炼金术 Agent 是一个**智能素材采集与处理系统**，用于从全网多个平台自动抓取内容，经过分类、评分、提取后，转化为结构化的知识库资产。

### 核心定位
- **输入**：URL链接、关键词、本地文件
- **处理**：自动抓取 → LLM分类 → 星级评分 → 观点提取
- **输出**：结构化Markdown文件 + SQLite数据库 + Obsidian知识库同步

---

## 🎯 二、核心功能

### 1. 智能抓取层（Smart Crawler）

**功能**：自动识别URL类型，路由到最合适的抓取器

| URL类型 | 路由目标 | 支持平台 |
|---------|----------|----------|
| 国内媒体 | MediaCrawler | 小红书、抖音、知乎、贴吧、B站、微博 |
| 国际社交媒体 | gallery-dl | Twitter/X、Instagram、Pixiv、Reddit、Flickr等267站 |
| 微信文章 | WeChatCrawler | 微信公众号（mp.weixin.qq.com） |
| 普通网页 | trafilatura | 所有静态网页 |

### 2. 微信反爬机制（三级降级）

```
方式1：trafilatura直接抓取（部分文章可用）
   ↓ 失败
方式2：Playwright浏览器模拟（绕过JS渲染/验证码）
   ↓ 失败
方式3：搜狗微信搜索备选（获取缓存页面）
```

### 3. 内容处理层（Processor）

**LLM驱动的五维处理流程**：

| 步骤 | 功能 | 输出 |
|------|------|------|
| 预筛 | 判断内容是否与主题相关 | 相关/无关 |
| 分类 | 时间维度 + 内容维度 + 场景维度 | 三维标签 |
| 评分 | 1-5星评级 | 星级 + 质量分 |
| 提取 | 核心观点、案例、金句 | 结构化内容 |
| 关联 | 双向链接到已有素材 | 关联关系 |

**分类维度**：
- **时间维度**：即时热点 / 近期趋势 / 经典常青
- **内容维度**：方法论 / 认知 / 案例 / 数据 / 软件工具 / 资源
- **场景维度**：脚本素材 / 竞品分析 / 避坑指南 / 金句库

### 4. 存储层（Storage）

- **SQLite数据库**：结构化存储所有素材元数据
- **本地Markdown文件**：按分类目录保存处理后的内容
- **Obsidian同步**：通过MCP协议同步到知识库

### 5. 定时调度（Scheduler）

- 支持RSS订阅定时抓取
- 支持Webhook通知
- 支持任务队列管理

---

## 🔧 三、技术架构

### 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| **爬虫层** | trafilatura | 静态网页正文提取 |
|  | gallery-dl | 社交媒体图片/内容抓取（267+站点） |
|  | Playwright | 动态页面渲染、反爬绕过 |
|  | MediaCrawler | 国内平台专用（小红书/抖音等） |
| **AI层** | OpenAI API | LLM分类、评分、提取 |
|  | LangChain | 重试机制、JSON解析 |
| **存储层** | SQLite | 结构化数据存储 |
|  | Markdown | 本地文件存储 |
| **同步层** | MCP协议 | Obsidian知识库同步 |
| **调度层** | schedule | 定时任务 |
| **前端** | Gradio | Web交互界面 |

### 项目结构

```
ai-knowledge-alchemist/
├── src/
│   ├── __init__.py
│   ├── crawler.py           # 智能路由爬虫（主入口）
│   ├── gallery_crawler.py   # gallery-dl封装
│   ├── media_crawler.py     # MediaCrawler轻量适配器
│   ├── wechat_crawler.py    # 微信爬虫（三级降级）
│   ├── processor.py         # 内容分类/评分/提取
│   ├── storage.py           # SQLite + 文件存储
│   ├── scheduler.py         # 定时任务调度
│   ├── mcp_client.py        # Obsidian同步
│   └── rss_fetcher.py       # RSS订阅
├── third_party/
│   └── MediaCrawler/        # 原始MediaCrawler项目（参考）
├── main.py                  # CLI入口
├── app.py                   # Gradio Web界面
├── requirements.txt         # 依赖列表
└── config/
    └── config.yaml          # 配置文件
```

---

## 🚀 四、使用方式

### CLI命令行模式

```bash
# 处理单个URL
python main.py --url "https://example.com/article"

# 批量处理URL文件
python main.py --batch urls.txt

# 生成报告
python main.py --report

# 查看已处理素材
python main.py --list
```

### Python代码调用

```python
# 智能路由爬虫
from src.crawler import WebCrawler

crawler = WebCrawler()

# 自动识别平台并抓取
result = crawler.fetch("https://www.xiaohongshu.com/explore/123")
result = crawler.fetch("https://twitter.com/user/status/123")
result = crawler.fetch("https://www.example.com/article")

# 微信文章专用
from src.wechat_crawler import WeChatCrawler
wechat = WeChatCrawler()
result = wechat.fetch_wechat_article("https://mp.weixin.qq.com/s/xxx")

# 内容处理
from src.processor import ContentProcessor
processor = ContentProcessor()
processed = processor.process(result)

# 存储
from src.storage import Storage
storage = Storage()
storage.save(processed)
```

### Web界面（Gradio）

启动后提供以下功能：
1. URL输入框 - 支持多个URL
2. 关键词搜索配置
3. 本地MD文件路径指定
4. API配置（OpenAI Key等）
5. 代理配置
6. 保存路径配置
7. 处理进度显示
8. 结果预览

---

## 📊 五、支持平台汇总

### 国内平台

| 平台 | 抓取器 | 支持内容 | 反爬能力 |
|------|--------|----------|----------|
| 小红书 | MediaCrawler | 笔记图文 | Playwright绕过 |
| 抖音 | MediaCrawler | 视频/图文 | Playwright绕过 |
| 知乎 | MediaCrawler | 问答/文章 | Playwright绕过 |
| 百度贴吧 | MediaCrawler | 帖子 | Playwright绕过 |
| B站 | MediaCrawler/gallery-dl | 视频/专栏 | 中等 |
| 微博 | MediaCrawler/gallery-dl | 博文/图片 | 中等 |
| 微信公众号 | WeChatCrawler | 文章 | 三级降级 |

### 国际平台

| 平台 | 抓取器 | 支持内容 |
|------|--------|----------|
| Twitter/X | gallery-dl | 推文/图片/视频 |
| Instagram | gallery-dl | 帖子/图片 |
| Pixiv | gallery-dl | 插画 |
| Reddit | gallery-dl | 帖子/评论 |
| Flickr | gallery-dl | 照片 |
| Tumblr | gallery-dl | 博文/图片 |
| DeviantArt | gallery-dl | 艺术作品 |
| ArtStation | gallery-dl | 艺术作品 |
| Pinterest | gallery-dl | 图片 |

---

## 🔐 六、反爬策略汇总

### 微信文章
- **方式1**：trafilatura直接抓取（快速尝试）
- **方式2**：Playwright浏览器模拟（注入反检测脚本）
- **方式3**：搜狗微信搜索（获取缓存页面）

### 小红书/抖音
- **Playwright**：模拟真实浏览器行为
- **反检测脚本**：隐藏webdriver属性
- **鼠标模拟**：滚动页面触发懒加载
- **等待策略**：networkidle + 额外等待

### 通用策略
- **User-Agent轮换**：模拟不同浏览器
- **请求头伪装**：完整的Accept/Accept-Language
- **延迟控制**：避免频繁请求
- **降级策略**：主方案失败自动切换备用方案

---

## ⚙️ 七、配置说明

### 环境变量

```bash
# OpenAI API配置
OPENAI_API_KEY=your_key_here
OPENAI_BASE_URL=https://api.openai.com/v1

# RSSHub配置（可选）
RSSHUB_URL=http://your-rsshub.example.com

# 代理配置（可选）
HTTP_PROXY=http://proxy.example.com:8080
HTTPS_PROXY=http://proxy.example.com:8080
```

### config.yaml

```yaml
# LLM配置
llm:
  model: "deepseek-chat"
  temperature: 0.1
  max_tokens: 2000
  base_url: "https://api.deepseek.com/v1"

# 存储配置
storage:
  db_path: "./data/materials.db"
  save_dir: "./materials"

# 抓取器配置
crawler:
  use_gallery_dl: true
  use_media_crawler: true
  gallery_dl_save_dir: "./gallery_dl_output"
```

---

## 📈 八、工作流程图

```
用户输入URL/关键词/文件
        ↓
   智能路由检测
        ↓
┌───────┼───────────┐
↓       ↓           ↓
MediaCrawler  gallery-dl  WeChatCrawler
(国内平台)   (国际社交)   (微信文章)
        ↓           ↓           ↓
        └───────┬───┘           ↓
                ↓               ↓
           trafilatura ←── 降级策略
           (普通网页)
                ↓
        统一输出格式
        (metadata + markdown)
                ↓
        ┌───────┴───────┐
        ↓               ↓
   LLM预筛          LLM分类
   (相关/无关)     (三维标签)
        ↓               ↓
    LLM评分         LLM提取
   (1-5星)        (观点/案例/金句)
        ↓               ↓
    ┌───┴───────────────┤
    ↓                   ↓
SQLite数据库      Markdown文件
    ↓                   ↓
    └───────┬───────────┘
            ↓
    Obsidian同步
    (MCP协议)
```

---

## 🛠️ 九、开发规范

### 代码风格
- Python 3.10+
- 使用type hints
- 函数/类有完整docstring
- 日志使用logging模块

### 依赖管理
```bash
pip install -r requirements.txt
python -m playwright install chromium  # 安装浏览器驱动
```

### 测试
```bash
# 测试智能路由
python test_full_crawler.py

# 测试微信爬虫
python test_wechat.py

# 测试gallery-dl
python test_gallery_integration.py
```

---

## 📝 十、已知限制

1. **小红书/抖音**：需要登录态才能获取完整内容（当前仅支持公开内容）
2. **yt-dlp**：国内平台需要配置cookie，海外平台需要代理
3. **ArchiveBox**：未集成（重量级，适合长期归档）
4. **大规模抓取**：建议配合IP代理池使用

---

## 🔄 十一、后续规划

| 优先级 | 功能 | 说明 |
|--------|------|------|
| P0 | LLM提示词优化 | 提升分类准确率 |
| P0 | 前端界面完善 | Gradio Web界面 |
| P1 | 小红书登录态 | 支持Cookie导入 |
| P1 | IP代理池 | 配合MediaCrawler使用 |
| P2 | 增量更新 | 检测内容变化自动更新 |
| P2 | 去重优化 | 基于embedding的语义去重 |
| P3 | 多Agent协作 | 与视频Agent对接 |

---

## 📞 十二、快速启动

```bash
# 1. 克隆仓库
git clone <repository_url>
cd ai-knowledge-alchemist

# 2. 安装依赖
pip install -r requirements.txt
python -m playwright install chromium

# 3. 配置环境变量
cp .env.example .env
# 编辑.env填写API Key

# 4. 运行测试
python test_full_crawler.py

# 5. 处理素材
python main.py --url "https://example.com/article"
```

---

*文档结束*
