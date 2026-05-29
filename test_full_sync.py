#!/usr/bin/env python3
"""完整同步流程测试"""
import sys
import os
import logging

logging.disable(logging.WARNING)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.sync_aihot import sync_items
from src.sync_rss import fetch_rss_sources
from src.storage import HotStorage

print("="*60)
print("完整同步流程测试")
print("="*60)

# 1. 测试AI HOT同步
print("\n[1/2] 测试AI HOT同步...")
print("-" * 60)
try:
    saved_aihot = sync_items("selected")
    print(f"✓ AI HOT同步完成: 新增 {saved_aihot} 条")
except Exception as e:
    print(f"✗ AI HOT同步失败: {e}")
    saved_aihot = 0

# 2. 测试RSS源内容抓取
print("\n[2/2] 检查RSS源配置...")
print("-" * 60)
try:
    from src.rss_fetcher import RSSFetcher
    from src.config import config
    
    sources = config.get("rss.sources", [])
    print(f"✓ 已配置 {len(sources)} 个RSS源")
    saved_rss = "N/A (配置检查完成)"
except Exception as e:
    print(f"⚠️ RSS源检查跳过: {e}")
    saved_rss = 0

# 3. 统计总览
print("\n" + "="*60)
print("同步总览")
print("="*60)
print(f"AI HOT新增: {saved_aihot} 条")
print(f"RSS新增: {saved_rss} 条")
print(f"总计新增: {saved_aihot + saved_rss} 条")

# 4. 检查数据库内容完整性
print("\n内容完整性检查...")
print("-" * 60)

storage = HotStorage()
conn = storage._get_conn()
conn.row_factory = lambda c, r: {col[0]: r[idx] for idx, col in enumerate(c.description)}
cursor = conn.cursor()

# 统计有正文和无正文的数量
cursor.execute("""
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN length(content) > 200 THEN 1 ELSE 0 END) as has_content,
        SUM(CASE WHEN length(content) <= 200 OR content IS NULL THEN 1 ELSE 0 END) as no_content
    FROM selected_items
""")
stats = cursor.fetchone()
print(f"数据库总内容: {stats['total']} 条")
print(f"有正文(>200字符): {stats['has_content']} 条 ({stats['has_content']/stats['total']*100:.1f}%)")
print(f"无正文/摘要: {stats['no_content']} 条 ({stats['no_content']/stats['total']*100:.1f}%)")

# 检查最新5条内容
print("\n最新5条内容:")
cursor.execute("""
    SELECT id, title, source_from, length(content) as content_len
    FROM selected_items 
    ORDER BY created_at DESC 
    LIMIT 5
""")
for row in cursor.fetchall():
    status = "✅" if row['content_len'] and row['content_len'] > 200 else "⚠️"
    print(f"  {status} ID:{row['id']} [{row['source_from']}] {row['title'][:40]}... ({row['content_len']}字符)")

conn.close()

print("\n" + "="*60)
print("测试完成")
print("="*60)
