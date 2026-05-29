#!/usr/bin/env python3
import sqlite3
from datetime import datetime

conn = sqlite3.connect('data/hot_pulse.db')
cursor = conn.cursor()

print("=" * 60)
print("AI-Pulse 数据库状态检查")
print("=" * 60)

# 最新内容
cursor.execute('SELECT publish_date, title FROM selected_items ORDER BY publish_date DESC LIMIT 5')
print("\n最新内容日期:")
for r in cursor.fetchall():
    print(f"  {r[0]} | {r[1][:50]}")

# 最新日报
cursor.execute('SELECT date, lead_title FROM daily_reports ORDER BY date DESC LIMIT 5')
print("\n最新日报日期:")
for r in cursor.fetchall():
    print(f"  {r[0]} | {r[1][:50] if r[1] else 'N/A'}")

# 内容统计
cursor.execute('SELECT COUNT(*) FROM selected_items WHERE selected=1')
total = cursor.fetchone()[0]
print(f"\n精选内容总数：{total}")

# 日报统计
cursor.execute('SELECT COUNT(*) FROM daily_reports')
daily_total = cursor.fetchone()[0]
print(f"日报总数：{daily_total}")

# 检查今日是否有同步
today = datetime.now().strftime('%Y-%m-%d')
cursor.execute('SELECT COUNT(*) FROM selected_items WHERE publish_date = ? AND selected=1', (today,))
today_count = cursor.fetchone()[0]
print(f"\n今日 ({today}) 新增内容：{today_count} 条")

conn.close()
print("\n" + "=" * 60)
