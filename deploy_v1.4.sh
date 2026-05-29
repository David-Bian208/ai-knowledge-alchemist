#!/bin/bash
# AI-Pulse v1.4 自动化部署脚本
# 使用方法：./deploy_v1.4.sh

set -e

echo "============================================================"
echo "AI-Pulse v1.4 自动化部署脚本"
echo "============================================================"
echo ""

# 配置
SERVER="8.130.148.166"
SERVER_USER="admin"
SERVER_PATH="/opt/behavior-recorder/ai-pulse"
LOCAL_PACKAGE="/home/admin/.openclaw/workspace/behavior_recorder_service/ai-pulse/ai-pulse-v1.4-final.tar.gz"
REMOTE_PACKAGE="/tmp/ai-pulse-v1.4-final.tar.gz"

echo "📦 部署包信息"
echo "  本地路径：$LOCAL_PACKAGE"
echo "  服务器：$SERVER_USER@$SERVER"
echo "  目标路径：$SERVER_PATH"
echo ""

# 步骤 1：检查部署包
echo "步骤 1: 检查部署包..."
if [ ! -f "$LOCAL_PACKAGE" ]; then
    echo "❌ 部署包不存在：$LOCAL_PACKAGE"
    exit 1
fi
echo "✅ 部署包存在，大小：$(ls -lh $LOCAL_PACKAGE | awk '{print $5}')"
echo ""

# 步骤 2：上传部署包
echo "步骤 2: 上传部署包到服务器..."
scp "$LOCAL_PACKAGE" "$SERVER_USER@$SERVER:$REMOTE_PACKAGE"
echo "✅ 上传完成"
echo ""

# 步骤 3：SSH 执行部署
echo "步骤 3: 在服务器上执行部署..."
ssh "$SERVER_USER@$SERVER" << 'ENDSSH'
set -e

echo "  📋 停止当前服务..."
ps aux | grep api_server | grep -v grep | awk '{print $2}' | xargs -r kill || true
sleep 2

echo "  💾 备份当前版本..."
cd /opt/behavior-recorder/ai-pulse
if [ -d . ]; then
    BACKUP_DIR="../ai-pulse-backup-$(date +%Y%m%d-%H%M%S)"
    cp -r . "$BACKUP_DIR"
    echo "  ✅ 备份到：$BACKUP_DIR"
fi

echo "  📦 解压新版本..."
cd /opt/behavior-recorder/ai-pulse
rm -rf config src frontend *.py requirements.txt 2>/dev/null || true
tar -xzf /tmp/ai-pulse-v1.4-final.tar.gz
echo "  ✅ 解压完成"

echo "  🔧 修复数据库配置..."
cd /opt/behavior-recorder/ai-pulse
python3 << 'PYEOF'
import sqlite3
conn = sqlite3.connect('data/hot_pulse.db')
cursor = conn.cursor()

cursor.execute("UPDATE system_config SET value='true' WHERE key='scheduled_enabled'")
cursor.execute("UPDATE system_config SET value='false' WHERE key='interval_enabled'")
cursor.execute("UPDATE system_config SET value='true' WHERE key='auto_generate_report'")

conn.commit()
conn.close()
print("  ✅ 数据库配置修复完成")
PYEOF

echo "  📋 验证配置..."
cd /opt/behavior-recorder/ai-pulse
python3 << 'PYEOF'
import sqlite3
conn = sqlite3.connect('data/hot_pulse.db')
cursor = conn.cursor()
cursor.execute('SELECT key, value FROM system_config WHERE key IN ("scheduled_enabled", "interval_enabled", "auto_generate_report")')
for r in cursor.fetchall():
    print(f"    {r[0]}: {r[1]}")
conn.close()
PYEOF

echo "  🚀 启动服务..."
cd /opt/behavior-recorder/ai-pulse
nohup python3 api_server.py > api_server.log 2>&1 &
sleep 3

echo "  ✅ 服务启动完成"
echo "  📊 进程状态:"
ps aux | grep api_server | grep -v grep

echo ""
echo "  🔍 健康检查:"
curl -s http://localhost:8887/health || echo "  ⚠️ 服务可能还在启动中..."

ENDSSH

echo ""
echo "============================================================"
echo "✅ 部署完成！"
echo "============================================================"
echo ""
echo "📋 下一步验证："
echo "  1. 访问前端：http://8.130.148.166:8887"
echo "  2. 手动触发更新：点击前端刷新按钮"
echo "  3. 等待明日 8:00 验证定时任务"
echo "  4. 查看日志：ssh admin@8.130.148.166 'tail -f /opt/behavior-recorder/ai-pulse/logs/fetch.log'"
echo ""
