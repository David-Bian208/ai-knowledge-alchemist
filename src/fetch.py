"""
数据抓取模块 - 双数据源并行抓取
"""
import threading
from typing import Dict, Any
from src.crawler import WebCrawler
from src.sync_aihot import sync_items
from src.storage import HotStorage
from src.dedup import DeduplicationService

def quick_fetch_task() -> Dict[str, Any]:
    """
    快速抓取任务 - 抓取所有信息源
    返回：抓取结果统计
    """
    try:
        storage = HotStorage()
        dedup = DeduplicationService()
        dedup.load_existing_urls(storage)
        
        crawler = WebCrawler()
        
        # 从配置获取信息源列表
        sources = storage.get_config("sources", "[]")
        if isinstance(sources, str):
            import json
            sources = json.loads(sources)
        
        fetched = 0
        saved = 0
        
        for source in sources:
            url = source.get("url")
            if url:
                try:
                    result = crawler.fetch(url)
                    if result.get("success"):
                        fetched += 1
                        if result.get("saved"):
                            saved += 1
                except Exception as e:
                    print(f"[抓取] {url} 失败：{e}")
        
        print(f"[抓取] 完成：抓取 {fetched} 条，新增 {saved} 条")
        return {"fetched": fetched, "saved": saved, "status": "success"}
    except Exception as e:
        print(f"[抓取] 失败：{e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

def full_fetch_task() -> Dict[str, Any]:
    """
    完整抓取任务 - 包含 AI HOT 同步 + 信息源抓取
    返回：抓取结果统计
    """
    storage = HotStorage()
    aihot_enabled = storage.get_config("aihot_enabled", "true") == "true"
    
    threads = []
    results = {"aihot": None, "crawler": None}
    
    # AI HOT 同步
    if aihot_enabled:
        def sync_aihot():
            try:
                saved_selected = sync_items("selected")
                saved_all = sync_items("all")
                results["aihot"] = {"saved": saved_selected + saved_all}
            except Exception as e:
                results["aihot"] = {"error": str(e)}
        
        t = threading.Thread(target=sync_aihot)
        threads.append(t)
        t.start()
    
    # 信息源抓取
    def sync_crawler():
        try:
            results["crawler"] = quick_fetch_task()
        except Exception as e:
            results["crawler"] = {"error": str(e)}
    
    t = threading.Thread(target=sync_crawler)
    threads.append(t)
    t.start()
    
    # 等待所有任务完成
    for t in threads:
        t.join()
    
    return results
