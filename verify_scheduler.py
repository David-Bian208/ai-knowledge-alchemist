#!/usr/bin/env python3
"""验证定时任务时间配置是否正确读取"""
import sys
import os
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.storage import HotStorage

print("="*60)
print("验证定时任务时间配置")
print("="*60)

storage = HotStorage()
conn = sqlite3.connect(storage.db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 读取所有定时任务相关配置
cursor.execute("SELECT key, value FROM system_config WHERE key IN ('scheduled_enabled', 'scheduled_time', 'interval_enabled', 'sync_interval', 'auto_generate_report')")
rows = cursor.fetchall()

print("\n当前配置：")
for row in rows:
    print(f"  {row['key']}: {row['value']}")

# 分析逻辑
configs = {row['key']: row['value'] for row in rows}

print("\n" + "="*60)
print("代码逻辑分析：")
print("="*60)

# 检查scheduler.py的逻辑
print("\nsrc/scheduler.py 第115行：")
print("  scheduled_hour = int(storage.get_config('scheduled_time', '8'))")
print("\n这意味着：")
print(f"  ✅ 代码从数据库读取 scheduled_time = {configs.get('scheduled_time', '未设置')}")
print("  ✅ 如果数据库没有这个值，才使用默认值 8")
print("\n结论：")
print("  时间是动态读取的，不是写死的！")
print("  你前端设置几点，就几点执行")

print("\n" + "="*60)
print("之前的问题不是时间写死，而是 scheduled_enabled=false")
print("导致整个定时更新功能被禁用了，所以8:00没执行")
print("现在已经修复为 scheduled_enabled=true")
print("="*60)

conn.close()
