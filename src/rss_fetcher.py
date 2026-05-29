"""
RSS订阅模块
支持订阅RSS源，自动抓取新内容并跳转原文链接获取全文
"""
import logging
from typing import List, Dict, Any
from datetime import datetime
from email.utils import parsedate_to_datetime
import requests

import feedparser

from src.crawler import WebCrawler

logger = logging.getLogger(__name__)


class RSSFetcher:
    """RSS订阅抓取器"""
    
    def __init__(self, fetch_full_content=False):
        self.user_agent = "KnowledgeAlchemist/1.0"
        self.fetch_full_content = fetch_full_content
        # 初始化爬虫，用于抓取原文全文
        if fetch_full_content:
            self.crawler = WebCrawler(use_gallery_dl=False, use_media_crawler=False)
    
    def fetch_feed(self, feed_url: str, timeout: int = 15) -> List[Dict[str, Any]]:
        """
        抓取RSS源，返回所有条目
        Args:
            feed_url: RSS feed URL
            timeout: 请求超时（秒）
        Returns:
            条目列表，每个条目包含title/link/summary/content/published等字段
        """
        logger.info(f"抓取RSS源: {feed_url}")
        
        try:
            # 先下载RSS XML内容（带超时）
            headers = {"User-Agent": self.user_agent}
            resp = requests.get(feed_url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            
            # 用feedparser解析
            feed = feedparser.parse(resp.content)
            
            if not feed.entries:
                logger.warning(f"RSS源无内容: {feed_url}")
                return []
            
            entries = []
            for entry in feed.entries[:10]:  # 每个RSS最多取10条
                # 标准化日期为ISO 8601格式（SQLite可识别）
                pub_raw = entry.get("published", "")
                pub_date = ""
                if pub_raw:
                    try:
                        dt = parsedate_to_datetime(pub_raw)
                        pub_date = dt.strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        pub_date = pub_raw
                
                item = {
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "summary": entry.get("summary", ""),
                    "published": pub_date,
                    "author": entry.get("author", ""),
                    "source": feed.feed.get("title", "")
                }
                
                # 优先使用content字段（很多RSS源content比summary更完整）
                if hasattr(entry, 'content') and entry.content:
                    item["content"] = entry.content[0].value
                
                # 如果开启了全文抓取，且RSS中没有完整内容，则抓取原文
                if self.fetch_full_content:
                    article_url = entry.get("link", "")
                    # 检查是否有完整内容（content字段或summary > 500字符）
                    has_full_content = (
                        (hasattr(entry, 'content') and entry.content and len(entry.content[0].value) > 500)
                        or (len(entry.get("summary", "")) > 500)
                    )
                    if not has_full_content and article_url:
                        logger.info(f"抓取原文全文: {article_url[:60]}...")
                        full_content = self._fetch_article_content(article_url)
                        if full_content:
                            item["content"] = full_content
                
                # 不在此处抓取全文，由后续pipeline处理
                entries.append(item)
            
            logger.info(f"RSS源抓取成功: {len(entries)} 条")
            return entries
            
        except requests.exceptions.Timeout:
            logger.warning(f"RSS抓取超时: {feed_url}")
            return []
        except requests.exceptions.RequestException as e:
            logger.warning(f"RSS请求失败: {feed_url}, 错误: {e}")
            return []
        except Exception as e:
            logger.error(f"RSS解析失败: {feed_url}, 错误: {e}")
            return []
    
    def _fetch_article_content(self, url: str) -> str:
        """
        抓取文章全文
        Args:
            url: 文章链接
        Returns:
            全文内容（Markdown格式），失败返回空字符串
        """
        try:
            result = self.crawler.fetch(url)
            if result.get("success"):
                content = result.get("markdown", "")
                if len(content) > 100:  # 确保有实质内容
                    # 限制长度
                    if len(content) > 50000:
                        content = content[:50000] + "\n\n[内容过长已截断]"
                    return content
        except Exception as e:
            logger.debug(f"抓取文章全文失败: {url}, {e}")
        return ""
    
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
