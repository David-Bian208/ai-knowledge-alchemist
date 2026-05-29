#!/usr/bin/env python3
"""修复定时任务配置"""
import sys
import os
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.storage import HotStorage

print("="*60)
print("修复定时任务配置")
print("="*60)

storage = HotStorage()
conn = sqlite3.connect(storage.db_path)
cursor = conn.cursor()

print("\n修复前：")
cursor.execute("SELECT key, value FROM system_config WHERE key IN ('scheduled_enabled', 'interval_enabled', 'sync_interval')")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

# 修复配置
print("\n执行修复：")

# 1. 启用定时更新
cursor.execute("UPDATE system_config SET value='true', updated_at=CURRENT_TIMESTAMP WHERE key='scheduled_enabled'")
print("  ✅ scheduled_enabled = true")

# 2. 禁用间隔更新（避免冲突，用户设置了8:00更新，说明需要定时而非间隔）
cursor.execute("UPDATE system_config SET value='false', updated_at=CURRENT_TIMESTAMP WHERE key='interval_enabled'")
print("  ✅ interval_enabled = false")

# 3. 确认同步间隔配置（保留以防需要切换）
cursor.execute("UPDATE system_config SET value='30' WHERE key='sync_interval'")
print("  ✅ sync_interval = 30 (保留)")

conn.commit()
conn.close()

print("\n修复后：")
storage2 = HotStorage()
conn2 = sqlite3.connect(storage2.db_path)
conn2.row_factory = sqlite3.Row
cursor2 = conn2.cursor()
cursor2.execute("SELECT key, value FROM system_config WHERE key IN ('scheduled_enabled', 'interval_enabled', 'sync_interval', 'scheduled_time', 'auto_generate_report')")
for row in cursor2.fetchall():
    print(f"  {row['key']}: {row['value']}")
conn2.close()

print("\n" + "="*60)
print("修复完成！")
print("="*60)
print("\n现在的行为：")
print("1. ✅ 每天8:00自动执行更新+生成日报")
print("2. ✅ 禁用30分钟间隔更新（避免重复执行）")
print("3. ✅ 如果需要同回间隔更新，可在前端设置中启用")
print("="*60)
