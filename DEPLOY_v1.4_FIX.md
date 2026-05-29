# AI-Pulse v1.4 修复部署说明

> 版本：v1.4-fix  
> 打包时间：2026-05-27 13:30  
> 包大小：120KB

---

## 修复内容

### 1. 修复定时更新失效问题
- **问题**：生产环境设置了8:00更新，但实际没有执行
- **原因**：数据库中 `scheduled_enabled=false`，定时更新被禁用
- **修复**：
  - 启用定时更新：`scheduled_enabled=true`
  - 禁用间隔更新：`interval_enabled=false`（避免与定时更新冲突）
  - 保留间隔配置：`sync_interval=30`（以便需要时切换回间隔模式）

### 2. 调整AI HOT同步策略，减少Twitter/X内容比例
- **问题**：65.9%的AI HOT内容来自Twitter/X，这些内容本身较短（100-300字符）
- **修复**：
  - 对Twitter内容降低评分20%（`final_score * 0.8`）
  - 只入库分数>=60的推文（过滤低质量推文）
  - 为Twitter内容添加标签：`["社交媒体", "Twitter/X"]`
  - 在内容中添加标记：`📱 *社交媒体内容，建议结合原文URL查看*`

### 3. 修复去重功能致命错误
- **问题**：`dedup.py` 中调用了不存在的 `storage.query_materials()` 方法
- **修复**：改为直接查询 `selected_items` 表

### 4. 修复sync_aihot.py变量作用域错误
- **问题**：`final_score` 在语义去重检查时使用但未定义
- **修复**：调整代码顺序，先计算评分再进行语义去重

### 5. 增强backfill_content.py无正文检测
- **问题**：未识别HTML链接-only的内容（RSS源常见问题）
- **修复**：增加对 `<a href` 标签的检测

---

## 部署步骤

### 1. 停止当前服务
```bash
# 如果使用systemd
sudo systemctl stop ai-pulse

# 如果直接运行
# 找到进程并kill
ps aux | grep api_server
kill <PID>
```

### 2. 备份当前版本
```bash
cd /path/to/ai-pulse
cp -r . /path/to/backup/ai-pulse-v1.3-backup
```

### 3. 解压新版本
```bash
cd /path/to/deploy
tar -xzf ai-pulse-v1.4-fix-deploy.tar.gz
# 或直接覆盖关键文件
cp src/dedup.py /path/to/ai-pulse/src/
cp src/sync_aihot.py /path/to/ai-pulse/src/
cp src/backfill_content.py /path/to/ai-pulse/src/
cp src/scheduler.py /path/to/ai-pulse/src/
```

### 4. 修复数据库配置（关键！）
```bash
cd /path/to/ai-pulse
python3 -c "
import sqlite3
conn = sqlite3.connect('data/hot_pulse.db')
cursor = conn.cursor()
cursor.execute(\"UPDATE system_config SET value='true', updated_at=CURRENT_TIMESTAMP WHERE key='scheduled_enabled'\")
cursor.execute(\"UPDATE system_config SET value='false', updated_at=CURRENT_TIMESTAMP WHERE key='interval_enabled'\")
conn.commit()
print('定时任务配置已修复')
conn.close()
"
```

### 5. 重启服务
```bash
# 使用systemd
sudo systemctl start ai-pulse
sudo systemctl status ai-pulse

# 或直接运行
cd /path/to/ai-pulse
nohup python3 api_server.py > api_server.log 2>&1 &
```

### 6. 验证部署
```bash
# 检查服务状态
curl http://localhost:8887/health

# 检查定时任务配置
curl http://localhost:8887/api/v1/config

# 检查精选内容
curl http://localhost:8887/api/v1/list?mode=selected&limit=5

# 手动触发一次更新测试
curl -X POST http://localhost:8887/api/v1/fetch
```

---

## 验证要点

### 1. 定时更新验证
- 等待下一个8:00，检查是否自动执行更新
- 或手动修改系统时间测试：`sudo date -s "2026-05-28 08:00:00"`
- 检查日志：`tail -f api_server.log | grep "定时任务"`

### 2. Twitter内容验证
- 同步后检查新入库的Twitter内容
- 确认分数已降低20%
- 确认tags包含"社交媒体"和"Twitter/X"
- 确认内容末尾有社交媒体标记

### 3. 去重功能验证
- 同步时观察日志，确认去重服务正常初始化
- 应该看到："去重服务初始化完成: 已加载XXX条URL"

---

## 已知事项

| 项目 | 说明 |
|------|------|
| Embedding 语义去重 | DeepSeek API 暂不支持 embedding 模型，功能自动降级为 URL 去重，不影响主流程 |
| Twitter/X内容 | 65.9%的AI HOT内容来自Twitter，已降低评分并标记，建议前端筛选 |
| 阿里云 ASR | 默认未启用（enabled: false），视频占比>15%时在 config.yaml 中启用 |
| B 站视频源 | 需要配置 B 站 Cookie/Session 才能抓取 |
| 数据库 | 首次启动自动创建，路径在 config.yaml 中配置 |

---

## 回滚方案

如果部署后出现问题，可快速回滚：

```bash
# 1. 停止服务
sudo systemctl stop ai-pulse

# 2. 恢复备份
rm -rf /path/to/ai-pulse/src/*
cp -r /path/to/backup/ai-pulse-v1.3-backup/src/* /path/to/ai-pulse/src/

# 3. 恢复数据库配置
python3 -c "
import sqlite3
conn = sqlite3.connect('data/hot_pulse.db')
cursor = conn.cursor()
cursor.execute(\"UPDATE system_config SET value='false' WHERE key='scheduled_enabled'\")
cursor.execute(\"UPDATE system_config SET value='true' WHERE key='interval_enabled'\")
conn.commit()
conn.close()
"

# 4. 重启服务
sudo systemctl start ai-pulse
```

---

## 联系

如有部署问题，请联系小治。
