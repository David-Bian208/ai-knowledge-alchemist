#!/usr/bin/env python3
"""测试backfill_content的无正文检测逻辑"""
import sys
import os
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.storage import HotStorage

print("="*60)
print("测试无正文检测逻辑")
print("="*60)

storage = HotStorage()
conn = sqlite3.connect(storage.db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 查询所有可能的无正文内容
query = """
    SELECT id, url, title, source_from, content, full_content 
    FROM selected_items 
    WHERE (
        (content IS NULL OR length(content) < 50) 
        AND (full_content IS NULL OR length(full_content) < 50)
    )
    OR (
        content LIKE '%<a href%' AND length(content) < 500
    )
    ORDER BY id DESC
    LIMIT 10
"""

cursor.execute(query)
rows = cursor.fetchall()

print(f"\n找到 {len(rows)} 条无正文/链接-only内容:\n")

for row in rows:
    content_text = row['content'] or ''
    has_link = '<a href' in content_text.lower()
    
    print(f"ID: {row['id']}")
    print(f"标题: {row['title'][:50]}")
    print(f"来源: {row['source_from']}")
    print(f"内容长度: {len(content_text)} 字符")
    print(f"包含HTML链接: {'是' if has_link else '否'}")
    
    if len(content_text) < 100:
        print(f"内容预览: {content_text[:80]}")
    else:
        print(f"内容预览: {content_text[:80]}...")
    print("-" * 60)

conn.close()

print("\n" + "="*60)
print("backfill_content应该能检测到所有这些内容")
print("="*60)
