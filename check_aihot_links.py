#!/usr/bin/env python3
"""检查AI HOT链接问题"""
import sys
import os
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.storage import HotStorage

print("="*60)
print("检查AI HOT链接问题")
print("="*60)

storage = HotStorage()
conn = sqlite3.connect(storage.db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 检查AI HOT来源的URL
print("\n[1] AI HOT来源的URL检查")
print("-" * 60)
cursor.execute("""
    SELECT id, url, title, source, source_from
    FROM selected_items 
    WHERE source_from = 'aihot'
    ORDER BY created_at DESC
    LIMIT 10
""")
rows = cursor.fetchall()
for row in rows:
    print(f"\nID: {row['id']}")
    print(f"标题: {row['title'][:50]}")
    print(f"URL: {row['url']}")
    
    # 检查URL是否有效
    url = row['url']
    if not url:
        print("状态: ❌ URL为空")
    elif url.startswith('http'):
        print("状态: ✅ URL格式正常")
    else:
        print(f"状态: ❌ URL格式异常: {url[:50]}")

# 检查所有空URL或异常URL
print("\n\n[2] 所有异常URL检查")
print("-" * 60)
cursor.execute("""
    SELECT id, url, title, source_from, source
    FROM selected_items 
    WHERE url IS NULL OR url = '' OR url NOT LIKE 'http%'
    LIMIT 20
""")
rows = cursor.fetchall()
print(f"找到 {len(rows)} 条异常URL:\n")
for row in rows:
    print(f"ID: {row['id']}")
    print(f"来源: {row['source_from']}")
    print(f"标题: {row['title'][:50]}")
    print(f"URL: '{row['url'] or '(空)'}'")
    print("-" * 60)

# 统计URL分布
print("\n[3] 按来源统计URL情况")
print("-" * 60)
cursor.execute("""
    SELECT 
        source_from,
        COUNT(*) as total,
        SUM(CASE WHEN url IS NULL OR url = '' THEN 1 ELSE 0 END) as no_url,
        SUM(CASE WHEN url LIKE 'http%' THEN 1 ELSE 0 END) as valid_url
    FROM selected_items
    GROUP BY source_from
""")
rows = cursor.fetchall()
for row in rows:
    print(f"\n{row['source_from']}:")
    print(f"  总计: {row['total']}")
    print(f"  无URL: {row['no_url']}")
    print(f"  有效URL: {row['valid_url']}")

conn.close()
print("\n" + "="*60)
