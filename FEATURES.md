# 知识炼金术 Agent - 完整功能清单
**版本**: V1.0-V1.3 | **开发**: 小治 | **日期**: 2026-05-17
---
## 一、产品定位
**全行业通用素材流水线引擎**
输入URL/RSS，自动完成「抓取→去噪→分类→评分→提炼→归档」全流程，输出结构化的素材库，直接供视频Agent使用。
---
## 二、核心功能模块
### 1. 爬虫模块（`src/crawler.py`）
- ✅ **通用HTML正文提取**：使用 trafilatura 自动提取网页正文，去除广告/导航/评论
- ✅ **元数据自动提取**：标题/作者/发布时间/来源
- ✅ **微信公众号抓取**（`src/wechat_crawler.py`）：支持直接抓取 + RSSHub方式
### 2. 处理引擎（`src/processor.py`）
- ✅ **三维分类**（内容维度×场景维度 + 代码判断时间维度）
- ✅ **三维评分**（重要性/稀缺性/实用性，LLM打分）
- ✅ **综合评分计算**（代码公式：LLM评分×权重×时效性加权）
- ✅ **核心提炼**（3-5个核心观点 + 视频适用场景建议）
- ✅ **高优先级增强**（≥4星素材额外生成摘要+复用价值点+视频制作建议）
### 3. 存储归档（`src/storage.py` + `src/archiver.py`）
- ✅ **SQLite数据库**：结构化存储所有素材，支持多维查询
- ✅ **本地目录自动归档**：按「内容维度/时间维度」自动保存
- ✅ **FrontMatter元数据**：Markdown文件头部附带完整处理结果
### 4. 去重检测（`src/dedup.py`）
- ✅ **URL精确匹配去重**：已处理URL自动跳过
- ✅ **批量处理自动去重**
### 5. RSS订阅（`src/rss_fetcher.py`）
- ✅ **RSS源自动抓取**：支持标准RSS格式
- ✅ **新内容过滤**：只抓取未处理过的内容
### 6. 定时调度（`src/scheduler.py`）
- ✅ **定时自动抓取**：默认每天10:00/16:00/22:00三个时间点
- ✅ **信源配置管理**：支持添加/删除信源
- ✅ **可配置调度时间**
### 7. 通知系统（`src/notification.py`）
- ✅ **失败通知**：抓取/处理失败时自动通知
- ✅ **多通道支持**：日志 + 文件 + Webhook
- ✅ **日报生成通知**
### 8. 自动日报（`src/report.py`）
- ✅ **一键生成行业日报**：按分类/分数自动排序，无需LLM
- ✅ **支持指定日期**：可生成任意日期的日报
### 9. MCP/Obsidian集成（`src/mcp_client.py`）
- ✅ **读取Obsidian笔记**：搜索/读取知识库内容
- ✅ **回写标签到FrontMatter**：处理结果自动同步到Obsidian
- ✅ **自动归档到Obsidian**：按分类保存到指定目录
### 10. 代理配置（`src/proxy_config.py`）
- ✅ **HTTP代理支持**：解决海外信源访问问题
---
## 三、评分公式
```
最终分 = (重要性×0.4 + 稀缺性×0.3 + 实用性×0.3) × 10 × 时效性权重
```
| 维度 | 权重 | 说明 |
|------|------|------|
| 重要性 | 40% | 事件的行业影响程度 |
| 稀缺性 | 30% | 是不是独家/一手信息 |
| 实用性 | 30% | 能不能直接用来做内容 |
**时效性权重**：7天内×1.5 / 1个月内×1.2 / 3个月内×1.0 / 1年内×0.9 / 超过1年×0.8
**星级映射**：≥90分→5星 / ≥80分→4星 / ≥70分→3星 / ≥60分→2星 / <60分→1星
---
## 四、命令行用法
```bash
# 处理单个URL
python3 main.py process --url https://example.com/article
# 处理URL并同步到Obsidian
python3 main.py process --url https://example.com --obsidian
# 批量处理URL列表（自动跳过已处理）
python3 main.py batch --file urls.txt
# 生成日报
python3 main.py report --date 2025-05-16
# 启动定时调度守护进程
python3 main.py daemon
# 同步SQLite数据到Obsidian
python3 main.py mcp-sync
```
---
## 五、环境变量配置
```bash
# 必须
export DEEPSEEK_API_KEY="your_api_key"
# 可选
export OBSIDIAN_VAULT_PATH="/path/to/your/obsidian/vault"
export RSSHUB_URL="http://your-rsshub-server:1200"
export HTTP_PROXY="http://proxy.example.com:8080"
```
---
## 六、技术架构
```
URL/RSS输入
↓
爬虫模块（trafilatura正文提取 + 元数据）
↓
重复检测（SQLite已有URL过滤）
↓
三维分类（LLM：内容×场景，代码：时间）
↓
三维评分（LLM：重要性/稀缺性/实用性）
↓
代码综合计算（公式：评分×权重×时效性）
↓
核心提炼（LLM：核心观点+视频适用场景）
↓
高优先级增强（≥4星：摘要+复用点+视频建议）
↓
SQLite入库 + 本地目录归档 + Obsidian同步
↓
通知系统（失败时自动通知）
```
---
## 七、V1.0-V1.3 迭代规划
| 版本 | 状态 | 核心功能 |
|------|------|---------|
| V1.0 | ✅ 完成 | URL抓取+分类+评分+提炼+归档基础链路 |
| V1.1 | ✅ 完成 | RSS订阅+批量处理+重复检测+日报生成+配置化 |
| V1.2 | ✅ 完成 | 定时调度+MCP/Obsidian+失败通知 |
| V1.3 | ✅ 完成 | 高优先级分层+HTTP代理配置+微信公众号抓取 |
| V1.4 | 待开发 | 事件聚类去重（Embedding语义匹配） |
---
## 八、核心优势（对比CherryStudio方案）
| 维度 | CherryStudio | 知识炼金术Agent |
|------|-------------|---------------|
| 信源管理 | 固定23个硬编码 | 配置包可切换领域 |
| 分类精度 | 4个大类 | 三维分类（时间×内容×场景） |
| 评分机制 | 无 | 三维评分+代码加权+星级映射 |
| 核心提炼 | 简单摘要 | 核心观点+视频适用场景 |
| 高优先级处理 | 无 | ≥4星额外生成摘要+复用价值点 |
| 重复检测 | 简单去重 | URL精确匹配+SQLite持久化 |
| 定时任务 | 有（3个时间点） | 有（可配置时间+信源管理） |
| MCP集成 | 有 | 有（Obsidian读取/写入/同步） |
---
## 九、测试验证结果
### 最新测试（2026-05-17）
**测试URL**: https://www.thepaper.cn/newsDetail_forward_28717294（澎湃新闻）
**处理结果**：
- ✅ **抓取**：成功提取正文，无广告噪音
- ✅ **元数据**：标题"7项国家机密被境外窃取！国家安全部披露详情"、来源澎湃新闻、发布时间2024-09-12
- ✅ **分类**：内容=案例、场景=脚本素材、时间=经典常青
- ✅ **评分**：重要性8/10、稀缺性6/10、实用性4/10
- ✅ **计算**：最终分49.6（1星，因为是2024年旧闻，时效性权重0.8拉低）
- ✅ **提炼**：4个核心观点 + 视频适用场景建议
- ✅ **归档**：本地目录 `案例/经典常青/` + SQLite入库成功
**历史测试统计**：
| URL | 结果 | 状态 |
|-----|------|------|
| 极客公园科技资讯 | 完整抓取，分类/评分/提炼全部正确 | ✅ |
| AIHOT主页（SPA） | 内容零散但LLM仍能处理 | ✅ |
| 澎湃新闻国家安全报道 | 完整处理，时效性加权正确 | ✅ |
---
## 十、项目文件结构
```
ai-knowledge-alchemist/
├── main.py # 命令行入口
├── requirements.txt # 依赖清单
├── README.md # 使用说明
├── FEATURES.md # 功能清单（本文档）
├── config/
│ ├── config.yaml # 主配置
│ └── domain_ai.yaml # AI领域配置包
├── prompts/
│ ├── classification.txt # 分类提示词
│ ├── scoring.txt # 评分提示词
│ └── extraction.txt # 提炼提示词
├── src/
│ ├── processor.py # 处理引擎
│ ├── crawler.py # 爬虫模块
│ ├── wechat_crawler.py # 微信抓取
│ ├── llm_client.py # LLM客户端
│ ├── storage.py # SQLite存储
│ ├── archiver.py # 归档模块
│ ├── dedup.py # 去重检测
│ ├── rss_fetcher.py # RSS订阅
│ ├── scheduler.py # 定时调度
│ ├── notification.py # 通知系统
│ ├── report.py # 日报生成
│ ├── mcp_client.py # MCP/Obsidian
│ ├── priority_enhancer.py # 高优先级增强
│ ├── proxy_config.py # 代理配置
│ ├── config.py # 配置管理
│ └── utils.py # 工具函数
├── data/
│ ├── materials.db # SQLite数据库
│ ├── output/ # 归档目录
│ └── notifications.json # 通知记录
└── ITER_V1.0_DEVELOPMENT_GUIDE.md # 开发手册
DEV_TASK_FOR_XIAOZHI.md # 开发指令
WORK_PROGRESS.md # 进度记录
```
---
## 十一、仓库地址
- **远程仓库**: `git@github.com:David-Bian208/ai-knowledge-alchemist.git`
- **当前分支**: `dev/xiaozhi_v1.0`
- **最新提交**: `docs: 功能清单文档(FEATURES.md)及测试验证`
