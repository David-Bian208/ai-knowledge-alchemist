#!/bin/bash
# AI-Pulse v1.4 一键部署脚本（复制粘贴版）
# 使用方法：复制整个脚本，粘贴到 SSH 会话中执行

set -e

echo "============================================================"
echo "AI-Pulse v1.4 一键部署脚本"
echo "============================================================"
echo ""

# 配置
SERVER_PATH="/opt/behavior-recorder/ai-pulse"
PACKAGE="/tmp/ai-pulse-v1.4-final.tar.gz"

echo "📦 步骤 1: 检查部署包..."
if [ ! -f "$PACKAGE" ]; then
    echo "❌ 部署包不存在：$PACKAGE"
    echo "请先执行：scp /home/admin/.openclaw/workspace/behavior_recorder_service/ai-pulse/ai-pulse-v1.4-final.tar.gz admin@8.130.148.166:/tmp/"
    exit 1
fi
echo "✅ 部署包存在，大小：$(ls -lh $PACKAGE | awk '{print $5}')"
echo ""

echo "📋 步骤 2: 停止当前服务..."
ps aux | grep api_server | grep -v grep | awk '{print $2}' | xargs -r kill || true
sleep 2
echo "✅ 服务已停止"
echo ""

echo "💾 步骤 3: 备份当前版本..."
cd $SERVER_PATH
if [ -d . ]; then
    BACKUP_DIR="../ai-pulse-backup-$(date +%Y%m%d-%H%M%S)"
    cp -r . "$BACKUP_DIR"
    echo "✅ 备份到：$BACKUP_DIR"
fi
echo ""

echo "📦 步骤 4: 解压新版本..."
cd $SERVER_PATH
rm -rf config src frontend *.py requirements.txt 2>/dev/null || true
tar -xzf $PACKAGE
echo "✅ 解压完成"
echo ""

echo "🔧 步骤 5: 修复数据库配置..."
cd $SERVER_PATH
python3 << 'PYEOF'
import sqlite3
conn = sqlite3.connect('data/hot_pulse.db')
cursor = conn.cursor()

cursor.execute("UPDATE system_config SET value='true' WHERE key='scheduled_enabled'")
cursor.execute("UPDATE system_config SET value='false' WHERE key='interval_enabled'")
cursor.execute("UPDATE system_config SET value='true' WHERE key='auto_generate_report'")

conn.commit()
conn.close()
print("✅ 数据库配置修复完成")
PYEOF
echo ""

echo "📋 步骤 6: 验证配置..."
cd $SERVER_PATH
python3 << 'PYEOF'
import sqlite3
conn = sqlite3.connect('data/hot_pulse.db')
cursor = conn.cursor()
cursor.execute('SELECT key, value FROM system_config WHERE key IN ("scheduled_enabled", "interval_enabled", "auto_generate_report")')
for r in cursor.fetchall():
    print(f"  {r[0]}: {r[1]}")
conn.close()
PYEOF
echo ""

echo "🚀 步骤 7: 启动服务..."
cd $SERVER_PATH
nohup python3 api_server.py > api_server.log 2>&1 &
sleep 3
echo "✅ 服务已启动"
echo ""

echo "📊 步骤 8: 验证服务..."
echo "  进程状态:"
ps aux | grep api_server | grep -v grep | head -1

echo ""
echo "  端口状态:"
netstat -tlnp 2>/dev/null | grep 8887 || ss -tlnp | grep 8887 || echo "  ⚠️ 端口检查失败"

echo ""
echo "  健康检查:"
curl -s http://localhost:8887/health || echo "  ⚠️ 服务可能还在启动中..."

echo ""
echo "============================================================"
echo "✅ 部署完成！"
echo "============================================================"
echo ""
echo "📋 下一步验证："
echo "  1. 访问前端：http://8.130.148.166:8887"
echo "  2. 手动触发更新：点击前端刷新按钮"
echo "  3. 等待明日 8:00 验证定时任务"
echo "  4. 查看日志：tail -f $SERVER_PATH/logs/fetch.log"
echo ""
