#!/usr/bin/env python3
"""深度检查内容质量问题"""
import sys
import os
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.storage import HotStorage

print("="*60)
print("内容质量问题深度检查")
print("="*60)

storage = HotStorage()
conn = sqlite3.connect(storage.db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 1. 检查RSS源的内容质量
print("\n[1] RSS源内容质量")
print("-" * 60)
cursor.execute("""
    SELECT id, title, content, full_content, source_from
    FROM selected_items 
    WHERE source_from = 'rss_fetch'
    ORDER BY created_at DESC
    LIMIT 10
""")
rows = cursor.fetchall()
rss_count = len(rows)
print(f"RSS源内容总数：{cursor.execute('SELECT COUNT(*) FROM selected_items WHERE source_from = \"rss_fetch\"').fetchone()[0]}")
print(f"\n最新10条RSS内容：")
for row in rows:
    content_len = len(row['content'] or '')
    print(f"ID: {row['id']}")
    print(f"标题: {row['title'][:50]}")
    print(f"内容长度: {content_len}")
    print(f"内容预览: {(row['content'] or '')[:100]}...")
    print("-" * 60)

# 2. 检查为什么有些内容字段为空
print("\n[2] 内容为空的原因分析")
print("-" * 60)
cursor.execute("""
    SELECT id, title, content, full_content, source_from
    FROM selected_items 
    WHERE (content IS NULL OR content = '')
    LIMIT 5
""")
rows = cursor.fetchall()
for row in rows:
    print(f"ID: {row['id']}")
    print(f"标题: {row['title']}")
    print(f"content: {row['content'] or '(空)'}")
    print(f"full_content: {(row['full_content'] or '')[:100]}...")
    print(f"来源: {row['source_from']}")
    print("-" * 60)

# 3. 按来源统计内容长度分布
print("\n[3] 各来源内容长度分布")
print("-" * 60)
cursor.execute("""
    SELECT 
        source_from,
        COUNT(*) as total,
        AVG(CASE WHEN content IS NOT NULL THEN length(content) ELSE 0 END) as avg_len,
        SUM(CASE WHEN content IS NOT NULL AND length(content) > 500 THEN 1 ELSE 0 END) as good_content
    FROM selected_items
    GROUP BY source_from
""")
for row in cursor.fetchall():
    print(f"\n{row['source_from']}:")
    print(f"  总数: {row['total']}")
    print(f"  平均长度: {row['avg_len']:.0f} 字符")
    print(f"  好内容(>500字符): {row['good_content']} 条")

conn.close()
