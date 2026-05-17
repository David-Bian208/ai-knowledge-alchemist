"""
RSS订阅模块
支持订阅RSS源，自动抓取新内容
"""
import logging
from typing import List, Dict, Any
from datetime import datetime

import feedparser

logger = logging.getLogger(__name__)


class RSSFetcher:
    """RSS订阅抓取器"""
    
    def __init__(self):
        self.user_agent = "KnowledgeAlchemist/1.0"
    
    def fetch_feed(self, feed_url: str) -> List[Dict[str, Any]]:
        """
        抓取RSS源，返回所有条目
        Args:
            feed_url: RSS feed URL
        Returns:
            条目列表，每个条目包含title/link/summary/published等字段
        """
        logger.info(f"抓取RSS源: {feed_url}")
        
        try:
            feed = feedparser.parse(feed_url)
            
            if not feed.entries:
                logger.warning(f"RSS源无内容: {feed_url}")
                return []
            
            entries = []
            for entry in feed.entries:
                entries.append({
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "summary": entry.get("summary", ""),
                    "published": entry.get("published", ""),
                    "author": entry.get("author", ""),
                    "source": feed.feed.get("title", "")
                })
            
            logger.info(f"RSS源抓取成功: {len(entries)} 条")
            return entries
            
        except Exception as e:
            logger.error(f"RSS抓取失败: {feed_url}, 错误: {e}")
            return []
    
    def fetch_new_entries(self, feed_url: str, existing_urls: set) -> List[Dict[str, Any]]:
        """
        抓取RSS源，过滤已处理的URL
        Args:
            feed_url: RSS feed URL
            existing_urls: 已处理的URL集合
        Returns:
            新条目列表
        """
        all_entries = self.fetch_feed(feed_url)
        new_entries = [e for e in all_entries if e["link"] not in existing_urls]
        
        if new_entries:
            logger.info(f"发现 {len(new_entries)} 条新内容")
        
        return new_entries
