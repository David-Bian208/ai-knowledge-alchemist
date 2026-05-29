#!/usr/bin/env python3
"""检查内容质量分布"""
import sys
import os
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.storage import HotStorage

print("="*60)
print("内容质量深度分析")
print("="*60)

storage = HotStorage()
conn = sqlite3.connect(storage.db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 获取所有内容
cursor.execute("SELECT id, title, content, source_from, source_tier, final_score, created_at FROM selected_items ORDER BY created_at DESC")
rows = cursor.fetchall()

total = len(rows)
print(f"\n总内容数：{total} 条\n")

# 按内容长度分类
short_content = []    # < 200字符
medium_content = []   # 200-1000字符
long_content = []     # 1000-5000字符
very_long_content = [] # > 5000字符

for row in rows:
    content_len = len(row['content'] or '')
    if content_len < 200:
        short_content.append({'id': row['id'], 'title': row['title'], 'len': content_len, 'tier': row['source_tier'], 'source': row['source_from']})
    elif content_len < 1000:
        medium_content.append({'id': row['id'], 'title': row['title'], 'len': content_len, 'tier': row['source_tier'], 'source': row['source_from']})
    elif content_len < 5000:
        long_content.append({'id': row['id'], 'title': row['title'], 'len': content_len, 'tier': row['source_tier'], 'source': row['source_from']})
    else:
        very_long_content.append({'id': row['id'], 'title': row['title'], 'len': content_len, 'tier': row['source_tier'], 'source': row['source_from']})

print("内容长度分布：")
print(f"  极短内容 (<200字符): {len(short_content)} 条 ({len(short_content)/total*100:.1f}%)")
print(f"  中等内容 (200-1000字符): {len(medium_content)} 条 ({len(medium_content)/total*100:.1f}%)")
print(f"  长内容 (1000-5000字符): {len(long_content)} 条 ({len(long_content)/total*100:.1f}%)")
print(f"  超长内容 (>5000字符): {len(very_long_content)} 条 ({len(very_long_content)/total*100:.1f}%)")

print("\n" + "="*60)
print("极短内容样例（最新10条）")
print("="*60)
for item in short_content[:10]:
    print(f"\nID: {item['id']}")
    print(f"标题: {item['title'][:60]}")
    print(f"长度: {item['len']} 字符")
    print(f"信源等级: {item['tier']}")
    print(f"来源: {item['source']}")

print("\n" + "="*60)
print("长内容样例（最新5条）")
print("="*60)
for item in long_content[:5]:
    print(f"\nID: {item['id']}")
    print(f"标题: {item['title'][:60]}")
    print(f"长度: {item['len']} 字符")
    print(f"信源等级: {item['tier']}")
    print(f"来源: {item['source']}")

print("\n" + "="*60)
print("超长内容样例（最新5条）")
print("="*60)
for item in very_long_content[:5]:
    print(f"\nID: {item['id']}")
    print(f"标题: {item['title'][:60]}")
    print(f"长度: {item['len']} 字符")
    print(f"信源等级: {item['tier']}")
    print(f"来源: {item['source']}")

# 按来源分析
print("\n" + "="*60)
print("按来源类型分析")
print("="*60)

cursor.execute("""
    SELECT 
        source_from,
        COUNT(*) as total,
        AVG(length(content)) as avg_len,
        SUM(CASE WHEN length(content) > 1000 THEN 1 ELSE 0 END) as long_count
    FROM selected_items
    GROUP BY source_from
""")
for row in cursor.fetchall():
    print(f"\n{row['source_from']}:")
    print(f"  总数量: {row['total']}")
    print(f"  平均长度: {row['avg_len']:.0f} 字符")
    print(f"  长内容(>1000): {row['long_count']} 条")

conn.close()
print("\n" + "="*60)
