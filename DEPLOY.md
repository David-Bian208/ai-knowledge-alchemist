# AI-Pulse v1.3 部署指南

> 版本：v1.3  
> 打包时间：2026-05-26  
> 包大小：1.7MB

---

## 快速部署（5 分钟）

```bash
# 1. 解压到目标目录
cd /path/to/deploy
tar -xzf ai-pulse-v1.3-deploy.tar.gz
cd ai-pulse-deploy

# 2. 安装依赖
pip3 install -r requirements.txt

# 3. 配置 API Key（编辑 config/config.yaml）
# - llm.api_key: DeepSeek API Key（已有）
# - aliyun.api_key: 阿里云 DashScope Key（视频 ASR 转写用，已有）

# 4. 启动服务
python3 api_server.py
```

**默认端口：** 8887  
**访问地址：** http://localhost:8887

---

## 目录结构

```
ai-pulse/
├── api_server.py        # FastAPI 后端服务（主入口）
├── app.py               # Gradio 前端（可选）
├── api.py               # API 接口定义
├── config/
│   ├── config.yaml      # 主配置文件（LLM/ASR/存储路径）
│   └── sources.yaml     # 265 个信源配置
├── src/                 # 核心模块
│   ├── processor.py     # 内容处理流水线
│   ├── crawler.py       # 网页爬虫
│   ├── rss_fetcher.py   # RSS 抓取
│   ├── dedup.py         # 双层去重（URL+Embedding）
│   ├── storage.py       # 数据库操作
│   ├── source_manager.py# 信源管理
│   ├── daily_generator.py# 日报生成
│   └── ...
├── frontend/dist/       # 前端构建产物
└── third_party/MediaCrawler/  # 第三方媒体爬虫
```

---

## 启动方式

### 方式 1：后台运行
```bash
nohup python3 api_server.py > api_server.log 2>&1 &
```

### 方式 2：systemd 服务
```bash
# 创建 /etc/systemd/system/ai-pulse.service
[Unit]
Description=AI-Pulse Content Aggregator
After=network.target

[Service]
Type=simple
User=admin
WorkingDirectory=/path/to/ai-pulse
ExecStart=/usr/bin/python3 api_server.py
Restart=always

[Install]
WantedBy=multi-user.target

# 启动服务
systemctl enable ai-pulse
systemctl start ai-pulse
```

---

## 功能验证

部署后运行以下命令验证：

```bash
# 1. 检查服务状态
curl http://localhost:8887/health

# 2. 检查精选内容
curl http://localhost:8887/api/v1/list?limit=5

# 3. 检查信源列表
curl http://localhost:8887/api/v1/sources

# 4. 手动触发更新
curl -X POST http://localhost:8887/api/v1/fetch
```

---

## 已知事项

| 项目 | 说明 |
|------|------|
| Embedding 语义去重 | DeepSeek API 暂不支持 embedding 模型，功能自动降级为 URL 去重，不影响主流程 |
| 阿里云 ASR | 默认未启用（enabled: false），视频占比>15% 时在 config.yaml 中启用 |
| B 站视频源 | 需要配置 B 站 Cookie/Session 才能抓取 |
| 数据库 | 首次启动自动创建，路径在 config.yaml 中配置 |

---

## 配置文件说明

### config/config.yaml

```yaml
llm:
  api_key: "sk-xxx"  # DeepSeek API Key
  cheap_model: "deepseek-v4-flash"
  pro_model: "deepseek-v4-pro"

aliyun:
  api_key: "sk-xxx"  # 阿里云 DashScope Key（视频 ASR）
  enabled: false     # 视频占比>15% 时改为 true

storage:
  db_path: "data/hot_pulse.db"
```

---

## Git 仓库

```bash
git clone <仓库地址>
cd ai-pulse
# 查看提交历史（仅 2 个 commit）
git log --oneline
```

---

## 联系

如有部署问题，请联系小治。
