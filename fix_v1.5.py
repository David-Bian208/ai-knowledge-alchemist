#!/usr/bin/env python3
"""AI-Pulse v1.5 定时任务修复脚本"""
import os

WORKSPACE = "/home/admin/.openclaw/workspace/behavior_recorder_service/ai-pulse"
os.chdir(WORKSPACE)

# ========== 修复 1: api_server.py 添加定时任务初始化 ==========
print("🔧 修复 1: api_server.py 添加定时任务初始化...")

with open('api_server.py', 'r') as f:
    content = f.read()

scheduler_code = '''# ========== 定时任务初始化 ==========
from src.scheduler import DailyScheduler

# 创建定时任务实例
_scheduler = DailyScheduler(hour=8, minute=0)

@app.on_event("startup")
async def startup_event():
    """服务启动时初始化定时任务"""
    print("🔧 正在初始化定时任务...")
    storage = HotStorage()
    llm_config = {
        "model": "deepseek-chat",
        "api_key": os.getenv("DEEPSEEK_API_KEY", "")
    }
    _scheduler.start(storage=storage, llm_config=llm_config)
    print("✅ 定时任务初始化完成")

@app.on_event("shutdown")
async def shutdown_event():
    """服务关闭时停止定时任务"""
    print("🛑 正在停止定时任务...")
    _scheduler.stop()
    print("✅ 定时任务已停止")

'''

if 'if __name__ == "__main__":' in content and 'startup_event' not in content:
    content = content.replace('if __name__ == "__main__":', scheduler_code + 'if __name__ == "__main__":')
    with open('api_server.py', 'w') as f:
        f.write(content)
    print("✅ api_server.py 已添加定时任务初始化代码")
else:
    print("⚠️  api_server.py 可能已修复或无需修复")

# ========== 修复 2: 创建 src/fetch.py ==========
print("\n🔧 修复 2: 创建 src/fetch.py...")

fetch_code = '''"""
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
'''

if not os.path.exists('src/fetch.py'):
    with open('src/fetch.py', 'w') as f:
        f.write(fetch_code)
    print("✅ src/fetch.py 已创建")
else:
    print("⚠️  src/fetch.py 已存在")

# ========== 修复 3: src/scheduler.py 时间解析逻辑 ==========
print("\n🔧 修复 3: src/scheduler.py 时间解析逻辑...")

with open('src/scheduler.py', 'r') as f:
    content = f.read()

old_code = 'scheduled_hour = int(storage.get_config("scheduled_time", "8"))'
new_code = '''scheduled_time_str = storage.get_config("scheduled_time", "08:00")
            if ":" in str(scheduled_time_str):
                scheduled_hour = int(scheduled_time_str.split(":")[0])
                scheduled_minute = int(scheduled_time_str.split(":")[1])
            else:
                scheduled_hour = int(scheduled_time_str)
                scheduled_minute = 0'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open('src/scheduler.py', 'w') as f:
        f.write(content)
    print("✅ src/scheduler.py 时间解析逻辑已修复")
else:
    print("⚠️  src/scheduler.py 可能已修复或无需修复")

print("\n✅ 所有修复已完成！")
