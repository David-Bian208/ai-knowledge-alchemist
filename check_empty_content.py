#!/usr/bin/env python3
"""检查为什么有些内容长度为0"""
import sys
import os
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.storage import HotStorage

print("="*60)
print("检查内容为空的条目")
print("="*60)

storage = HotStorage()
conn = sqlite3.connect(storage.db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("SELECT id, title, content, full_content, source_from, source_tier, created_at FROM selected_items WHERE length(content) = 0 OR content IS NULL LIMIT 20")
rows = cursor.fetchall()

print(f"\n找到 {len(rows)} 条内容为空的记录:\n")

for row in rows:
    print(f"ID: {row['id']}")
    print(f"标题: {row['title'][:60]}")
    print(f"来源: {row['source_from']}")
    print(f"信源等级: {row['source_tier']}")
    print(f"full_content: {row['full_content'][:100] if row['full_content'] else '(空)'}")
    print(f"创建时间: {row['created_at']}")
    print("-" * 60)

conn.close()
