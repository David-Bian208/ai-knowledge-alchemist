#!/usr/bin/env python3
"""测试脚本：验证sync_aihot的修复效果"""
import sys
import os
import logging

# 禁用详细日志
logging.disable(logging.WARNING)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.sync_aihot import sync_items
from src.storage import HotStorage

print("="*60)
print("测试AI HOT同步 - 验证正文抓取修复")
print("="*60)

# 运行同步
print("\n运行sync_items('selected')...\n")
saved = sync_items("selected")

print(f"\n{'='*60}")
print(f"同步完成: 新增 {saved} 条")
print(f"{'='*60}")

# 检查最新入库的文章内容
print("\n检查最新入库的5条文章内容...")
print("="*60)

storage = HotStorage()
conn = storage._get_conn()
conn.row_factory = lambda c, r: {col[0]: r[idx] for idx, col in enumerate(c.description)}
cursor = conn.cursor()
cursor.execute("""
    SELECT id, title, source, length(content) as content_len, 
           substr(content, 1, 100) as content_preview
    FROM selected_items 
    ORDER BY created_at DESC 
    LIMIT 5
""")

rows = cursor.fetchall()
for row in rows:
    print(f"\nID: {row['id']}")
    print(f"标题: {row['title'][:60]}")
    print(f"来源: {row['source']}")
    print(f"内容长度: {row['content_len']} 字符")
    print(f"内容预览: {row['content_preview'][:80]}...")
    
    # 判断是否有实质内容
    if row['content_len'] and row['content_len'] > 200:
        print("状态: ✅ 有正文")
    elif row['content_len'] and row['content_len'] > 50:
        print("状态: ⚠️ 内容过短")
    else:
        print("状态: ❌ 无正文/仅链接")

conn.close()
print("\n" + "="*60)
print("测试完成")
print("="*60)
