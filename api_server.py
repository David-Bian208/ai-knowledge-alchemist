"""
AI-Pulse FastAPI 服务器 - REST API + 前端静态资源服务
"""
from fastapi import FastAPI, Query, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional
import os
import logging
import json
from datetime import datetime
from api import get_items, get_daily, get_dailies, generate_rss, generate_skill_md
from src.processor import HotPipeline
from src.storage import HotStorage

app = FastAPI(title="AI-Pulse API", version="1.0.0")

# 配置日志
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# 刷新状态
_fetch_status = {
    "running": False,
    "aborting": False,
    "started_at": None,
    "completed_at": None,
    "aihot_result": None,
    "crawler_result": None,
    "total_saved": 0,
    "total_sources": 0,
    "failed_sources": [],
    "source_details": [],
    "error": None
}

# 取消事件
_fetch_cancel_event = None

# 刷新日志记录器
fetch_logger = logging.getLogger("fetch")
fetch_logger.setLevel(logging.INFO)
fetch_handler = logging.FileHandler(os.path.join(LOG_DIR, "fetch.log"), encoding="utf-8")
fetch_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
fetch_logger.addHandler(fetch_handler)

# CORS配置 - 允许前端开发服务器访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== REST API 端点 ==========

@app.get("/api/v1/list")
async def list_items(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    q: Optional[str] = None,
    mode: Optional[str] = Query("selected"),
    min_score: Optional[int] = Query(None),
    time_filter: Optional[str] = Query("week")
):
    """获取内容列表"""
    take = size
    cursor = None
    if page > 1:
        import json
        cursor = json.dumps({"offset": (page - 1) * size})
    
    result = get_items(
        mode=mode or "selected",
        since=None,
        category=category,
        q=q,
        take=take,
        cursor=cursor,
        time_filter=time_filter
    )
    
    # 前端评分过滤
    if min_score is not None:
        if "items" in result:
            result["items"] = [i for i in result["items"] if i.get("final_score", 0) >= min_score]
        result["count"] = len(result.get("items", []))
    
    return result

@app.get("/api/v1/daily")
async def daily(date: Optional[str] = None):
    """获取日报"""
    result = get_daily(date)
    return result

@app.get("/api/v1/dailies")
async def dailies(take: int = Query(30, ge=1, le=180)):
    """获取日报列表"""
    result = get_dailies(take)
    return result

@app.get("/api/v1/detail/{item_id}")
async def detail(item_id: str):
    """获取内容详情"""
    from src.storage import HotStorage
    storage = HotStorage()
    import sqlite3
    try:
        conn = storage._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM selected_items WHERE id = ?", (item_id,))
        row = cursor.fetchone()
        if row:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
        return JSONResponse(status_code=404, content={"error": "not found"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/v1/sources")
async def sources(status: str = "all"):
    """获取所有信源列表（支持按状态筛选）"""
    from src.source_manager import SourceManager
    manager = SourceManager()
    sources_list = manager.get_all_sources()
    
    result = []
    for s in sources_list:
        # Apply status filter
        if status == "enabled" and not s.enabled:
            continue
        if status == "disabled" and s.enabled:
            continue
        
        # 使用信源的direction作为category
        category = s.direction or "ai"
        
        result.append({
            "id": s.id,
            "name": s.name,
            "url": s.url,
            "tier": s.tier,
            "type": s.type,
            "enabled": s.enabled,
            "interval": s.fetch_interval,
            "description": s.description,
            "tags": s.tags,
            "category": s.direction,
            "direction": s.direction
        })
    return result

@app.get("/api/v1/rss")
async def rss(mode: str = "selected"):
    """获取RSS订阅"""
    rss_xml = generate_rss(mode=mode)
    return Response(content=rss_xml, media_type="application/xml")

@app.get("/api/v1/skill.md")
async def skill():
    """获取SKILL.md"""
    skill_md = generate_skill_md()
    return Response(content=skill_md, media_type="text/markdown")



@app.get("/api/v1/sources/unhealthy")
async def get_unhealthy_sources():
    """获取所有失效信源列表"""
    from src.source_health import SourceHealthChecker
    checker = SourceHealthChecker()
    unhealthy = checker.get_unhealthy_sources()
    return {"code": 0, "msg": "success", "data": unhealthy}

@app.delete("/api/v1/sources/{source_id}")
async def delete_source(source_id: str):
    """删除单个信源"""
    from src.source_manager import SourceManager
    manager = SourceManager()
    
    success = manager.delete_source(source_id)
    
    if success:
        return {"code": 0, "msg": "success", "data": {"deleted": True, "source_id": source_id}}
    else:
        return {"code": 404, "msg": "信源不存在", "data": {"deleted": False}}

@app.delete("/api/v1/sources/unhealthy")
async def delete_unhealthy_sources():
    """批量删除所有失效信源"""
    from src.source_manager import SourceManager
    from src.source_health import SourceHealthChecker
    
    # 获取所有失效信源
    checker = SourceHealthChecker()
    unhealthy = checker.get_unhealthy_sources()
    unhealthy_ids = [s["source_id"] for s in unhealthy]
    
    if not unhealthy_ids:
        return {"code": 0, "msg": "没有失效信源", "data": {"deleted": 0, "ids": []}}
    
    # 批量删除
    manager = SourceManager()
    deleted = manager.delete_unhealthy_sources(unhealthy_ids)
    
    return {"code": 0, "msg": "success", "data": {"deleted": deleted, "ids": unhealthy_ids}}

@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok"}

# ========== 信源健康监控 API ==========

@app.get("/api/v1/health/stats")
async def get_health_stats():
    """获取信源健康统计信息（基于sources.yaml数据源）"""
    from src.source_manager import SourceManager
    from src.storage import HotStorage
    
    manager = SourceManager()
    storage = HotStorage()
    
    # 从sources.yaml获取所有信源
    sources = manager.get_all_sources()
    total = len(sources)
    
    # 统计健康状态
    healthy = 0
    unhealthy = 0
    warning = 0
    error_distribution = {}
    
    for s in sources:
        health = storage.get_source_health(s.id)
        if health:
            if health.get('is_healthy', True):
                healthy += 1
            else:
                cf = health.get('consecutive_failures', 0)
                if cf >= 3:
                    unhealthy += 1
                else:
                    warning += 1
                # 统计错误原因
                err = health.get('last_error', '')
                if err:
                    error_distribution[err] = error_distribution.get(err, 0) + 1
        else:
            # 没有健康记录的信源视为健康（首次）
            healthy += 1
    
    success_rate = round(healthy / total * 100, 1) if total > 0 else 0
    
    return {"code": 0, "msg": "success", "data": {
        "total": total,
        "healthy": healthy,
        "warning": warning,
        "unhealthy": unhealthy,
        "success_rate": success_rate,
        "error_distribution": error_distribution
    }}

@app.get("/api/v1/health/sources")
async def get_all_source_health():
    """获取所有信源配置及健康状态（从sources.yaml读取，与信源管理一致）"""
    from src.source_manager import SourceManager
    from src.storage import HotStorage
    
    manager = SourceManager()
    storage = HotStorage()
    
    # 从sources.yaml获取所有信源
    sources = manager.get_all_sources()
    
    # 获取健康状态
    health_map = {}
    for s in sources:
        health = storage.get_source_health(s.id)
        if health:
            health_map[s.id] = health
    
    # 合并数据
    result = []
    for s in sources:
        health = health_map.get(s.id, {})
        result.append({
            "source_id": s.id,
            "source_name": s.name,
            "source_url": s.url,
            "tier": s.tier,
            "type": s.type,
            "direction": getattr(s, 'direction', None),
            "description": s.description or '',
            "tags": getattr(s, 'tags', None) or [],
            "fetch_interval": s.fetch_interval,
            "is_healthy": health.get('is_healthy', 1),
            "consecutive_failures": health.get('consecutive_failures', 0),
            "last_error": health.get('last_error', ''),
            "last_check_time": health.get('last_check_time', ''),
            "last_success_time": health.get('last_success_time', '')
        })
    
    return {"code": 0, "msg": "success", "data": result}

@app.get("/api/v1/health/logs")
async def get_health_logs(source_id: str = None, limit: int = 50):
    """获取信源健康日志"""
    from src.storage import HotStorage
    storage = HotStorage()
    logs = storage.get_source_health_logs(source_id=source_id, limit=limit)
    return {"code": 0, "msg": "success", "data": logs}

@app.post("/api/v1/health/check/{source_id}")
async def check_source_health(source_id: str):
    """手动检测单个信源健康状态"""
    from src.source_manager import SourceManager
    from src.source_health import SourceHealthChecker
    
    manager = SourceManager()
    checker = SourceHealthChecker()
    
    source = manager.get_source_by_id(source_id)
    if not source:
        return {"code": 404, "msg": "信源不存在", "data": None}
    
    result = checker.check_source(source.id, source.name, source.url, source.type)
    return {"code": 0, "msg": "success", "data": result}

# ========== AI HOT 配置 API ==========

@app.post("/api/v1/sources/{source_id}/toggle")
async def toggle_source(source_id: str, body: dict = None):
    """切换信源启用/禁用状态"""
    from src.source_manager import SourceManager
    
    if body is None:
        body = {}
    enabled = body.get("enabled", True)
    
    manager = SourceManager()
    success = manager.toggle_source(source_id, enabled)
    
    if success:
        return {"code": 0, "msg": "success", "data": {"id": source_id, "enabled": enabled}}
    else:
        return {"code": 404, "msg": "信源不存在", "data": None}

@app.post("/api/v1/sources/batch-enable")
async def batch_enable_sources(body: dict = None):
    """批量启用所有禁用的信源"""
    from src.source_manager import SourceManager
    
    manager = SourceManager()
    enabled_count = manager.batch_enable_all()
    
    return {"code": 0, "msg": "success", "data": {"enabled_count": enabled_count}}

@app.get("/api/v1/config/aihot")
async def get_aihot_config():
    """获取AI HOT开关状态"""
    from src.storage import HotStorage
    storage = HotStorage()
    enabled = storage.get_config("aihot_enabled", "true") == "true"
    return {"enabled": enabled}

@app.post("/api/v1/config/aihot")
async def set_aihot_config(enabled: bool = Query(..., description="是否开启AI HOT同步")):
    """设置AI HOT开关状态"""
    from src.storage import HotStorage
    storage = HotStorage()
    storage.set_config("aihot_enabled", "true" if enabled else "false")
    return {"enabled": enabled, "message": "AI HOT同步状态已更新"}

@app.get("/api/v1/config/sync_interval")
async def get_sync_interval_config():
    """获取自动同步间隔时间（分钟）"""
    from src.storage import HotStorage
    storage = HotStorage()
    interval = int(storage.get_config("sync_interval", "60"))
    return {"sync_interval": interval}

@app.post("/api/v1/config/sync_interval")
async def set_sync_interval_config(interval: int = Query(..., ge=1, le=1440, description="自动同步间隔时间，单位分钟，范围1~1440")):
    """设置自动同步间隔时间（分钟）"""
    from src.storage import HotStorage
    storage = HotStorage()
    storage.set_config("sync_interval", str(interval))
    return {"sync_interval": interval, "message": f"自动同步间隔已设置为{interval}分钟"}

async def _llm_generate_reason(item: dict) -> str:
    """使用LLM生成推荐理由"""
    from src.llm_client import LLMClient
    from src.config import config
    import os
    
    title = item.get('title', '')
    summary = item.get('summary', '')
    category = item.get('category', '')
    tags = item.get('tags', '[]')
    content = item.get('content', '') or item.get('full_text', '') or item.get('markdown', '') or ''
    
    category_desc = {
        'ai-models': '模型发布/更新',
        'ai-products': '产品发布/更新',
        'industry': '行业动态',
        'paper': '论文研究',
        'tip': '技巧与观点'
    }
    cat_name = category_desc.get(category, 'AI资讯')
    
    prompt = f"""你是AI行业资深编辑，请为以下内容生成一段推荐理由。

【内容信息】
标题: {title}
分类: {cat_name} ({category})
标签: {tags}
摘要: {summary}
全文: {content[:3000]}

【生成公式】
核心价值/独家信息 + 针对什么人群/解决什么痛点 + 推荐价值/行动建议

【质量要求】
1. 必须指出内容里最有价值的具体信息点，不说空话
2. 明确告诉目标读者谁该看、解决什么痛点
3. 隐含给出读了之后的收益
4. 口语化表达，像行业朋友推荐，不要用"本文阐述了""本文介绍了"这类书面语
5. 字数40-120字
6. 禁止使用"极高质量""优质内容""值得一看"等无信息量的表述
7. 每个理由必须明确对应一类目标用户

【示例参考】
- 模型类: "推理速度大幅提升，做RAG/agent服务的团队可以直接把核心链路切过去，性价比拉满。"
- 产品类: "Claude Code这次版本把可编程性和可观测性提升了一大截，做自动化脚本和监控的可以直接更新了。"
- 论文类: "这篇论文证实了顺从率从35%升到51%，做AI安全对齐的必须读。"
- 行业类: "月活突破9亿，说明AI助手已不再是少数人的玩具，产品经理应该看到这是从实验室到亿级设备的真实穿透率。"
- 技巧类: "这套Prompt技巧能让LLM写代码的准确率提升40%，开发者可以直接抄去用。"

直接输出推荐理由，不要其他内容：
"""
    
    try:
        llm = LLMClient(
            api_key=config.get("llm.api_key") or os.getenv("DEEPSEEK_API_KEY", ""),
            base_url=config.get("llm.base_url", "https://api.deepseek.com"),
            model_map={
                "cheap": config.get("llm.cheap_model", "deepseek-chat"),
                "pro": config.get("llm.pro_model", "deepseek-pro")
            }
        )
        
        reason = llm.chat(
            "只输出推荐理由，不要其他内容，40-120字。",
            prompt,
            model="cheap"
        ).strip()
        
        if len(reason) > 120:
            reason = reason[:118] + "。"
        
        return reason
    except Exception as e:
        import logging
        logging.error(f"LLM reason generation failed: {e}")
        return ""

@app.post("/api/v1/reason/{item_id}")
async def generate_reason_api(item_id: str):
    """为指定内容生成推荐理由（使用LLM）"""
    from src.storage import HotStorage
    
    storage = HotStorage()
    conn = storage._get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM selected_items WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return JSONResponse(status_code=404, content={"error": "not found"})
    
    columns = [desc[0] for desc in cursor.description]
    item = dict(zip(columns, row))
    
    reason = await _llm_generate_reason(item)
    if not reason:
        return JSONResponse(status_code=500, content={"error": "LLM generation failed"})
    
    conn2 = storage._get_conn()
    conn2.execute("UPDATE selected_items SET recommendation_reason = ? WHERE id = ?", (reason, item_id))
    conn2.commit()
    conn2.close()
    
    return {"id": item_id, "recommendation_reason": reason}

@app.post("/api/v1/fetch")
async def trigger_fetch(background_tasks: BackgroundTasks):
    """触发爬虫全量刷新 - 异步执行，不阻塞前端"""
    global _fetch_status, _fetch_cancel_event
    
    if _fetch_status["running"]:
        return {"status": "running", "message": "刷新任务已在运行中，请等待完成"}
    
    # 关键修复：每次新任务都要创建新的取消事件
    import threading
    _fetch_cancel_event = threading.Event()
    
    _fetch_status = {
        "running": True,
        "aborting": False,
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "aihot_result": None,
        "crawler_result": None,
        "total_saved": 0,
        "total_sources": 0,
        "failed_sources": [],
        "source_details": [],
        "error": None
    }
    
    fetch_logger.info("=== 全量刷新任务启动 ===")
    background_tasks.add_task(_do_fetch_full)
    return {"status": "started", "message": "后台刷新已启动，请稍后刷新页面查看结果"}

@app.post("/api/v1/fetch/abort")
async def abort_fetch():
    """中止正在运行的刷新任务"""
    global _fetch_cancel_event
    if _fetch_status["running"] and not _fetch_status["aborting"]:
        _fetch_status["aborting"] = True
        # 关键修复：设置取消事件，通知所有线程停止
        if _fetch_cancel_event:
            _fetch_cancel_event.set()
            fetch_logger.info("[中止] 用户请求中止刷新任务，已发送取消信号")
        else:
            fetch_logger.warning("[中止] 取消事件未初始化，无法发送信号")
        return {"status": "aborting", "message": "正在中止刷新任务..."}
    return {"status": "no_running_task", "message": "没有正在运行的任务"}

@app.get("/api/v1/fetch/status")
async def get_fetch_status():
    """获取刷新任务状态"""
    return _fetch_status

def _do_fetch_full():
    """后台执行全量抓取 - 双数据源并行：AI HOT同步 + 所有信息源"""
    import threading
    import time
    import traceback
    global _fetch_status, _fetch_cancel_event
    
    fetch_logger.info("开始执行全量刷新任务...")
    fetch_logger.info(f"[调试] _fetch_cancel_event 状态: is_set={_fetch_cancel_event.is_set() if _fetch_cancel_event else 'None'}")
    
    def sync_ai_hot_task():
        global _fetch_status
        try:
            fetch_logger.info("[AI HOT] 开始执行同步任务...")
            time.sleep(0.5)
            
            from src.sync_aihot import sync_items
            from src.storage import HotStorage
            
            storage = HotStorage()
            aihot_enabled = storage.get_config("aihot_enabled", "true") == "true"
            
            if not aihot_enabled:
                fetch_logger.info("[AI HOT] 同步已关闭，跳过")
                return {"saved": 0, "skipped": 0, "status": "disabled"}
            
            if _fetch_cancel_event and _fetch_cancel_event.is_set():
                fetch_logger.info("[AI HOT] 任务已中止（检测到取消信号）")
                return {"saved": 0, "status": "aborted"}
            
            fetch_logger.info("[AI HOT] 开始同步精选内容...")
            saved_selected = sync_items("selected")
            fetch_logger.info(f"[AI HOT] 精选内容同步完成，新增 {saved_selected} 条")
            time.sleep(0.3)
            
            if _fetch_cancel_event and _fetch_cancel_event.is_set():
                fetch_logger.info("[AI HOT] 任务已中止（精选后检测）")
                return {"saved": saved_selected, "status": "aborted"}
            
            fetch_logger.info("[AI HOT] 开始同步全部内容...")
            saved_all = sync_items("all")
            fetch_logger.info(f"[AI HOT] 全部内容同步完成，新增 {saved_all} 条")
            
            total_saved = saved_selected + saved_all
            fetch_logger.info(f"[AI HOT] 同步完成，共新增 {total_saved} 条内容")
            return {"saved": total_saved, "selected": saved_selected, "all": saved_all, "status": "success"}
        except Exception as e:
            fetch_logger.error(f"[AI HOT] 同步异常: {e}")
            fetch_logger.error(traceback.format_exc())
            return {"saved": 0, "status": "error", "error": str(e)}

    def crawl_all_sources_task():
        """抓取所有启用的信息源"""
        global _fetch_status
        try:
            fetch_logger.info("[步骤2] 开始执行全量信息源抓取任务...")
            
            from src.source_manager import SourceManager
            from src.rss_fetcher import RSSFetcher
            from src.crawler import WebCrawler
            from src.processor import HotPipeline
            from src.storage import HotStorage
            
            manager = SourceManager()
            all_sources = manager.get_all_enabled_sources()
            total_count = len(all_sources)
            fetch_logger.info(f"[信息源] 共找到 {total_count} 个启用的信息源")
            
            _fetch_status["total_sources"] = total_count
            
            pipeline = HotPipeline()
            storage = HotStorage()
            web_crawler = WebCrawler()
            rss_fetcher = RSSFetcher(fetch_full_content=True)
            
            total_fetched = 0
            total_saved = 0
            source_details = []
            failed_sources = []
            
            # 分离RSS源和Web源：RSS可并发抓取，Web串行处理避免反爬
            rss_sources = [s for s in all_sources if s.type == 'rss']
            web_sources = [s for s in all_sources if s.type == 'web']
            
            fetch_logger.info(f"[信息源] RSS源: {len(rss_sources)}个, Web源: {len(web_sources)}个")
            
            # 第一阶段：并发抓取RSS源数据（最多5个并发）
            rss_fetched_data = {}  # {source_name: {'entries': [...], 'error': None or str}}
            
            def fetch_rss_source(source):
                """单独抓取一个RSS源"""
                try:
                    entries = rss_fetcher.fetch_feed(source.url)
                    return source.name, entries, None
                except Exception as e:
                    return source.name, [], str(e)
            
            if rss_sources:
                import concurrent.futures
                fetch_logger.info("[RSS] 开始并发抓取...")
                executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)
                try:
                    futures = {executor.submit(fetch_rss_source, source): source for source in rss_sources}
                    completed = 0
                    for future in concurrent.futures.as_completed(futures):
                        source = futures[future]
                        completed += 1
                        if _fetch_cancel_event and _fetch_cancel_event.is_set():
                            fetch_logger.info(f"[RSS] 任务已中止，取消剩余 {len(futures) - completed} 个任务")
                            # 取消所有未完成的Future
                            for f in futures:
                                f.cancel()
                            break
                        try:
                            name, entries, error = future.result()
                            rss_fetched_data[name] = {'entries': entries, 'error': error}
                            if completed % 10 == 0 or completed == len(rss_sources):
                                fetch_logger.info(f"[RSS] 已抓取 {completed}/{len(rss_sources)} 个源")
                        except Exception as e:
                            fetch_logger.error(f"[RSS] {source.name} 异常: {e}")
                            rss_fetched_data[source.name] = {'entries': [], 'error': str(e)}
                finally:
                    executor.shutdown(wait=False, cancel_futures=True)
                
                fetch_logger.info(f"[RSS] 并发抓取完成，共 {len(rss_fetched_data)} 个源")
            
            # 第二阶段：并发抓取Web源数据（最多5个并发，带重试）
            web_fetched_data = {}  # {source_name: {'crawl_result': {...}, 'error': None or str}}
            
            from urllib.parse import urlparse
            SOCIAL_MEDIA_DOMAINS = ['x.com', 'twitter.com', 'weibo.com', 'bsky.app', 'threads.net', 'facebook.com', 'instagram.com', 'tiktok.com', 'douyin.com']
            
            def fetch_web_source(source):
                """单独抓取一个Web源（带重试）"""
                hostname = urlparse(source.url).hostname or ""
                is_social = any(d in hostname for d in SOCIAL_MEDIA_DOMAINS)
                
                if is_social:
                    return source.name, None, 'skipped_social'
                
                max_retries = 2
                for attempt in range(max_retries + 1):
                    try:
                        crawl_result = web_crawler.fetch(source.url)
                        return source.name, crawl_result, None
                    except Exception as e:
                        if attempt < max_retries:
                            time.sleep(2)
                            continue
                        else:
                            return source.name, None, str(e)
            
            if web_sources:
                import concurrent.futures
                # 过滤掉社交媒体源
                fetchable_web = [s for s in web_sources if not any(d in (urlparse(s.url).hostname or "") for d in SOCIAL_MEDIA_DOMAINS)]
                skipped_web = [s for s in web_sources if any(d in (urlparse(s.url).hostname or "") for d in SOCIAL_MEDIA_DOMAINS)]
                
                fetch_logger.info(f"[Web] 可抓取: {len(fetchable_web)}个, 跳过社交: {len(skipped_web)}个")
                fetch_logger.info("[Web] 开始并发抓取...")
                
                executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)
                try:
                    futures = {executor.submit(fetch_web_source, source): source for source in fetchable_web}
                    completed = 0
                    for future in concurrent.futures.as_completed(futures):
                        source = futures[future]
                        completed += 1
                        if _fetch_cancel_event and _fetch_cancel_event.is_set():
                            fetch_logger.info(f"[Web] 任务已中止，取消剩余 {len(futures) - completed} 个任务")
                            # 取消所有未完成的Future
                            for f in futures:
                                f.cancel()
                            break
                        try:
                            name, crawl_result, error = future.result()
                            web_fetched_data[name] = {'crawl_result': crawl_result, 'error': error}
                            if completed % 10 == 0 or completed == len(fetchable_web):
                                fetch_logger.info(f"[Web] 已抓取 {completed}/{len(fetchable_web)} 个源")
                        except Exception as e:
                            fetch_logger.error(f"[Web] {source.name} 异常: {e}")
                            web_fetched_data[source.name] = {'crawl_result': None, 'error': str(e)}
                finally:
                    executor.shutdown(wait=False, cancel_futures=True)
                
                # 社交媒体源直接标记为跳过
                for s in skipped_web:
                    web_fetched_data[s.name] = {'crawl_result': None, 'error': 'skipped_social'}
                
                fetch_logger.info(f"[Web] 并发抓取完成，共 {len(web_fetched_data)} 个源")
            
            # 第三阶段：串行处理所有源（保证SQLite线程安全）
            for i, source in enumerate(all_sources):
                if _fetch_cancel_event and _fetch_cancel_event.is_set():
                    fetch_logger.info(f"[信息源] 任务已中止，已完成 {i}/{total_count} 个信源")
                    break
                
                fetch_logger.info(f"[信息源 {i+1}/{total_count}] 正在处理: {source.name} ({source.type}, {source.tier})")
                
                source_result = {
                    "name": source.name,
                    "type": source.type,
                    "tier": source.tier,
                    "fetched": 0,
                    "saved": 0,
                    "status": "pending"
                }
                
                try:
                    if source.type == 'rss':
                        # 使用已抓取的数据
                        fetched = rss_fetched_data.get(source.name, {'entries': [], 'error': 'not found'})
                        entries = fetched.get('entries', [])
                        error = fetched.get('error')
                        
                        if error:
                            source_result["status"] = "failed"
                            source_result["error"] = error
                            failed_sources.append({
                                "name": source.name,
                                "url": source.url[:80],
                                "type": source.type,
                                "error": error[:200],
                                "is_blocked": False
                            })
                            # 信源健康记录：失败
                            storage.update_source_status(source.id, source.name, source.url, is_healthy=False, error_message=error[:200])
                        else:
                            source_result["fetched"] = len(entries)
                            
                            for entry in entries[:5]:
                                if _fetch_cancel_event and _fetch_cancel_event.is_set():
                                    break
                                eurl = entry.get('link', entry.get('url', ''))
                                if not eurl:
                                    continue
                                
                                # 存L1缓存
                                storage.save_raw_cache(eurl, json.dumps(entry, ensure_ascii=False), source.name)
                                
                                selected, result = pipeline.process_rss_entry(entry, source.tier, source.name, lightweight=True)
                                if selected:
                                    storage.save_selected_item(result)
                                    total_saved += 1
                                    source_result["saved"] += 1
                                    fetch_logger.info(f"[保存] 新增: {result.get('title', '')[:40]}...")
                                
                                total_fetched += 1
                            
                            source_result["status"] = "success"
                            # 信源健康记录：成功
                            storage.update_source_status(source.id, source.name, source.url, is_healthy=True)
                    
                    elif source.type == 'web':
                        # 使用已抓取的Web数据
                        fetched = web_fetched_data.get(source.name, {'crawl_result': None, 'error': 'not found'})
                        crawl_result = fetched.get('crawl_result')
                        error = fetched.get('error')
                        
                        if error == 'skipped_social':
                            fetch_logger.info(f"[网页] 跳过社交媒体: {source.name}")
                            source_result["fetched"] = 0
                            source_result["status"] = "skipped_social"
                        elif error:
                            source_result["status"] = "failed"
                            source_result["error"] = error
                            failed_sources.append({
                                "name": source.name,
                                "url": source.url[:80],
                                "type": source.type,
                                "error": error[:200],
                                "is_blocked": "403" in error or "401" in error or "Forbidden" in error
                            })
                            # 信源健康记录：失败
                            storage.update_source_status(source.id, source.name, source.url, is_healthy=False, error_message=error[:200])
                        elif crawl_result:
                            # 存L1缓存
                            storage.save_raw_cache(source.url, json.dumps(crawl_result.get('markdown', ''), ensure_ascii=False)[:10000], source.name)
                            
                            if crawl_result.get('title'):
                                fetch_logger.info(f"[网页] 获取到: {crawl_result.get('title', '')[:50]}...")
                                selected, result = pipeline.process_crawl_result(source.url, crawl_result, source.tier)
                                if selected:
                                    storage.save_selected_item(result)
                                    total_saved += 1
                                    source_result["saved"] += 1
                                    fetch_logger.info(f"[保存] 新增: {result.get('title', '')[:40]}...")
                                source_result["fetched"] = 1
                                total_fetched += 1
                            else:
                                fetch_logger.info(f"[网页] 未获取到有效内容")
                                source_result["fetched"] = 0
                            
                            source_result["status"] = "success"
                            # 信源健康记录：成功
                            storage.update_source_status(source.id, source.name, source.url, is_healthy=True)
                        else:
                            source_result["status"] = "failed"
                            source_result["error"] = "no data"
                            # 信源健康记录：失败（无数据）
                            storage.update_source_status(source.id, source.name, source.url, is_healthy=False, error_message="no data")
                    
                    fetch_logger.info(f"[{source.name}] 完成：抓取 {source_result['fetched']} 条，新增 {source_result['saved']} 条")
                    
                except Exception as e:
                    error_msg = str(e)
                    source_result["status"] = "failed"
                    source_result["error"] = error_msg
                    
                    is_blocked = "403" in error_msg or "401" in error_msg or "Forbidden" in error_msg or "blocked" in error_msg.lower()
                    if is_blocked:
                        fetch_logger.error(f"[{source.name}] 反爬/403: {error_msg}")
                    else:
                        fetch_logger.error(f"[{source.name}] 失败: {error_msg}")
                    
                    failed_sources.append({
                        "name": source.name,
                        "url": source.url[:80],
                        "type": source.type,
                        "error": error_msg[:200],
                        "is_blocked": is_blocked
                    })
                    # 信源健康记录：异常
                    storage.update_source_status(source.id, source.name, source.url, is_healthy=False, error_message=error_msg[:200])
                
                source_details.append(source_result)
            
            # 更新状态
            _fetch_status["source_details"] = source_details
            _fetch_status["failed_sources"] = failed_sources
            
            fetch_logger.info(f"[信息源同步完成] 共抓取 {total_fetched} 条，新增 {total_saved} 条")
            if failed_sources:
                fetch_logger.info(f"[失败信源] 共 {len(failed_sources)} 个信源抓取失败")
                for fs in failed_sources:
                    fetch_logger.info(f"  - {fs['name']}: {fs['error'][:100]}")
            
            return {"fetched": total_fetched, "saved": total_saved, "status": "success", "source_details": source_details, "failed_sources": failed_sources}
        except Exception as e:
            fetch_logger.error(f"[信息源同步失败] {e}")
            import traceback
            fetch_logger.error(traceback.format_exc())
            return {"fetched": 0, "saved": 0, "status": "error", "error": str(e)}
    
    try:
        import threading
        from src.storage import HotStorage
        storage = HotStorage()
        aihot_enabled = storage.get_config("aihot_enabled", "true") == "true"
        
        threads = []
        results = {"aihot": None, "crawler": None}
        
        # AI HOT 同步
        if aihot_enabled:
            fetch_logger.info("[AI HOT] 开始同步...")
            def sync_task():
                results["aihot"] = sync_ai_hot_task()
            t1 = threading.Thread(target=sync_task)
            threads.append(t1)
            t1.start()
        else:
            fetch_logger.info("[AI HOT] 已关闭，跳过")
            results["aihot"] = {"saved": 0, "status": "disabled"}
        
        # 全量信息源爬虫
        fetch_logger.info("[信息源] 开始抓取...")
        def crawl_task():
            results["crawler"] = crawl_all_sources_task()
        t2 = threading.Thread(target=crawl_task)
        threads.append(t2)
        t2.start()
        
        # 等待所有任务完成（带中止检查）
        for t in threads:
            # 每1秒检查一次中止状态
            while t.is_alive():
                t.join(timeout=1.0)
                if _fetch_cancel_event and _fetch_cancel_event.is_set():
                    fetch_logger.info("[全局] 检测到中止信号，等待线程退出...")
                    break
        
        # 汇总结果
        total_saved = 0
        if results["aihot"] and results["aihot"].get("status") == "success":
            total_saved += results["aihot"].get("saved", 0)
        if results["crawler"] and results["crawler"].get("status") == "success":
            total_saved += results["crawler"].get("saved", 0)
        
        # 判断是否被中止
        is_aborted = _fetch_cancel_event and _fetch_cancel_event.is_set()
        if is_aborted:
            fetch_logger.info("=== 刷新任务已中止 ===")
        else:
            fetch_logger.info(f"=== 刷新任务完成 === 总共新增 {total_saved} 条内容")
        
        _fetch_status["running"] = False
        _fetch_status["completed_at"] = datetime.now().isoformat()
        _fetch_status["aihot_result"] = results.get("aihot")
        _fetch_status["crawler_result"] = results.get("crawler")
        _fetch_status["total_saved"] = total_saved
        _fetch_status["aborting"] = False
        
        fetch_logger.info(f"AI HOT 结果: {results.get('aihot')}")
        fetch_logger.info(f"信息源结果: {results.get('crawler')}")
        
        # 更新后自动生成日报（如果开启了该功能）
        auto_generate = storage.get_config("auto_generate_report", "true") == "true"
        if auto_generate and not is_aborted:
            try:
                from datetime import timedelta
                today = datetime.now().strftime("%Y-%m-%d")
                fetch_logger.info(f"[日报] 更新完成，正在生成当日日报: {today}")
                from src.daily_generator import generate_daily_report
                report_result = generate_daily_report(today, storage, force=True)
                if report_result.get("code") == 0:
                    fetch_logger.info(f"[日报] 生成成功: {report_result.get('data', {}).get('total', 0)} 条内容")
                else:
                    fetch_logger.info(f"[日报] 生成失败或跳过: {report_result.get('message', '')}")
            except Exception as e:
                fetch_logger.error(f"[日报] 自动生成异常: {e}")
    
    except Exception as e:
        _fetch_status["running"] = False
        _fetch_status["aborting"] = False
        _fetch_status["error"] = str(e)
        _fetch_status["completed_at"] = datetime.now().isoformat()
        fetch_logger.error(f"刷新任务异常: {e}")
        import traceback
        fetch_logger.error(traceback.format_exc())

@app.get("/api/v1/fetch/logs")
async def get_fetch_logs(lines: int = 50):
    """获取刷新日志"""
    log_file = os.path.join(LOG_DIR, "fetch.log")
    try:
        if not os.path.exists(log_file):
            return {"logs": [], "message": "暂无日志"}
        
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
        
        # 返回最后 N 行
        recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        return {"logs": [line.strip() for line in recent_lines], "total": len(all_lines)}
    except Exception as e:
        return {"logs": [], "error": str(e)}

@app.post("/api/v1/reasons/batch")
async def batch_generate_reasons_api():
    """为数据库中所有没有推荐理由的内容批量生成"""
    from src.storage import HotStorage
    
    storage = HotStorage()
    conn = storage._get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM selected_items WHERE recommendation_reason IS NULL OR recommendation_reason = '' LIMIT 50")
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return {"generated": 0, "message": "所有内容已有推荐理由"}
    
    generated = 0
    for row in rows:
        item_id = row[0]
        conn2 = storage._get_conn()
        c2 = conn2.cursor()
        c2.execute("SELECT * FROM selected_items WHERE id = ?", (item_id,))
        r = c2.fetchone()
        conn2.close()
        
        if r:
            cols = [desc[0] for desc in c2.description]
            item = dict(zip(cols, r))
            reason = await _llm_generate_reason(item)
            if reason:
                conn3 = storage._get_conn()
                conn3.execute("UPDATE selected_items SET recommendation_reason = ? WHERE id = ?", (reason, item_id))
                conn3.commit()
                conn3.close()
                generated += 1
    
    return {"generated": generated, "total": len(rows)}

@app.post("/api/v1/process-url")
async def process_url(request: Request):
    """处理URL并入库"""
    from src.processor import HotPipeline
    from src.storage import HotStorage
    import json
    
    body = await request.json()
    url = body.get("url", "")
    tier = body.get("tier", "T2")
    
    if not url or not url.startswith("http"):
        return JSONResponse(status_code=400, content={"error": "无效的URL"})
    
    try:
        pipeline = HotPipeline()
        selected, result = pipeline.process_url(url, tier)
        
        return {
            "selected": selected,
            "title": result.get("title", ""),
            "source": result.get("source", ""),
            "final_score": result.get("final_score", 0),
            "url": url
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={
            "error": str(e),
            "selected": False,
            "final_score": 0
        })

# ========== 日报模块 API ==========

@app.get("/api/v1/daily/check")
async def check_daily_ready(date: str = Query(None, description="检查日期 YYYY-MM-DD，不传默认昨天")):
    """检查指定日期是否可以生成日报（精选内容≥10条）"""
    try:
        from src.daily_generator import check_daily_report_ready
        storage = HotStorage()
        result = check_daily_report_ready(date, storage)
        return result
    except Exception as e:
        return {"ready": False, "count": 0, "message": str(e)}

@app.post("/api/v1/daily/generate")
async def generate_daily(request: Request):
    """手动生成日报（支持覆盖已有日报）"""
    try:
        body = await request.json()
        date_str = body.get("date", "")
        force = body.get("force", False)
        
        if not date_str:
            date_str = (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)).strftime("%Y-%m-%d")
        
        from src.daily_generator import generate_daily_report
        storage = HotStorage()
        result = generate_daily_report(date_str, storage, force=force)
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"code": -1, "message": str(e)}

@app.get("/api/v1/daily/config")
async def get_daily_config():
    """获取日报生成配置"""
    try:
        storage = HotStorage()
        return {
            "code": 0,
            "data": {
                "auto_enabled": storage.get_config("daily_auto_enabled", "false") == "true",
                "daily_time": int(storage.get_config("daily_time", "8"))
            }
        }
    except Exception as e:
        return {"code": -1, "message": str(e)}

@app.post("/api/v1/daily/config")
async def set_daily_config(request: Request):
    """保存日报生成配置"""
    try:
        body = await request.json()
        storage = HotStorage()
        if "auto_enabled" in body:
            storage.set_config("daily_auto_enabled", "true" if body["auto_enabled"] else "false")
        if "daily_time" in body:
            storage.set_config("daily_time", str(body["daily_time"]))
        return {"code": 0, "message": "保存成功"}
    except Exception as e:
        return {"code": -1, "message": str(e)}

# ========== 统一更新配置 API ==========

@app.get("/api/v1/update/config")
async def get_update_config():
    """获取统一更新配置"""
    try:
        storage = HotStorage()
        return {
            "code": 0,
            "data": {
                "interval_enabled": storage.get_config("interval_enabled", "false") == "true",
                "sync_interval": int(storage.get_config("sync_interval", "60")),
                "scheduled_enabled": storage.get_config("scheduled_enabled", "true") == "true",
                "scheduled_time": int(storage.get_config("scheduled_time", "8")),
                "auto_generate_report": storage.get_config("auto_generate_report", "true") == "true"
            }
        }
    except Exception as e:
        return {"code": -1, "message": str(e)}

@app.post("/api/v1/update/config")
async def set_update_config(request: Request):
    """保存统一更新配置"""
    try:
        body = await request.json()
        storage = HotStorage()
        if "interval_enabled" in body:
            storage.set_config("interval_enabled", "true" if body["interval_enabled"] else "false")
        if "sync_interval" in body:
            storage.set_config("sync_interval", str(body["sync_interval"]))
        if "scheduled_enabled" in body:
            storage.set_config("scheduled_enabled", "true" if body["scheduled_enabled"] else "false")
        if "scheduled_time" in body:
            storage.set_config("scheduled_time", str(body["scheduled_time"]))
        if "auto_generate_report" in body:
            storage.set_config("auto_generate_report", "true" if body["auto_generate_report"] else "false")
        return {"code": 0, "message": "保存成功"}
    except Exception as e:
        return {"code": -1, "message": str(e)}

# ========== 下载模块 API ==========

@app.get("/api/v1/download/config")
async def get_download_config():
    """获取下载配置"""
    storage = HotStorage()
    return {
        "code": 0,
        "data": {
            "save_path": storage.get_config("download_save_path", "~/My_Knowledge_Base/Inbox"),
            "l1_retention_days": int(storage.get_config("l1_retention_days", "7"))
        }
    }

@app.post("/api/v1/download/config")
async def set_download_config(request: Request):
    """保存下载配置"""
    try:
        body = await request.json()
        storage = HotStorage()
        if "save_path" in body:
            storage.set_config("download_save_path", body["save_path"])
        if "l1_retention_days" in body:
            storage.set_config("l1_retention_days", str(body["l1_retention_days"]))
        return {"code": 0, "message": "保存成功"}
    except Exception as e:
        return {"code": -1, "message": str(e)}

@app.post("/api/v1/cache/l1/clean")
async def clean_l1_cache(request: Request):
    """清理L1缓存"""
    try:
        body = await request.json()
        clean_all = body.get("clean_all", False)
        storage = HotStorage()
        if clean_all:
            count = storage.clean_raw_cache_all()
            return {"code": 0, "data": {"clean_count": count}}
        else:
            retention_days = int(storage.get_config("l1_retention_days", "7"))
            count = storage.clean_raw_cache_expired(retention_days)
            return {"code": 0, "data": {"clean_count": count}}
    except Exception as e:
        return {"code": -1, "message": str(e)}

@app.post("/api/v1/download/mark")
async def mark_downloaded(request: Request):
    """标记内容为已下载"""
    try:
        body = await request.json()
        article_ids = body.get("article_ids", [])
        storage = HotStorage()
        count = storage.mark_downloaded(article_ids)
        return {"code": 0, "data": {"marked_count": count}}
    except Exception as e:
        return {"code": -1, "message": str(e)}

@app.get("/api/v1/download/status")
async def get_download_status(article_ids: str = Query(..., description="逗号分隔的文章ID")):
    """获取下载状态"""
    try:
        ids = [int(x.strip()) for x in article_ids.split(",") if x.strip()]
        storage = HotStorage()
        status = storage.get_download_status(ids)
        return {"code": 0, "data": status}
    except Exception as e:
        return {"code": -1, "message": str(e)}

@app.post("/api/v1/download/zip")
async def download_zip(request: Request):
    """下载Markdown文件 - 单个文章返回.md，多个文章返回包含.md的ZIP，同时保存到用户配置的目录"""
    import io
    import zipfile
    import re
    import os
    
    try:
        body = await request.json()
        article_ids = body.get("article_ids", [])
        
        if len(article_ids) > 100:
            return JSONResponse(status_code=400, content={"code": -1, "message": "单次最多选择100篇内容下载"})
        
        if not article_ids:
            return JSONResponse(status_code=400, content={"code": -1, "message": "请选择要下载的内容"})
        
        storage = HotStorage()
        
        # 获取用户配置的保存路径
        save_path = storage.get_config("download_save_path")
        if save_path:
            # 补全路径（如果用户输入的是相对路径）
            if not save_path.startswith("/"):
                save_path = "/" + save_path
            # 测试路径是否可写
            try:
                os.makedirs(save_path, exist_ok=True)
                # 测试写入权限
                test_file = os.path.join(save_path, ".write_test")
                with open(test_file, 'w') as f:
                    f.write('')
                os.remove(test_file)
            except (OSError, PermissionError) as e:
                # 如果配置的目录不可写（如Desktop只读），使用备用路径
                logging.warning(f"配置路径不可写: {save_path}, 错误: {e}")
                save_path = "/tmp/ai_pulse_downloads"
                os.makedirs(save_path, exist_ok=True)
        else:
            save_path = "/tmp/ai_pulse_downloads"
            os.makedirs(save_path, exist_ok=True)
        
        downloaded_ids = storage.get_downloaded_ids(article_ids)
        ids_to_download = [aid for aid in article_ids if aid not in downloaded_ids]
        
        if not ids_to_download:
            return JSONResponse(status_code=200, content={"code": 0, "message": "所选内容已全部下载过，无需重复下载", "skipped": len(article_ids)})
        
        items = storage.get_items_for_download(ids_to_download)
        if not items:
            return JSONResponse(status_code=404, content={"code": -1, "message": "未找到指定内容"})
        
        storage.mark_downloaded([item["id"] for item in items])
        
        def build_markdown(item):
            tags = []
            if item.get("tags"):
                try:
                    tags = json.loads(item["tags"]) if isinstance(item["tags"], str) else item["tags"]
                except:
                    tags = []
            
            # 优先使用 full_content（完整正文），没有则使用 summary（摘要）
            full_content = item.get("full_content")
            summary = item.get("summary")
            content = full_content if full_content and len(full_content) > 200 else summary or full_content or ""
            
            # 抓取时间 = created_at 字段
            crawl_date = ""
            if item.get("created_at"):
                try:
                    crawl_date = str(item["created_at"])[:10]
                except:
                    pass
            
            yaml_header = f"""---
title: "{item.get('title', '')}"
url: "{item.get('url', '')}"
source: "{item.get('source', '')}"
publish_date: "{item.get('publish_date', '')}"
crawl_date: "{crawl_date}"
tier: "{item.get('source_tier', '')}"
category: "{item.get('category', '')}"
score: {int(item.get('final_score', 0))}
tags: [{', '.join(f'"{t}"' for t in tags)}]
---

"""
            return yaml_header + content
        
        def make_filename(item):
            pub_date = item.get("publish_date", "")[:10] if item.get("publish_date") else "unknown"
            keywords = re.sub(r'[^\w\u4e00-\u9fff]', '_', item.get('title', '')[:40])[:40]
            return f"{pub_date}_{keywords}.md"
        
        # 先保存到用户配置的目录
        if save_path:
            for item in items:
                md_content = build_markdown(item)
                filename = make_filename(item)
                file_path = os.path.join(save_path, filename)
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(md_content)
                except Exception as e:
                    logging.warning(f"保存文件失败 {file_path}: {e}")
        
        # 单个文章：直接下载.md文件
        if len(items) == 1:
            item = items[0]
            md_content = build_markdown(item)
            filename = make_filename(item)
            
            from urllib.parse import quote
            
            # 纯ASCII文件名
            safe_title = re.sub(r'[^\x00-\x7F]', '', item.get('title', '')[:30])[:30]
            safe_title = re.sub(r'[^\w]', '_', safe_title) or "article"
            ascii_filename = f"{item.get('publish_date', '')[:10] or 'unknown'}_{safe_title}.md"
            
            saved_path_full = os.path.join(save_path, filename) if save_path else ""
            # HTTP headers必须是ASCII，对中文路径进行URL编码
            saved_path_encoded = quote(saved_path_full.encode('utf-8'), safe='') if saved_path_full else ""
            
            from fastapi.responses import Response
            resp = Response(
                content=md_content.encode("utf-8"),
                media_type="text/markdown; charset=utf-8"
            )
            resp.headers["Content-Disposition"] = f'attachment; filename="{ascii_filename}"'
            resp.headers["X-Saved-Path"] = saved_path_encoded
            return resp
        
        # 多个文章：打包为ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for item in items:
                md_content = build_markdown(item)
                filename = make_filename(item)
                zf.writestr(filename, md_content.encode("utf-8"))
        
        zip_buffer.seek(0)
        
        from fastapi.responses import StreamingResponse
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename=ai_pulse_download.zip',
                "X-Saved-Path": save_path or ""
            }
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"code": -1, "message": str(e)})

# ========== 前端静态资源服务 ==========

# 前端构建产物目录
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "frontend", "dist")

# 挂载静态资源
app.mount("/static", StaticFiles(directory=os.path.join(FRONTEND_DIST, "static")), name="static")

@app.get("/")
async def serve_frontend():
    """提供前端主页"""
    return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))

# SPA路由回退：所有非API GET路径返回index.html
@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    """SPA路由支持 - 所有非API路径返回index.html"""
    # 排除API路径
    if full_path.startswith("api/") or full_path.startswith("health"):
        return JSONResponse(status_code=404, content={"error": "not found"})
    
    index_file = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return JSONResponse(status_code=404, content={"error": "frontend not built"})

# ========== 定时任务初始化 ==========
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

if __name__ == "__main__":
    import uvicorn
    import sys
    port = 8887
    if "--port" in sys.argv:
        idx = sys.argv.index("--port")
        if idx + 1 < len(sys.argv):
            port = int(sys.argv[idx + 1])
    print("🚀 AI-Pulse 服务启动中...")
    print(f"   API: http://localhost:{port}/api/v1/...")
    if os.path.exists(FRONTEND_DIST):
        print(f"   前端: http://localhost:{port}/")
    uvicorn.run(app, host="0.0.0.0", port=port)
