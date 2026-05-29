"""
历史内容正文回填脚本
批量为数据库中没有正文的历史内容重新抓取完整正文
使用改进后的高可靠性爬虫（多引擎降级+重试）
"""
import sys
import os
import time
import sqlite3
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.crawler import WebCrawler
from src.storage import HotStorage

# 配置
BATCH_SIZE = 5              # 每批处理5条，避免一次性太多
DELAY_BETWEEN = 2           # 每条之间延迟2秒，避免被封
MAX_CONTENT_LEN = 50000     # 正文最大长度

# 必须跳过的域名
SKIP_DOMAINS = ['x.com', 'twitter.com', 'weibo.com', 'bsky.app', 'threads.net']

def backfill_content(limit=None, source_from=None, dry_run=False):
    """回填历史内容正文
    
    Args:
        limit: 限制处理条数，None表示全部
        source_from: 只处理指定来源，None表示全部
        dry_run: 仅打印计划，不实际执行
    """
    storage = HotStorage()
    crawler = WebCrawler(use_gallery_dl=True, use_media_crawler=True)
    
    # 查询没有正文的内容
    query = """
        SELECT id, url, title, source_from, content, full_content 
        FROM selected_items 
        WHERE (
            (content IS NULL OR length(content) < 50) 
            AND (full_content IS NULL OR length(full_content) < 50)
        )
        OR (
            -- 检测HTML链接-only的内容（RSS源常见问题）
            content LIKE '%<a href%' AND length(content) < 500
        )
        OR (
            -- 检测内容过短（<200字符）且不是社交媒体的内容
            length(content) < 200 
            AND source_from != 'aihot'
            AND source_from NOT LIKE '%twitter%'
            AND source_from NOT LIKE '%x.com%'
        )
    """
    params = []
    
    if source_from:
        query += " AND source_from = ?"
        params.append(source_from)
    
    query += " ORDER BY id DESC"
    
    if limit:
        query += " LIMIT ?"
        params.append(limit)
    
    conn = sqlite3.connect(storage.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(query, params)
    items = cursor.fetchall()
    
    total = len(items)
    print(f"\n{'='*60}")
    print(f"正文回填任务")
    print(f"{'='*60}")
    print(f"找到 {total} 条无正文的历史内容")
    if source_from:
        print(f"来源筛选: {source_from}")
    if dry_run:
        print(f"模式: 试运行（不会实际保存）")
    print(f"{'='*60}\n")
    
    if total == 0:
        print("没有需要回填的内容，退出")
        return
    
    success_count = 0
    fail_count = 0
    skip_count = 0
    fallback_count = 0
    
    for i, item in enumerate(items):
        item_id = item['id']
        url = item['url']
        title = item['title'][:40]
        source = item['source_from']
        
        print(f"[{i+1}/{total}] ID={item_id} [{source}] {title}...")
        print(f"  URL: {url[:70]}")
        
        if any(d in url.lower() for d in SKIP_DOMAINS):
            print(f"  跳过: 社交媒体链接，无法抓取")
            skip_count += 1
            continue
        
        if dry_run:
            print(f"  [试运行] 将尝试抓取")
            continue
        
        try:
            result = crawler.fetch(url)
            
            if result.get('success'):
                content = result.get('markdown', '')
                if len(content) > MAX_CONTENT_LEN:
                    content = content[:MAX_CONTENT_LEN] + "\n\n[内容过长已截断]"
                
                if len(content) < 50:
                    print(f"  抓取成功但内容过短 ({len(content)}字符)，跳过")
                    skip_count += 1
                    continue
                
                cursor.execute("""
                    UPDATE selected_items 
                    SET full_content = ?, content = ?
                    WHERE id = ?
                """, (content, content, item_id))
                conn.commit()
                
                print(f"  成功: 正文 {len(content)} 字符")
                success_count += 1
            else:
                error = result.get('error', '未知错误')
                print(f"  失败: {error}")
                fail_count += 1
                
        except Exception as e:
            print(f"  异常: {e}")
            fail_count += 1
        
        if i < total - 1:
            time.sleep(DELAY_BETWEEN)
    
    conn.close()
    
    print(f"\n{'='*60}")
    print(f"回填完成")
    print(f"{'='*60}")
    print(f"  成功: {success_count} 条")
    print(f"  失败: {fail_count} 条")
    print(f"  跳过: {skip_count} 条")
    print(f"  总计: {total} 条")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="历史内容正文回填脚本")
    parser.add_argument("--limit", type=int, help="限制处理条数")
    parser.add_argument("--source", help="只处理指定来源 (aihot/original)")
    parser.add_argument("--dry-run", action="store_true", help="试运行模式，不实际保存")
    
    args = parser.parse_args()
    
    backfill_content(
        limit=args.limit,
        source_from=args.source,
        dry_run=args.dry_run
    )
