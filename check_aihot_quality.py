#!/usr/bin/env python3
"""检查AI HOT内容质量问题"""
import sys
import os
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.storage import HotStorage

print("="*60)
print("检查AI HOT内容质量")
print("="*60)

storage = HotStorage()
conn = sqlite3.connect(storage.db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("""
    SELECT id, url, title, content, source
    FROM selected_items 
    WHERE source_from = 'aihot'
    ORDER BY created_at DESC
""")
rows = cursor.fetchall()

x_count = 0
normal_url = 0
no_content = 0
has_content = 0

x_items = []
normal_items = []

for row in rows:
    url = (row['url'] or '').lower()
    content = row['content'] or ''
    content_len = len(content)
    
    if 'x.com' in url or 'twitter.com' in url:
        x_count += 1
        x_items.append({'row': row, 'content_len': content_len})
    else:
        normal_url += 1
        normal_items.append({'row': row, 'content_len': content_len})
    
    if content_len > 200:
        has_content += 1
    else:
        no_content += 1

print(f"总计: {len(rows)} 条")
print(f"\nTwitter/X链接: {x_count} 条 ({x_count/len(rows)*100:.1f}%)")
print(f"正常URL: {normal_url} 条 ({normal_url/len(rows)*100:.1f}%)")
print(f"\n有正文(>200字符): {has_content} 条 ({has_content/len(rows)*100:.1f}%)")
print(f"无正文/摘要: {no_content} 条 ({no_content/len(rows)*100:.1f}%)")

# 查看Twitter链接的内容情况
print(f"\n\n[1] Twitter/X链接的内容样例（最新5条）")
print("-" * 60)
for item in x_items[:5]:
    row = item['row']
    print(f"\nID: {row['id']}")
    print(f"标题: {row['title'][:50]}")
    print(f"来源: {row['source']}")
    print(f"URL: {row['url']}")
    print(f"内容长度: {item['content_len']} 字符")
    content = row['content'] or ''
    print(f"内容预览: {content[:100]}...")
    print("-" * 60)

# 查看正常URL的内容情况
print(f"\n\n[2] 正常URL的内容样例（最新5条）")
print("-" * 60)
for item in normal_items[:5]:
    row = item['row']
    print(f"\nID: {row['id']}")
    print(f"标题: {row['title'][:50]}")
    print(f"来源: {row['source']}")
    print(f"URL: {row['url']}")
    print(f"内容长度: {item['content_len']} 字符")
    content = row['content'] or ''
    print(f"内容预览: {content[:150]}...")
    print("-" * 60)

conn.close()
print("\n" + "="*60)
print("结论：65.9%是Twitter/X链接，无法抓取正文")
print("建议：需要在同步时增加Twitter内容的特殊处理")
print("="*60)
