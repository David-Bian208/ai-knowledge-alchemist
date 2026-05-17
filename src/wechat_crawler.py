"""
微信公众号抓取模块
支持两种抓取方式：
1. 搜狗微信搜索 - 通过搜索获取微信文章
2. RSSHub - 通过自建RSSHub获取微信公众号RSS
"""
import os
import re
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

import trafilatura
from trafilatura import fetch_url, extract
from src.crawler import ArticleMetadata, WebCrawler
from src.rss_fetcher import RSSFetcher

logger = logging.getLogger(__name__)


class WeChatCrawler:
    """微信公众号抓取器"""
    
    def __init__(self):
        self.web_crawler = WebCrawler()
        self.rss_fetcher = RSSFetcher()
        self.rsshub_url = os.getenv("RSSHUB_URL", "")  # 自建RSSHub地址
    
    def fetch_wechat_article(self, url: str) -> Dict:
        """
        抓取微信文章
        Args:
            url: 微信公众号文章URL
        Returns:
            与WebCrawler.fetch()相同格式的结果
        """
        logger.info(f"开始抓取微信文章: {url}")
        
        # 方式1：直接尝试trafilatura抓取（部分文章可以）
        try:
            result = self.web_crawler.fetch(url)
            if result.get("success") and result.get("markdown"):
                logger.info("微信文章抓取成功（直接抓取）")
                return result
        except Exception as e:
            logger.warning(f"直接抓取失败: {e}")
        
        # 方式2：用搜狗微信搜索获取
        try:
            sogou_result = self._fetch_via_sogou(url)
            if sogou_result.get("success"):
                logger.info("微信文章抓取成功（搜狗搜索）")
                return sogou_result
        except Exception as e:
            logger.warning(f"搜狗搜索抓取失败: {e}")
        
        logger.error(f"微信文章抓取失败: {url}")
        return {"success": False, "metadata": None, "markdown": "", "error": "微信文章无法抓取"}
    
    def _fetch_via_sogou(self, original_url: str) -> Dict:
        """
        通过搜狗微信搜索获取文章缓存
        搜狗会缓存微信文章，且没有强反爬
        """
        # 从原始URL提取文章ID
        match = re.search(r'sn=([a-f0-9]+)', original_url)
        if not match:
            return {"success": False, "metadata": None, "markdown": "", "error": "无法解析文章ID"}
        
        sn = match.group(1)
        
        # 搜狗搜索URL（这里用简单搜索，实际可能需要更复杂的逻辑）
        sogou_url = f"https://weixin.sogou.com/weixin?type=2&query={sn}"
        
        # 搜狗也有反爬，所以这里用简单方式
        # 更可靠的方式是通过RSSHub
        
        return {"success": False, "metadata": None, "markdown": "", "error": "搜狗搜索暂未实现"}
    
    def fetch_wechat_rss(self, rss_url: str) -> List[Dict[str, Any]]:
        """
        通过RSS抓取微信公众号
        Args:
            rss_url: RSS源URL（可以是RSSHub或第三方RSS服务）
        Returns:
            文章列表
        """
        if not rss_url:
            return []
        
        logger.info(f"通过RSS抓取微信内容: {rss_url}")
        
        try:
            entries = self.rss_fetcher.fetch_feed(rss_url)
            results = []
            
            for entry in entries:
                url = entry.get("link", "")
                if not url:
                    continue
                
                # 抓取文章正文
                try:
                    article_result = self.fetch_wechat_article(url)
                    if article_result.get("success"):
                        results.append(article_result)
                except Exception as e:
                    logger.warning(f"文章抓取失败: {url}, {e}")
            
            logger.info(f"RSS抓取完成: {len(results)} 篇文章")
            return results
            
        except Exception as e:
            logger.error(f"RSS抓取失败: {e}")
            return []
    
    def fetch_via_rsshub(self, wechat_id: str) -> List[Dict[str, Any]]:
        """
        通过RSSHub抓取微信公众号
        Args:
            wechat_id: 微信公众号ID（如：huashexiaozhen）
        Returns:
            文章列表
        """
        if not self.rsshub_url:
            logger.warning("RSSHUB_URL 未配置")
            return []
        
        # RSSHub的微信公众号路由
        rss_url = f"{self.rsshub_url}/wechat/ershoulu/{wechat_id}"
        
        return self.fetch_wechat_rss(rss_url)
