"""
SQLite存储模块 - AIHOT架构版本
用于保存精选内容、信源日志、处理记录等
"""
import os
import json
import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.config import config

logger = logging.getLogger(__name__)


class HotStorage:
    """AI热点数据持久化存储"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = config.get("storage.db_path", "data/hot_pulse.db")
        self.db_path = db_path
        self._ensure_db_directory()
        self._init_db()

    def _ensure_db_directory(self):
        """确保数据库所在目录存在"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=DELETE")  # Use DELETE mode to avoid WAL corruption
        return conn

    def _init_db(self):
        """初始化数据库表"""
        conn = self._get_conn()
        cursor = conn.cursor()

        # 精选内容表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS selected_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE,
                title TEXT,
                source TEXT,
                source_tier TEXT,  -- T1/T1.5/T2
                author TEXT,
                
                -- 分类字段（对齐AIHOT的5个分类）
                category TEXT,  -- ai-models/ai-products/industry/paper/tip
                
                -- 时间字段（双时间戳）
                publish_date TEXT,  -- 原文发布时间（ISO-8601）
                ingested_at TIMESTAMP,  -- 录入系统时间（自动设置）
                
                final_score REAL,
                selected INTEGER DEFAULT 0,
                
                -- 5维评分
                timeliness REAL,
                importance REAL,
                scarcity REAL,
                practicality REAL,
                relevance REAL,
                
                -- 预筛结果
                pre_screen_reason TEXT,
                
                -- AI生成的摘要
                summary TEXT,
                
                -- 标签系统（JSON数组，如 ["Anthropic", "MCP/工具", "产品更新", "部署/工程"]）
                tags TEXT,  -- JSON格式字符串
                
                -- 推荐理由（LLM生成的100字以内核心推荐理由，绿色高亮显示）
                recommendation_reason TEXT,
                
                -- 原始内容
                content TEXT,
                
                -- 数据来源标识：aihot/ original/ other
                source_from TEXT DEFAULT 'original',
                
                -- 兼容旧字段
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 数据库迁移：为已存在的表添加缺失字段
        # 检查并添加 category 字段
        try:
            cursor.execute("SELECT category FROM selected_items LIMIT 1")
        except sqlite3.OperationalError:
            logger.info("数据库迁移：添加category字段")
            cursor.execute("ALTER TABLE selected_items ADD COLUMN category TEXT")

        # 检查并添加 ingested_at 字段
        try:
            cursor.execute("SELECT ingested_at FROM selected_items LIMIT 1")
        except sqlite3.OperationalError:
            print("[数据库迁移] 添加ingested_at字段")
            cursor.execute("ALTER TABLE selected_items ADD COLUMN ingested_at TIMESTAMP")
            # 更新已有记录的ingested_at为当前时间
            cursor.execute("UPDATE selected_items SET ingested_at = datetime('now') WHERE ingested_at IS NULL")

        # 回填已有记录的ingested_at（如果仍为NULL）
        cursor.execute("UPDATE selected_items SET ingested_at = fetched_at WHERE ingested_at IS NULL AND fetched_at IS NOT NULL")
        cursor.execute("UPDATE selected_items SET ingested_at = created_at WHERE ingested_at IS NULL AND created_at IS NOT NULL")

        # 检查并添加 tags 字段
        try:
            cursor.execute("SELECT tags FROM selected_items LIMIT 1")
        except sqlite3.OperationalError:
            print("[数据库迁移] 添加tags字段")
            cursor.execute("ALTER TABLE selected_items ADD COLUMN tags TEXT DEFAULT '[]'")

        # 检查并添加 recommendation_reason 字段
        try:
            cursor.execute("SELECT recommendation_reason FROM selected_items LIMIT 1")
        except sqlite3.OperationalError:
            print("[数据库迁移] 添加recommendation_reason字段")
            cursor.execute("ALTER TABLE selected_items ADD COLUMN recommendation_reason TEXT")

        # 检查并添加 content_type 字段（内容类型：推文/博客/新闻等）
        try:
            cursor.execute("SELECT content_type FROM selected_items LIMIT 1")
        except sqlite3.OperationalError:
            print("[数据库迁移] 添加content_type字段")
            cursor.execute("ALTER TABLE selected_items ADD COLUMN content_type TEXT")

        # 检查并添加 summary_detail 字段
        try:
            cursor.execute("SELECT summary_detail FROM selected_items LIMIT 1")
        except sqlite3.OperationalError:
            print("[数据库迁移] 添加summary_detail字段")
            cursor.execute("ALTER TABLE selected_items ADD COLUMN summary_detail TEXT")
            
        # 检查并添加 source_from 字段（数据来源标识）
        try:
            cursor.execute("SELECT source_from FROM selected_items LIMIT 1")
        except sqlite3.OperationalError:
            print("[数据库迁移] 添加source_from字段")
            cursor.execute("ALTER TABLE selected_items ADD COLUMN source_from TEXT DEFAULT 'original'")
            cursor.execute("UPDATE selected_items SET source_from = 'aihot' WHERE source LIKE '%X:%' OR source LIKE '%X（%' OR source LIKE '%AI HOT%'")
            conn.commit()

        # 检查并添加 crawl_time 字段（抓取时间，作为所有时间筛选的唯一基准）
        try:
            cursor.execute("SELECT crawl_time FROM selected_items LIMIT 1")
        except sqlite3.OperationalError:
            print("[数据库迁移] 添加crawl_time字段")
            cursor.execute("ALTER TABLE selected_items ADD COLUMN crawl_time TEXT DEFAULT ''")
            # 用 ingested_at 填充历史数据的 crawl_time
            cursor.execute("UPDATE selected_items SET crawl_time = ingested_at WHERE crawl_time = ''")
            conn.commit()

        # 检查并添加 full_content 字段（完整正文Markdown，用于下载）
        try:
            cursor.execute("SELECT full_content FROM selected_items LIMIT 1")
        except sqlite3.OperationalError:
            print("[数据库迁移] 添加full_content字段")
            cursor.execute("ALTER TABLE selected_items ADD COLUMN full_content TEXT")
            conn.commit()

        # 抓取日志表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fetch_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT,
                source_name TEXT,
                url TEXT,
                status TEXT,  -- success/failed/skipped
                error TEXT,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 系统配置表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # 初始化配置项
        cursor.execute("INSERT OR IGNORE INTO system_config (key, value) VALUES ('aihot_enabled', 'true')")
        cursor.execute("INSERT OR IGNORE INTO system_config (key, value) VALUES ('sync_interval', '60')")
        cursor.execute("INSERT OR IGNORE INTO system_config (key, value) VALUES ('download_save_path', '~/My_Knowledge_Base/Inbox')")
        cursor.execute("INSERT OR IGNORE INTO system_config (key, value) VALUES ('l1_retention_days', '7')")
        conn.commit()

        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_selected_score ON selected_items (final_score DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_selected_tier ON selected_items (source_tier)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_selected_date ON selected_items (publish_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_selected_category ON selected_items (category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_selected_ingested ON selected_items (ingested_at DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fetch_logs_date ON fetch_logs (fetched_at)")

        # 日报存储表（对齐AIHOT的日报存档机制）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE,  -- YYYY-MM-DD
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                window_start TEXT,  -- ISO-8601
                window_end TEXT,    -- ISO-8601
                lead_title TEXT,
                lead_paragraph TEXT,  -- LLM生成的100字以内导语
                sections_json TEXT,   -- JSON格式的sections数组
                flashes_json TEXT,    -- JSON格式的flashes数组
                total_items INTEGER DEFAULT 0,
                content_json TEXT     -- 完整日报JSON（用于快速查询）
            )
        """)

        # FTS全文检索表（SQLite的FTS5引擎，替代PostgreSQL的pg_trgm）
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS selected_items_fts USING fts5(
                title,
                summary,
                source,
                tags,
                recommendation_reason,
                content='selected_items',
                content_rowid='id'
            )
        """)

        # 创建FTS触发器（自动同步）
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS selected_items_ai AFTER INSERT ON selected_items BEGIN
                INSERT INTO selected_items_fts(rowid, title, summary, source, tags, recommendation_reason)
                VALUES (new.id, new.title, new.summary, new.source, new.tags, new.recommendation_reason);
            END
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS selected_items_ad AFTER DELETE ON selected_items BEGIN
                DELETE FROM selected_items_fts WHERE rowid = old.id;
            END
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS selected_items_au AFTER UPDATE ON selected_items BEGIN
                UPDATE selected_items_fts
                SET title = new.title, summary = new.summary, source = new.source,
                    tags = new.tags, recommendation_reason = new.recommendation_reason
                WHERE rowid = old.id;
            END
        """)

        # 创建FTS索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_date ON daily_reports (date DESC)")

        # 原始抓取缓存表（L1缓存）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS raw_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE,
                raw_content TEXT,  -- 爬虫抓取的完整结构化文本/JSON
                crawl_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- 抓取时间（清理基准）
                source TEXT  -- 信源
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_raw_cache_crawl_time ON raw_cache (crawl_time)")

        # 下载状态表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS download_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,  -- 用户ID（当前单用户模式可为NULL）
                article_id INTEGER NOT NULL,  -- 关联selected_items.id
                download_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, article_id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_download_article ON download_status (article_id)")

        # 信源健康记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS source_health_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                source_name TEXT,
                source_url TEXT,
                check_time TEXT,
                status TEXT,
                reachable BOOLEAN,
                error_message TEXT,
                content_count INTEGER DEFAULT 0,
                response_time_ms INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_source_health_sid ON source_health_log (source_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_source_health_time ON source_health_log (check_time)")

        # 信源状态汇总表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS source_status (
                source_id TEXT PRIMARY KEY,
                source_name TEXT,
                source_url TEXT,
                last_check_time TEXT,
                is_healthy BOOLEAN DEFAULT 1,
                consecutive_failures INTEGER DEFAULT 0,
                last_error TEXT,
                last_success_time TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def save_selected_item(self, result: Dict[str, Any]) -> int:
        """
        保存精选内容到数据库
        Args:
            result: pipeline.process_crawl_result()返回的结果
        Returns:
            插入记录的ID
        """
        conn = self._get_conn()
        cursor = conn.cursor()

        scoring = result.get("scoring", {})
        pre_screen = result.get("pre_screen_result", {})
        
        # 分类字段（对齐AIHOT的5个分类）
        category = result.get("category", "")
        
        # 录入系统时间（自动设置）
        ingested_at = datetime.now().isoformat()
        crawl_time = result.get("crawl_time") or ingested_at

        cursor.execute("""
            INSERT INTO selected_items (
                url, title, source, source_tier, author, category,
                publish_date, ingested_at, crawl_time,
                final_score, selected,
                timeliness, importance, scarcity, practicality, relevance,
                pre_screen_reason, summary, content, full_content,
                tags, recommendation_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                title=excluded.title,
                category=excluded.category,
                final_score=excluded.final_score,
                selected=excluded.selected,
                timeliness=excluded.timeliness,
                importance=excluded.importance,
                scarcity=excluded.scarcity,
                practicality=excluded.practicality,
                relevance=excluded.relevance,
                summary=excluded.summary,
                content=excluded.content,
                full_content=excluded.full_content,
                tags=excluded.tags,
                recommendation_reason=excluded.recommendation_reason,
                crawl_time=excluded.crawl_time
        """, (
            result.get("url", ""),
            result.get("title", ""),
            result.get("source", ""),
            result.get("source_tier", "T2"),
            result.get("author", ""),
            category,
            result.get("publish_date", ""),
            ingested_at,
            crawl_time,
            result.get("final_score", 0),
            1 if result.get("selected", False) else 0,
            scoring.get("timeliness", 0),
            scoring.get("importance", 0),
            scoring.get("scarcity", 0),
            scoring.get("practicality", 0),
            scoring.get("relevance", 0),
            pre_screen.get("reason", ""),
            result.get("summary", ""),
            "",  # content字段预留
            result.get("full_content", "") or "",
            result.get("tags", "[]"),
            result.get("recommendation_reason", "")
        ))

        item_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return item_id

    def query_selected(
        self,
        time_filter: str = "today",
        source_tier: str = None,
        category: str = None,
        min_score: float = None,
        limit: int = 100,
        include_unselected: bool = False,
        custom_start: str = None,
        custom_end: str = None
    ) -> List[Dict[str, Any]]:
        """
        查询精选内容
        Args:
            time_filter: today/yesterday/week/all/custom
            source_tier: T1/T2/T3/None
            category: ai-models/ai-products/industry/paper/tip/None
            min_score: 最低分数
            limit: 返回数量限制
            include_unselected: 是否包含未入选内容（selected=0）
            custom_start: 自定义开始日期 YYYY-MM-DD
            custom_end: 自定义结束日期 YYYY-MM-DD
        Returns:
            精选内容列表
        """
        conn = self._get_conn()
        cursor = conn.cursor()

        conditions = [] if include_unselected else ["selected = 1"]
        params = []

        # 时间过滤 - 基于发布时间(publishedAt)
        # 支持自定义日期范围：custom_start, custom_end
        # 使用STRFTIME解析多种日期格式（ISO 8601、RFC 822等）
        now = datetime.now()
        
        # 日期解析表达式：处理ISO 8601 (2026-05-23) 和 RFC 822 (Sat, 23 May 2026) 格式
        date_parse_expr = """
        CASE 
            WHEN publish_date LIKE '____-__-__%' THEN SUBSTR(publish_date, 1, 10)
            WHEN publish_date LIKE '%,%' THEN 
                STRFTIME('%Y-%m-%d', 
                    SUBSTR(publish_date, INSTR(publish_date, ',') + 2)
                )
            ELSE SUBSTR(publish_date, 1, 10)
        END
        """
        
        # 过滤掉未来日期的内容
        conditions.append(f"{date_parse_expr} <= ?")
        params.append(now.strftime("%Y-%m-%d"))
        
        if time_filter == "today":
            conditions.append(f"{date_parse_expr} = ?")
            params.append(now.strftime("%Y-%m-%d"))
        elif time_filter == "yesterday":
            from datetime import timedelta
            yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
            conditions.append(f"{date_parse_expr} = ?")
            params.append(yesterday)
        elif time_filter == "week":
            from datetime import timedelta
            week_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")
            conditions.append(f"{date_parse_expr} >= ?")
            params.append(week_ago)
        elif time_filter == "custom":
            if custom_start:
                conditions.append(f"{date_parse_expr} >= ?")
                params.append(custom_start)
            if custom_end:
                conditions.append(f"{date_parse_expr} <= ?")
                params.append(custom_end)

        # 信源等级过滤
        if source_tier:
            conditions.append("source_tier = ?")
            params.append(source_tier)

        # 分类过滤
        if category:
            conditions.append("category = ?")
            params.append(category)

        # 分数过滤
        if min_score is not None:
            conditions.append("final_score >= ?")
            params.append(min_score)

        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

        query = f"""
            SELECT * FROM selected_items {where_clause}
            ORDER BY 
                CASE 
                    WHEN publish_date LIKE '%,%' THEN SUBSTR(publish_date, INSTR(publish_date, ',')+2, 11) || SUBSTR(publish_date, INSTR(publish_date, ',')+14, 8)
                    ELSE SUBSTR(publish_date, 1, 19)
                END DESC,
                created_at DESC
            LIMIT ?
        """
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_dict(row) for row in rows]

    def count_selected(
        self,
        time_filter: str = "today",
        source_tier: str = None,
        category: str = None,
        min_score: float = None,
        include_unselected: bool = False,
        custom_start: str = None,
        custom_end: str = None
    ) -> int:
        """查询精选内容总数"""
        conn = self._get_conn()
        cursor = conn.cursor()

        conditions = [] if include_unselected else ["selected = 1"]
        params = []

        now = datetime.now()
        
        date_parse_expr = """
        CASE 
            WHEN publish_date LIKE '____-__-__%' THEN SUBSTR(publish_date, 1, 10)
            WHEN publish_date LIKE '%,%' THEN 
                STRFTIME('%Y-%m-%d', 
                    SUBSTR(publish_date, INSTR(publish_date, ',') + 2)
                )
            ELSE SUBSTR(publish_date, 1, 10)
        END
        """
        
        conditions.append(f"{date_parse_expr} <= ?")
        params.append(now.strftime("%Y-%m-%d"))
        
        if time_filter == "today":
            conditions.append(f"{date_parse_expr} = ?")
            params.append(now.strftime("%Y-%m-%d"))
        elif time_filter == "yesterday":
            from datetime import timedelta
            yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
            conditions.append(f"{date_parse_expr} = ?")
            params.append(yesterday)
        elif time_filter == "week":
            from datetime import timedelta
            week_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")
            conditions.append(f"{date_parse_expr} >= ?")
            params.append(week_ago)
        elif time_filter == "custom":
            if custom_start:
                conditions.append(f"{date_parse_expr} >= ?")
                params.append(custom_start)
            if custom_end:
                conditions.append(f"{date_parse_expr} <= ?")
                params.append(custom_end)

        if source_tier:
            conditions.append("source_tier = ?")
            params.append(source_tier)

        if category:
            conditions.append("category = ?")
            params.append(category)

        if min_score is not None:
            conditions.append("final_score >= ?")
            params.append(min_score)

        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

        query = f"SELECT COUNT(*) as total FROM selected_items {where_clause}"
        cursor.execute(query, params)
        result = cursor.fetchone()
        conn.close()

        return result["total"] if result else 0

    def save_fetch_log(self, source_id: str, source_name: str, url: str, status: str, error: str = None):
        """保存抓取日志"""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO fetch_logs (source_id, source_name, url, status, error)
            VALUES (?, ?, ?, ?, ?)
        """, (source_id, source_name, url, status, error))

        conn.commit()
        conn.close()

    def get_config(self, key: str, default: str = None) -> Optional[str]:
        """获取系统配置"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT value FROM system_config WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default
        except:
            return default
        finally:
            conn.close()
    
    def set_config(self, key: str, value: str):
        """设置系统配置"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO system_config (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, value))
            conn.commit()
        finally:
            conn.close()
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # 精选总数
        cursor.execute("SELECT COUNT(*) as total FROM selected_items WHERE selected = 1")
        total_selected = cursor.fetchone()["total"]
        
        # 按等级分布
        cursor.execute("""
            SELECT source_tier, COUNT(*) as count 
            FROM selected_items 
            WHERE selected = 1 
            GROUP BY source_tier
        """)
        tier_distribution = {row["source_tier"]: row["count"] for row in cursor.fetchall()}

        # 今日新增
        now = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("""
            SELECT COUNT(*) as today_count 
            FROM selected_items 
            WHERE selected = 1 AND DATE(created_at) = ?
        """, (now,))
        today_count = cursor.fetchone()["today_count"]

        # 平均分数
        cursor.execute("""
            SELECT AVG(final_score) as avg_score 
            FROM selected_items 
            WHERE selected = 1
        """)
        avg_score = cursor.fetchone()["avg_score"] or 0

        conn.close()

        return {
            "total_selected": total_selected,
            "tier_distribution": tier_distribution,
            "today_count": today_count,
            "avg_score": round(avg_score, 1)
        }

    def save_daily_report(self, daily_data: Dict[str, Any]) -> int:
        """
        保存日报到数据库（对齐AIHOT的日报存档机制）
        Args:
            daily_data: 包含date, lead, sections, flashes等字段的日报数据
        Returns:
            插入记录的ID
        """
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO daily_reports (
                date, generated_at, window_start, window_end,
                lead_title, lead_paragraph,
                sections_json, flashes_json, total_items, content_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                generated_at=excluded.generated_at,
                window_start=excluded.window_start,
                window_end=excluded.window_end,
                lead_title=excluded.lead_title,
                lead_paragraph=excluded.lead_paragraph,
                sections_json=excluded.sections_json,
                flashes_json=excluded.flashes_json,
                total_items=excluded.total_items,
                content_json=excluded.content_json
        """, (
            daily_data.get("date"),
            daily_data.get("generatedAt", datetime.now().isoformat()),
            daily_data.get("windowStart"),
            daily_data.get("windowEnd"),
            daily_data.get("lead", {}).get("title"),
            daily_data.get("lead", {}).get("leadParagraph"),
            json.dumps(daily_data.get("sections", []), ensure_ascii=False),
            json.dumps(daily_data.get("flashes", []), ensure_ascii=False),
            daily_data.get("total_items", 0),
            json.dumps(daily_data, ensure_ascii=False)
        ))

        report_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return report_id

    def query_daily_report(self, date: str = None) -> Optional[Dict[str, Any]]:
        """
        查询指定日期的日报
        Args:
            date: YYYY-MM-DD格式，None表示最新日报
        Returns:
            日报数据字典，不存在则返回None
        """
        conn = self._get_conn()
        cursor = conn.cursor()

        if date:
            cursor.execute("SELECT * FROM daily_reports WHERE date = ?", (date,))
        else:
            cursor.execute("SELECT * FROM daily_reports ORDER BY date DESC LIMIT 1")

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        data = self._row_to_dict(row)
        
        # 解析JSON字段
        data["sections"] = json.loads(data["sections_json"]) if data["sections_json"] else []
        data["flashes"] = json.loads(data["flashes_json"]) if data["flashes_json"] else []
        data["content"] = json.loads(data["content_json"]) if data["content_json"] else {}
        
        # 构建对齐AIHOT的响应格式
        return {
            "date": data["date"],
            "generatedAt": data["generated_at"],
            "windowStart": data["window_start"],
            "windowEnd": data["window_end"],
            "lead": {
                "title": data["lead_title"],
                "leadParagraph": data["lead_paragraph"]
            },
            "sections": data["sections"],
            "flashes": data["flashes"],
            "total_items": data["total_items"]
        }

    def query_dailies(self, take: int = 30) -> List[Dict[str, Any]]:
        """
        查询日报归档列表
        Args:
            take: 返回数量
        Returns:
            日报列表，每项包含date和leadTitle
        """
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT date, generated_at, lead_title 
            FROM daily_reports 
            ORDER BY date DESC 
            LIMIT ?
        """, (take,))

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "date": row["date"],
                "generatedAt": row["generated_at"],
                "leadTitle": row["lead_title"]
            }
            for row in rows
        ]

    def search_items_fts(self, keyword: str, limit: int = 50) -> List[int]:
        """
        使用FTS5全文检索搜索内容
        Args:
            keyword: 搜索关键词
            limit: 返回数量
        Returns:
            匹配记录的ID列表
        """
        if not keyword or len(keyword) < 2:
            return []

        conn = self._get_conn()
        cursor = conn.cursor()

        # FTS5查询（支持模糊匹配）
        query = f"""
            SELECT rowid, rank FROM selected_items_fts
            WHERE selected_items_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """
        
        # FTS5语法：关键词用双引号包裹，支持前缀匹配
        fts_query = f'"{keyword}"*'
        cursor.execute(query, (fts_query, limit))
        
        rows = cursor.fetchall()
        conn.close()

        return [row["rowid"] for row in rows]

    # ========== L1缓存管理 ==========

    def save_raw_cache(self, url: str, raw_content: str, source: str = "") -> int:
        """保存原始抓取数据到L1缓存"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO raw_cache (url, raw_content, source, crawl_time)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(url) DO UPDATE SET
                raw_content=excluded.raw_content,
                crawl_time=CURRENT_TIMESTAMP,
                source=excluded.source
        """, (url, raw_content, source))
        cache_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return cache_id

    def clean_raw_cache_expired(self, retention_days: int) -> int:
        """清理过期L1缓存，以crawl_time为基准"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM raw_cache
            WHERE datetime(crawl_time) < datetime('now', '-' || ? || ' days')
        """, (retention_days,))
        cleaned = cursor.rowcount
        conn.commit()
        conn.close()
        return cleaned

    def clean_raw_cache_all(self) -> int:
        """清空全部L1缓存"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM raw_cache")
        cleaned = cursor.rowcount
        conn.commit()
        conn.close()
        return cleaned

    # ========== 下载状态管理 ==========

    def mark_downloaded(self, article_ids: List[int], user_id: str = None) -> int:
        """标记内容为已下载"""
        conn = self._get_conn()
        cursor = conn.cursor()
        marked = 0
        for aid in article_ids:
            cursor.execute("""
                INSERT OR IGNORE INTO download_status (user_id, article_id, download_time)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (user_id, aid))
            marked += cursor.rowcount
        conn.commit()
        conn.close()
        return marked

    def get_download_status(self, article_ids: List[int], user_id: str = None) -> Dict[int, bool]:
        """获取内容的下载状态"""
        conn = self._get_conn()
        cursor = conn.cursor()
        result = {}
        for aid in article_ids:
            cursor.execute("""
                SELECT 1 FROM download_status WHERE user_id IS ? AND article_id = ?
            """, (user_id, aid))
            result[aid] = cursor.fetchone() is not None
        conn.close()
        return result

    def get_items_for_download(self, article_ids: List[int]) -> List[Dict[str, Any]]:
        """获取用于下载的文章数据"""
        if not article_ids:
            return []
        placeholders = ",".join("?" for _ in article_ids)
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT id, url, title, source, source_tier, final_score, publish_date, tags, full_content, summary
            FROM selected_items
            WHERE id IN ({placeholders})
        """, article_ids)
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_dict(row) for row in rows]

    def get_downloaded_ids(self, article_ids: List[int], user_id: str = None) -> List[int]:
        """获取已下载的文章ID列表"""
        if not article_ids:
            return []
        conn = self._get_conn()
        cursor = conn.cursor()
        placeholders = ",".join("?" for _ in article_ids)
        # user_id为None时匹配NULL值
        if user_id is None:
            cursor.execute(f"""
                SELECT article_id FROM download_status
                WHERE user_id IS NULL AND article_id IN ({placeholders})
            """, article_ids)
        else:
            cursor.execute(f"""
                SELECT article_id FROM download_status
                WHERE user_id = ? AND article_id IN ({placeholders})
            """, [user_id] + article_ids)
        result = [row["article_id"] for row in cursor.fetchall()]
        conn.close()
        return result

    # ========== 信源健康管理 ==========

    def save_source_health_log(self, source_id: str, source_name: str, source_url: str, 
                                status: str, reachable: bool, error_message: str = None,
                                content_count: int = 0, response_time_ms: int = None):
        """保存信源健康检测日志"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO source_health_log 
                    (source_id, source_name, source_url, check_time, status, 
                     reachable, error_message, content_count, response_time_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (source_id, source_name, source_url, datetime.now().isoformat(),
                  status, reachable, error_message, content_count, response_time_ms))
            conn.commit()
        finally:
            conn.close()

    def update_source_status(self, source_id: str, source_name: str, source_url: str,
                              is_healthy: bool, error_message: str = None):
        """更新信源状态汇总"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            now = datetime.now().isoformat()
            if is_healthy:
                cursor.execute("""
                    INSERT INTO source_status 
                        (source_id, source_name, source_url, last_check_time, is_healthy, 
                         consecutive_failures, last_error, last_success_time)
                    VALUES (?, ?, ?, ?, 1, 0, NULL, ?)
                    ON CONFLICT(source_id) DO UPDATE SET
                        last_check_time=excluded.last_check_time,
                        is_healthy=1,
                        consecutive_failures=0,
                        last_error=NULL,
                        last_success_time=excluded.last_success_time
                """, (source_id, source_name, source_url, now, now))
            else:
                cursor.execute("""
                    INSERT INTO source_status 
                        (source_id, source_name, source_url, last_check_time, is_healthy, 
                         consecutive_failures, last_error)
                    VALUES (?, ?, ?, ?, 0, 
                            COALESCE((SELECT consecutive_failures FROM source_status WHERE source_id = ?), 0) + 1, 
                            ?)
                    ON CONFLICT(source_id) DO UPDATE SET
                        last_check_time=excluded.last_check_time,
                        is_healthy=0,
                        consecutive_failures=consecutive_failures+1,
                        last_error=excluded.last_error
                """, (source_id, source_name, source_url, now, source_id, error_message))
            conn.commit()
        finally:
            conn.close()

    def get_unhealthy_sources(self) -> List[Dict[str, Any]]:
        """获取所有失效信源"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT source_id, source_name, source_url, last_check_time, 
                       consecutive_failures, last_error, last_success_time
                FROM source_status
                WHERE is_healthy = 0
                ORDER BY consecutive_failures DESC
            """)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_source_health(self, source_id: str) -> Optional[Dict[str, Any]]:
        """获取指定信源的健康状态"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT * FROM source_status WHERE source_id = ?
            """, (source_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_source_health_logs(self, source_id: str = None, hours: int = 24, limit: int = 50) -> List[Dict[str, Any]]:
        """查询信源健康日志"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            if source_id:
                cursor.execute("""
                    SELECT source_id, source_name, source_url, check_time, status,
                           reachable, error_message, content_count, response_time_ms
                    FROM source_health_log
                    WHERE source_id = ?
                    ORDER BY check_time DESC
                    LIMIT ?
                """, (source_id, limit))
            else:
                # 查询所有信源的日志
                cursor.execute("""
                    SELECT source_id, source_name, source_url, check_time, status,
                           reachable, error_message, content_count, response_time_ms
                    FROM source_health_log
                    ORDER BY check_time DESC
                    LIMIT ?
                """, (limit,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_health_stats(self) -> Dict[str, Any]:
        """获取信源健康统计信息"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            # 总信源数
            cursor.execute("SELECT COUNT(*) as total FROM source_status")
            total = cursor.fetchone()["total"] or 0

            # 健康/警告/失效数量
            cursor.execute("SELECT COUNT(*) as healthy FROM source_status WHERE is_healthy = 1")
            healthy = cursor.fetchone()["healthy"] or 0

            cursor.execute("SELECT COUNT(*) as unhealthy FROM source_status WHERE is_healthy = 0 AND consecutive_failures >= 3")
            unhealthy = cursor.fetchone()["unhealthy"] or 0

            warning = total - healthy - unhealthy

            # 按失败原因统计
            cursor.execute("""
                SELECT last_error, COUNT(*) as count
                FROM source_status
                WHERE is_healthy = 0
                GROUP BY last_error
                ORDER BY count DESC
                LIMIT 5
            """)
            error_distribution = {row["last_error"] or "未知": row["count"] for row in cursor.fetchall()}

            # 成功率
            success_rate = round(healthy / total * 100, 1) if total > 0 else 0

            return {
                "total": total,
                "healthy": healthy,
                "warning": warning,
                "unhealthy": unhealthy,
                "success_rate": success_rate,
                "error_distribution": error_distribution
            }
        finally:
            conn.close()

    def get_all_source_health(self) -> List[Dict[str, Any]]:
        """获取所有信源的健康状态列表"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT source_id, source_name, source_url, last_check_time,
                       is_healthy, consecutive_failures, last_error, last_success_time
                FROM source_status
                ORDER BY is_healthy ASC, consecutive_failures DESC
            """)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """将数据库行转换为字典"""
        return dict(row)
