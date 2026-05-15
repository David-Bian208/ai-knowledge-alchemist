"""
SQLite 存储模块
用于保存和查询处理后的素材数据
"""
import os
import json
import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.config import config


class MaterialStorage:
    """素材数据持久化存储"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = config.get("storage.db_path", "data/materials.db")
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
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """初始化数据库表"""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE,
                title TEXT,
                author TEXT,
                source TEXT,
                publish_date TEXT,
                content TEXT,
                content_dimension TEXT,
                time_dimension TEXT,
                scene_dimension TEXT,
                importance_score REAL,
                scarcity_score REAL,
                practicality_score REAL,
                final_score REAL,
                star_level INTEGER,
                core_points TEXT,
                video_usage TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_dimension ON materials (content_dimension)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_time_dimension ON materials (time_dimension)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_final_score ON materials (final_score)")

        conn.commit()
        conn.close()

    def save_material(self, url: str, title: str, content: str, result: Dict[str, Any]) -> int:
        """
        保存处理后的素材到数据库
        Args:
            url: 原始URL
            title: 标题
            content: 原始 Markdown 内容
            result: 处理结果
        Returns:
            插入记录的 ID
        """
        conn = self._get_conn()
        cursor = conn.cursor()

        metadata = result.get("metadata", {})
        classification = result.get("classification", {})
        scoring = result.get("scoring", {}).get("scoring", result.get("scoring", {}))
        extraction = result.get("extraction", {})

        cursor.execute("""
            INSERT INTO materials (
                url, title, author, source, publish_date, content,
                content_dimension, time_dimension, scene_dimension,
                importance_score, scarcity_score, practicality_score,
                final_score, star_level,
                core_points, video_usage
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                title=excluded.title,
                content_dimension=excluded.content_dimension,
                time_dimension=excluded.time_dimension,
                scene_dimension=excluded.scene_dimension,
                importance_score=excluded.importance_score,
                scarcity_score=excluded.scarcity_score,
                practicality_score=excluded.practicality_score,
                final_score=excluded.final_score,
                star_level=excluded.star_level,
                core_points=excluded.core_points,
                video_usage=excluded.video_usage,
                content=excluded.content
        """, (
            url,
            title,
            metadata.get("author", ""),
            metadata.get("source", ""),
            metadata.get("publish_date"),
            content,
            classification.get("content_dimension", ""),
            classification.get("time_dimension", ""),
            classification.get("scene_dimension", ""),
            scoring.get("importance", 0),
            scoring.get("scarcity", 0),
            scoring.get("practicality", 0),
            result.get("final_score", 0),
            result.get("star_level", 0),
            json.dumps(extraction.get("core_points", []), ensure_ascii=False),
            extraction.get("video_usage", "")
        ))

        material_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return material_id

    def query_materials(
        self,
        content_dimension: str = None,
        time_dimension: str = None,
        scene_dimension: str = None,
        min_score: float = None,
        max_score: float = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        查询素材，支持多种过滤条件
        """
        conn = self._get_conn()
        cursor = conn.cursor()

        conditions = []
        params = []

        if content_dimension:
            conditions.append("content_dimension = ?")
            params.append(content_dimension)

        if time_dimension:
            conditions.append("time_dimension = ?")
            params.append(time_dimension)

        if scene_dimension:
            conditions.append("scene_dimension = ?")
            params.append(scene_dimension)

        if min_score is not None:
            conditions.append("final_score >= ?")
            params.append(min_score)

        if max_score is not None:
            conditions.append("final_score <= ?")
            params.append(max_score)

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        query = f"""
            SELECT * FROM materials {where_clause}
            ORDER BY final_score DESC, created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_dict(row) for row in rows]

    def get_material_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """根据URL检查是否已存在"""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM materials WHERE url = ?", (url,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_dict(row)
        return None

    def get_statistics(self) -> Dict[str, Any]:
        """获取素材统计信息"""
        conn = self._get_conn()
        cursor = conn.cursor()

        # 总数量
        cursor.execute("SELECT COUNT(*) as total FROM materials")
        total = cursor.fetchone()["total"]

        # 各维度分布
        cursor.execute("""
            SELECT content_dimension, COUNT(*) as count
            FROM materials
            GROUP BY content_dimension
        """)
        content_distribution = {row["content_dimension"]: row["count"] for row in cursor.fetchall() if row["content_dimension"]}

        cursor.execute("""
            SELECT time_dimension, COUNT(*) as count
            FROM materials
            GROUP BY time_dimension
        """)
        time_distribution = {row["time_dimension"]: row["count"] for row in cursor.fetchall() if row["time_dimension"]}

        # 评分分布
        cursor.execute("""
            SELECT star_level, COUNT(*) as count
            FROM materials
            GROUP BY star_level
        """)
        star_distribution = {str(row["star_level"]): row["count"] for row in cursor.fetchall() if row["star_level"]}

        conn.close()

        return {
            "total": total,
            "content_distribution": content_distribution,
            "time_distribution": time_distribution,
            "star_distribution": star_distribution
        }

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """将数据库行转换为字典"""
        result = dict(row)

        # 解析 core_points
        if result.get("core_points"):
            try:
                result["core_points"] = json.loads(result["core_points"])
            except json.JSONDecodeError:
                result["core_points"] = []

        return result
