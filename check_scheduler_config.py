#!/usr/bin/env python3
"""检查定时任务配置"""
import sys
import os
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.storage import HotStorage

print("="*60)
print("检查定时任务配置")
print("="*60)

storage = HotStorage()
conn = sqlite3.connect(storage.db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 读取所有定时任务相关配置
cursor.execute("SELECT * FROM system_config")
rows = cursor.fetchall()

print("\n系统配置：")
for row in rows:
    print(f"  {row['key']}: {row['value']}")

conn.close()

print("\n" + "="*60)
print("分析结果：")
print("="*60)

# 检查关键配置
configs = {row['key']: row['value'] for row in rows}

interval_enabled = configs.get('interval_enabled', 'true')
sync_interval = configs.get('sync_interval', '60')
scheduled_enabled = configs.get('scheduled_enabled', 'false')
scheduled_time = configs.get('scheduled_time', '8')
auto_generate = configs.get('auto_generate_report', 'true')

print(f"\n1. 间隔更新: {'启用' if interval_enabled == 'true' else '禁用'}")
print(f"   间隔: {sync_interval} 分钟")
print(f"\n2. 定时更新: {'启用' if scheduled_enabled == 'true' else '禁用'}")
print(f"   时间: {scheduled_time}:00")
print(f"\n3. 自动日报: {'启用' if auto_generate == 'true' else '禁用'}")

print("\n" + "="*60)
print("问题诊断：")
print("="*60)

if scheduled_enabled != 'true':
    print("❌ 定时更新已禁用！这是8:00没有执行的原因")
    print("   需要在数据库中设置 scheduled_enabled=true")

if interval_enabled == 'true':
    print(f"⚠️ 间隔更新已启用（每{sync_interval}分钟）")
    print("   这会在8:00时也触发更新，可能导致冲突")

print("\n建议修复：")
print("1. 启用定时更新: scheduled_enabled=true")
print("2. 如果不需要间隔更新，可以禁用: interval_enabled=false")
print("="*60)
