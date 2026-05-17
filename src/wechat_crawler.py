"""
微信公众号抓取模块
支持多种抓取方式应对反爬机制：
1. 直接抓取 - trafialtura（部分文章可用）
2. Playwright浏览器模拟 - 绕过JS渲染和验证码
3. 搜狗微信搜索 - 通过搜狗缓存获取
4. RSSHub - 通过自建RSSHub获取微信公众号RSS
"""
import os
import re
import time
import logging
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime
from urllib.parse import quote

import trafilatura
from trafilatura import fetch_url, extract
from src.crawler import ArticleMetadata, WebCrawler
from src.rss_fetcher import RSSFetcher

logger = logging.getLogger(__name__)


class WeChatCrawler:
    """微信公众号抓取器 - 多级降级策略"""
    
    def __init__(self, use_playwright: bool = True):
        self.web_crawler = WebCrawler()
        self.rss_fetcher = RSSFetcher()
        self.rsshub_url = os.getenv("RSSHUB_URL", "")  # 自建RSSHub地址
        self.use_playwright = use_playwright
        self._playwright_available = False
        
        # 初始化Playwright
        if self.use_playwright:
            self._init_playwright()
        
        # 搜狗搜索配置
        self.sogou_timeout = 30
        self.sogou_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }
    
    def _init_playwright(self):
        """初始化Playwright浏览器"""
        try:
            from playwright.sync_api import sync_playwright
            
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-blink-features=AutomationControlled',
                ]
            )
            self.context = self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="zh-CN",
            )
            # 注入反检测脚本
            self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
                window.chrome = {runtime: {}};
            """)
            self._playwright_available = True
            logger.info("Playwright初始化成功")
        except Exception as e:
            logger.warning(f"Playwright初始化失败，将跳过浏览器模拟: {e}")
            self._playwright_available = False
    
    def fetch_wechat_article(self, url: str) -> Dict:
        """
        抓取微信文章 - 多级降级策略
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
        
        # 方式2：用Playwright浏览器模拟（绕过JS渲染和验证码）
        if self._playwright_available:
            try:
                browser_result = self._fetch_with_playwright(url)
                if browser_result.get("success"):
                    logger.info("微信文章抓取成功（Playwright）")
                    return browser_result
            except Exception as e:
                logger.warning(f"Playwright抓取失败: {e}")
        
        # 方式3：用搜狗微信搜索获取
        try:
            sogou_result = self._fetch_via_sogou(url)
            if sogou_result.get("success"):
                logger.info("微信文章抓取成功（搜狗搜索）")
                return sogou_result
        except Exception as e:
            logger.warning(f"搜狗搜索抓取失败: {e}")
        
        logger.error(f"微信文章抓取失败: {url}")
        return {"success": False, "metadata": None, "markdown": "", "error": "微信文章无法抓取"}
    
    def _fetch_with_playwright(self, url: str) -> Dict:
        """
        使用Playwright模拟浏览器抓取微信文章
        可以绕过大部分反爬机制：
        - JavaScript动态渲染
        - 验证码检测
        - 鼠标/键盘行为检测
        """
        if not self._playwright_available:
            return {"success": False, "metadata": None, "markdown": "", "error": "Playwright不可用"}
        
        logger.info(f"使用Playwright抓取: {url}")
        
        try:
            page = self.context.new_page()
            
            # 设置页面加载超时
            page.set_default_timeout(30000)
            
            # 访问页面
            page.goto(url, wait_until="networkidle", timeout=30000)
            
            # 等待页面加载完成（微信文章可能需要额外时间）
            time.sleep(3)
            
            # 尝试滚动页面以触发懒加载内容
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)
            page.evaluate("window.scrollTo(0, 0)")
            
            # 获取页面HTML
            html_content = page.content()
            
            # 获取页面标题
            title = page.title()
            
            page.close()
            
            if not html_content:
                return {"success": False, "metadata": None, "markdown": "", "error": "Playwright获取HTML失败"}
            
            # 使用trafilatura提取正文
            markdown_content = trafilatura.extract(
                html_content,
                include_comments=False,
                include_tables=True,
                include_images=False,
                include_links=False,
                favor_precision=True,
                output_format="txt"
            )
            
            if not markdown_content:
                # 如果trafilatura提取失败，尝试直接获取文本
                text_content = page.inner_text("body")
                if text_content:
                    markdown_content = text_content.strip()
                else:
                    return {"success": False, "metadata": None, "markdown": "", "error": "正文提取失败"}
            
            # 提取元数据
            metadata = self._extract_metadata_from_html(html_content, url, title)
            
            logger.info(f"Playwright抓取成功: {metadata.title}")
            return {
                "success": True,
                "metadata": metadata,
                "markdown": markdown_content.strip()
            }
            
        except Exception as e:
            logger.error(f"Playwright抓取异常: {e}")
            return {"success": False, "metadata": None, "markdown": "", "error": str(e)}
    
    def _extract_metadata_from_html(self, html: str, url: str, title: str = "") -> ArticleMetadata:
        """从HTML中提取元数据"""
        author = ""
        publish_date = None
        source = "微信公众号"
        
        # 尝试提取作者
        author_patterns = [
            r'var\s+nickname\s*=\s*["\']([^"\']+)["\']',
            r'profile_nickname\s*["\']?\s*[:=]\s*["\']?([^"\'<]+)',
            r'js_author_name[^>]*>([^<]+)',
        ]
        for pattern in author_patterns:
            match = re.search(pattern, html)
            if match:
                author = match.group(1).strip()
                break
        
        # 尝试提取发布时间
        date_patterns = [
            r'var\s+ct\s*=\s*["\']?(\d{10,})["\']?',
            r'publish_time\s*[:=]\s*["\']?(\d{4}-\d{2}-\d{2})',
            r'(\d{4})年(\d{1,2})月(\d{1,2})日',
        ]
        for pattern in date_patterns:
            match = re.search(pattern, html)
            if match:
                try:
                    if len(match.group(0)) > 10:  # 时间戳
                        publish_date = datetime.fromtimestamp(int(match.group(1)))
                    elif '-' in match.group(0):  # YYYY-MM-DD
                        publish_date = datetime.strptime(match.group(1), "%Y-%m-%d")
                    else:  # 中文日期
                        publish_date = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
                    break
                except:
                    pass
        
        return ArticleMetadata(
            url=url,
            title=title,
            author=author,
            publish_date=publish_date,
            source=source
        )
    
    def _fetch_via_sogou(self, original_url: str) -> Dict:
        """
        通过搜狗微信搜索获取文章缓存
        策略：
        1. 提取文章标题或关键词
        2. 在搜狗搜索
        3. 从搜索结果中获取缓存页面
        """
        logger.info(f"尝试通过搜狗搜索获取: {original_url}")
        
        # 方式1：直接访问微信文章URL（搜狗可能缓存）
        try:
            response = requests.get(
                original_url,
                headers=self.sogou_headers,
                timeout=self.sogou_timeout,
                allow_redirects=True
            )
            response.raise_for_status()
            
            # 检查是否是验证码页面
            if 'captcha' in response.url or 'verify' in response.url:
                logger.warning("搜狗返回验证码页面")
                return {"success": False, "metadata": None, "markdown": "", "error": "搜狗验证码拦截"}
            
            html_content = response.text
            
            # 提取正文
            markdown_content = trafilatura.extract(
                html_content,
                include_comments=False,
                include_tables=True,
                favor_precision=True,
                output_format="txt"
            )
            
            if markdown_content:
                metadata = self._extract_metadata_from_html(html_content, original_url)
                return {
                    "success": True,
                    "metadata": metadata,
                    "markdown": markdown_content.strip()
                }
        except Exception as e:
            logger.warning(f"搜狗直接访问失败: {e}")
        
        # 方式2：通过搜索获取（提取关键词搜索）
        try:
            # 从URL提取文章ID作为搜索词
            match = re.search(r'sn=([a-f0-9]+)', original_url)
            if match:
                search_query = match.group(1)
            else:
                # 提取URL路径作为搜索词
                search_query = original_url.split('/')[-1].split('?')[0]
            
            search_url = f"https://weixin.sogou.com/weixin?type=2&query={quote(search_query)}"
            
            response = requests.get(
                search_url,
                headers=self.sogou_headers,
                timeout=self.sogou_timeout,
                allow_redirects=True
            )
            response.raise_for_status()
            
            # 检查验证码
            if 'captcha' in response.url or 'verify' in response.url:
                logger.warning("搜狗搜索被验证码拦截")
                return {"success": False, "metadata": None, "markdown": "", "error": "搜狗验证码拦截"}
            
            # 解析搜索结果，提取第一篇文章链接
            search_html = response.text
            
            # 提取搜索结果中的微信文章链接
            article_links = re.findall(r'href="(https://mp\.weixin\.qq\.com/s/[^"]+)"', search_html)
            
            if article_links:
                # 取第一个结果
                article_url = article_links[0]
                logger.info(f"搜狗搜索找到文章: {article_url}")
                
                # 访问文章
                article_response = requests.get(
                    article_url,
                    headers=self.sogou_headers,
                    timeout=self.sogou_timeout
                )
                article_response.raise_for_status()
                
                article_html = article_response.text
                markdown_content = trafilatura.extract(
                    article_html,
                    include_comments=False,
                    include_tables=True,
                    favor_precision=True,
                    output_format="txt"
                )
                
                if markdown_content:
                    metadata = self._extract_metadata_from_html(article_html, article_url)
                    return {
                        "success": True,
                        "metadata": metadata,
                        "markdown": markdown_content.strip()
                    }
        except Exception as e:
            logger.warning(f"搜狗搜索失败: {e}")
        
        return {"success": False, "metadata": None, "markdown": "", "error": "搜狗搜索无法获取文章"}
    
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
    
    def close(self):
        """关闭浏览器"""
        if self._playwright_available and hasattr(self, 'browser'):
            try:
                self.browser.close()
                self.playwright.stop()
                logger.info("Playwright浏览器已关闭")
            except Exception as e:
                logger.warning(f"关闭Playwright失败: {e}")
