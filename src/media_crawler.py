"""
MediaCrawler 轻量级封装
基于Playwright实现小红书、抖音、知乎、贴吧等平台抓取
不需要完整MediaCrawler项目，只需核心抓取逻辑
"""
import asyncio
import logging
import re
import time
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class MediaCrawlerAdapter:
    """
    轻量级MediaCrawler适配器
    支持平台：小红书、抖音、知乎、贴吧、微博
    """
    
    # 支持的域名映射
    SUPPORTED_PLATFORMS = {
        'xiaohongshu.com': 'xhs',
        'xhslink.com': 'xhs',
        'douyin.com': 'dy',
        'iesdouyin.com': 'dy',
        'zhihu.com': 'zhihu',
        'tieba.baidu.com': 'tieba',
        'weibo.com': 'weibo',
    }
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self._playwright_available = False
        self._browser = None
        self._context = None
        
        self._init_playwright()
    
    def _init_playwright(self):
        """初始化Playwright"""
        try:
            from playwright.sync_api import sync_playwright
            
            self.playwright = sync_playwright().start()
            self._browser = self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-blink-features=AutomationControlled',
                ]
            )
            self._context = self._browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="zh-CN",
            )
            # 反检测脚本
            self._context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
                window.chrome = {runtime: {}};
            """)
            self._playwright_available = True
            logger.info("MediaCrawler Playwright初始化成功")
        except Exception as e:
            logger.warning(f"MediaCrawler Playwright初始化失败: {e}")
            self._playwright_available = False
    
    def is_supported(self, url: str) -> bool:
        """检查URL是否支持"""
        if not self._playwright_available:
            return False
        
        for domain in self.SUPPORTED_PLATFORMS.keys():
            if domain in url.lower():
                return True
        return False
    
    def get_platform(self, url: str) -> Optional[str]:
        """获取平台名称"""
        for domain, platform in self.SUPPORTED_PLATFORMS.items():
            if domain in url.lower():
                return platform
        return None
    
    def fetch(self, url: str) -> Dict:
        """
        抓取媒体平台内容
        Args:
            url: 目标URL
        Returns:
            {
                "success": bool,
                "platform": str,  # 平台名称
                "metadata": dict,  # 元数据
                "content": str,  # 文本内容
                "images": list,  # 图片URL列表
                "error": str  # 错误信息
            }
        """
        if not self._playwright_available:
            return {"success": False, "error": "Playwright不可用"}
        
        platform = self.get_platform(url)
        if not platform:
            return {"success": False, "error": "不支持的平台"}
        
        logger.info(f"MediaCrawler抓取: {platform} - {url}")
        
        # 根据平台选择抓取策略
        if platform == 'xhs':
            return self._fetch_xhs(url)
        elif platform == 'dy':
            return self._fetch_dy(url)
        elif platform == 'zhihu':
            return self._fetch_zhihu(url)
        elif platform == 'tieba':
            return self._fetch_tieba(url)
        elif platform == 'weibo':
            return self._fetch_weibo(url)
        else:
            return self._fetch_generic(url)
    
    def _fetch_xhs(self, url: str) -> Dict:
        """抓取小红书笔记"""
        try:
            page = self._context.new_page()
            page.set_default_timeout(30000)
            page.goto(url, wait_until="networkidle", timeout=30000)
            time.sleep(3)
            
            # 提取内容
            content = page.inner_text("body")
            title_el = page.query_selector("h1, .title, .note-title")
            title = title_el.inner_text() if title_el else ""
            
            # 提取图片
            images = page.eval_on_selector_all(
                "img", 
                "els => els.map(el => el.src).filter(src => src && (src.includes('http') || src.includes('//')))"
            )
            
            page.close()
            
            # 解析小红书特有元数据
            author_match = re.search(r'@(\w+)', content)
            author = author_match.group(1) if author_match else ""
            
            return {
                "success": True,
                "platform": "xiaohongshu",
                "metadata": {
                    "title": title,
                    "author": author,
                    "source": "小红书",
                    "url": url,
                },
                "content": content[:3000],
                "images": images[:10],
            }
        except Exception as e:
            logger.error(f"小红书抓取失败: {e}")
            return {"success": False, "platform": "xiaohongshu", "error": str(e)}
    
    def _fetch_dy(self, url: str) -> Dict:
        """抓取抖音内容"""
        try:
            page = self._context.new_page()
            page.set_default_timeout(30000)
            page.goto(url, wait_until="networkidle", timeout=30000)
            time.sleep(3)
            
            content = page.inner_text("body")
            title_el = page.query_selector("h1, .title, .video-title")
            title = title_el.inner_text() if title_el else ""
            
            # 抖音视频URL
            video_el = page.query_selector("video source, video")
            video_url = ""
            if video_el:
                video_url = video_el.get_attribute("src") or ""
                if not video_url:
                    source_el = video_el.query_selector("source")
                    if source_el:
                        video_url = source_el.get_attribute("src") or ""
            
            page.close()
            
            return {
                "success": True,
                "platform": "douyin",
                "metadata": {
                    "title": title,
                    "author": "",
                    "source": "抖音",
                    "url": url,
                },
                "content": content[:3000],
                "video_url": video_url,
            }
        except Exception as e:
            logger.error(f"抖音抓取失败: {e}")
            return {"success": False, "platform": "douyin", "error": str(e)}
    
    def _fetch_zhihu(self, url: str) -> Dict:
        """抓取知乎内容"""
        try:
            page = self._context.new_page()
            page.set_default_timeout(30000)
            page.goto(url, wait_until="networkidle", timeout=30000)
            time.sleep(2)
            
            content = page.inner_text("body")
            title_el = page.query_selector("h1, .QuestionHeader-title")
            title = title_el.inner_text() if title_el else ""
            
            page.close()
            
            return {
                "success": True,
                "platform": "zhihu",
                "metadata": {
                    "title": title,
                    "author": "",
                    "source": "知乎",
                    "url": url,
                },
                "content": content[:3000],
            }
        except Exception as e:
            logger.error(f"知乎抓取失败: {e}")
            return {"success": False, "platform": "zhihu", "error": str(e)}
    
    def _fetch_tieba(self, url: str) -> Dict:
        """抓取贴吧内容"""
        try:
            page = self._context.new_page()
            page.set_default_timeout(30000)
            page.goto(url, wait_until="networkidle", timeout=30000)
            time.sleep(2)
            
            content = page.inner_text("body")
            title_el = page.query_selector("h1, .core_title_txt")
            title = title_el.inner_text() if title_el else ""
            
            page.close()
            
            return {
                "success": True,
                "platform": "tieba",
                "metadata": {
                    "title": title,
                    "author": "",
                    "source": "百度贴吧",
                    "url": url,
                },
                "content": content[:3000],
            }
        except Exception as e:
            logger.error(f"贴吧抓取失败: {e}")
            return {"success": False, "platform": "tieba", "error": str(e)}
    
    def _fetch_weibo(self, url: str) -> Dict:
        """抓取微博内容"""
        try:
            page = self._context.new_page()
            page.set_default_timeout(30000)
            page.goto(url, wait_until="networkidle", timeout=30000)
            time.sleep(3)
            
            content = page.inner_text("body")
            
            page.close()
            
            return {
                "success": True,
                "platform": "weibo",
                "metadata": {
                    "title": "",
                    "author": "",
                    "source": "微博",
                    "url": url,
                },
                "content": content[:3000],
            }
        except Exception as e:
            logger.error(f"微博抓取失败: {e}")
            return {"success": False, "platform": "weibo", "error": str(e)}
    
    def _fetch_generic(self, url: str) -> Dict:
        """通用抓取"""
        try:
            page = self._context.new_page()
            page.set_default_timeout(30000)
            page.goto(url, wait_until="networkidle", timeout=30000)
            time.sleep(2)
            
            content = page.inner_text("body")
            title = page.title()
            
            page.close()
            
            return {
                "success": True,
                "platform": "generic",
                "metadata": {
                    "title": title,
                    "author": "",
                    "source": "unknown",
                    "url": url,
                },
                "content": content[:3000],
            }
        except Exception as e:
            logger.error(f"通用抓取失败: {e}")
            return {"success": False, "platform": "generic", "error": str(e)}
    
    def close(self):
        """关闭浏览器"""
        if self._browser:
            try:
                self._browser.close()
                self.playwright.stop()
                logger.info("MediaCrawler浏览器已关闭")
            except Exception as e:
                logger.warning(f"关闭浏览器失败: {e}")
