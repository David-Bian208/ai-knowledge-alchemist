"""
事件聚类去重模块
使用Embedding语义匹配，避免同一事件重复入库
"""
import os
import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class DeduplicationService:
    """重复检测服务"""
    
    def __init__(self):
        # V1.0先用URL精确匹配
        # V1.1后续用Embedding做语义相似度匹配
        self.seen_urls = set()
    
    def load_existing_urls(self, storage) -> int:
        """
        从数据库加载已有URL
        Args:
            storage: MaterialStorage实例
        Returns:
            加载的URL数量
        """
        try:
            materials = storage.query_materials(limit=10000)
            self.seen_urls = {m["url"] for m in materials}
            logger.info(f"加载已有URL: {len(self.seen_urls)} 条")
            return len(self.seen_urls)
        except Exception as e:
            logger.warning(f"加载已有URL失败: {e}")
            return 0
    
    def is_duplicate(self, url: str) -> bool:
        """检查URL是否已存在"""
        return url in self.seen_urls
    
    def add_url(self, url: str):
        """标记URL为已处理"""
        self.seen_urls.add(url)
