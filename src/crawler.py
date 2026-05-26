"""
爬虫模块 - 智能路由 + 通用HTML正文提取 + 多引擎降级
支持自动识别URL类型，路由到最合适的抓取器：
1. 社交媒体/图片站 → gallery-dl
2. 微信文章 → WeChatCrawler
3. 普通网页 → trafilatura → readability → 纯HTML提取 (三级降级)

高可靠性保障：
- 多引擎降级策略
- 失败重试 + User-Agent轮换
- 自适应超时
- 失败时保留标题+元数据作为后备内容
"""
import logging
import re
import signal
import random
import time
from typing import Dict, Optional
from datetime import datetime
from urllib.parse import urlparse
import requests

import trafilatura
from trafilatura.metadata import extract_metadata

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]

def _get_random_ua():
    return random.choice(USER_AGENTS)


class ArticleMetadata:
    """文章元数据"""
    
    def __init__(
        self,
        url: str,
        title: str = "",
        author: str = "",
        publish_date: Optional[datetime] = None,
        source: str = ""
    ):
        self.url = url
        self.title = title
        self.author = author
        self.publish_date = publish_date
        self.source = source
    
    def to_dict(self) -> Dict:
        return {
            "url": self.url,
            "title": self.title,
            "author": self.author,
            "publish_date": self.publish_date.isoformat() if self.publish_date else None,
            "source": self.source
        }
    
    def __repr__(self):
        return f"ArticleMetadata(title='{self.title}', author='{self.author}', date={self.publish_date})"


# 社交媒体/图片站域名列表
SOCIAL_MEDIA_DOMAINS = {
    'weibo.com', 'twitter.com', 'x.com', 'instagram.com',
    'pixiv.net', 'flickr.com', 'tumblr.com', 'deviantart.com',
    'artstation.com', 'pinterest.com', 'reddit.com',
    'danbooru.donmai.us', 'gelbooru.com', 'nhentai.net',
    'fanbox.cc', 'fanbox.fanbox.cc',
}

WECHAT_DOMAINS = {'mp.weixin.qq.com', 'weixin.qq.com'}

# 国内媒体平台域名列表 (MediaCrawler处理)
MEDIA_CRAWLER_DOMAINS = {
    'xiaohongshu.com', 'xhslink.com',  # 小红书
    'douyin.com', 'iesdouyin.com',  # 抖音
    'zhihu.com', 'zhimg.com',  # 知乎
    'tieba.baidu.com',  # 百度贴吧
    'kuaishou.com',  # 快手
}

# 视频平台域名列表（字幕提取）
VIDEO_PLATFORM_DOMAINS = {
    'bilibili.com', 'b23.tv',  # B站
    'youtube.com', 'youtu.be',  # YouTube
}


def detect_url_type(url: str) -> str:
    """
    检测URL类型，用于智能路由
    Returns:
        'social_media' | 'wechat' | 'web'
    """
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        hostname = hostname.lower()
        
        for domain in SOCIAL_MEDIA_DOMAINS:
            if domain in hostname:
                return 'social_media'
        
        for domain in WECHAT_DOMAINS:
            if domain in hostname:
                return 'wechat'
        
        return 'web'
    except:
        return 'web'


class WebCrawler:
    """智能路由网页爬虫"""
    
    def __init__(self, timeout: int = 30, use_gallery_dl: bool = True, gallery_dl_save_dir: str = "./gallery_dl_output", use_media_crawler: bool = True):
        self.timeout = timeout
        self.use_gallery_dl = use_gallery_dl
        self.use_media_crawler = use_media_crawler
        
        # 初始化gallery-dl抓取器
        if self.use_gallery_dl:
            try:
                from src.gallery_crawler import GalleryDLCrawler
                self.gallery_crawler = GalleryDLCrawler(save_dir=gallery_dl_save_dir)
                logger.info(f"gallery-dl抓取器已初始化")
            except Exception as e:
                logger.warning(f"gallery-dl初始化失败，将使用默认抓取: {e}")
                self.gallery_crawler = None
        else:
            self.gallery_crawler = None
        
        # 初始化MediaCrawler
        if self.use_media_crawler:
            try:
                from src.media_crawler import MediaCrawlerAdapter
                self.media_crawler = MediaCrawlerAdapter()
                logger.info(f"MediaCrawler已初始化")
            except Exception as e:
                logger.warning(f"MediaCrawler初始化失败，将使用默认抓取: {e}")
                self.media_crawler = None
        else:
            self.media_crawler = None
        
        # 初始化视频字幕提取器
        try:
            from src.video_subtitle import VideoSubtitleExtractor
            self.subtitle_extractor = VideoSubtitleExtractor()
            if self.subtitle_extractor.available:
                logger.info(f"视频字幕提取器已初始化")
        except Exception as e:
            logger.warning(f"视频字幕提取器初始化失败: {e}")
            self.subtitle_extractor = None
    
    def fetch(self, url: str) -> Dict:
        """
        智能抓取 - 根据URL类型自动选择最合适的抓取器
        路由优先级：
        1. 国内媒体平台（小红书/抖音/知乎等）→ MediaCrawler
        2. 国际社交媒体（Twitter/Instagram等）→ gallery-dl（如果不可用则跳过）
        3. 微信文章 → WeChatCrawler（提示）
        4. 普通网页 → trafilatura
        """
        logger.info(f"开始抓取: {url}")
        
        # 检测URL类型
        url_type = self._detect_url_type(url)
        logger.info(f"URL类型: {url_type}")
        
        # 社交媒体URL：gallery-dl不可用时直接跳过，不降级到trafilatura（反爬严重）
        if url_type == 'social_media':
            if self.gallery_crawler and self.gallery_crawler.available:
                return self._fetch_social_media(url)
            else:
                logger.warning(f"跳过社交媒体URL（gallery-dl不可用）: {url}")
                return {
                    "success": False,
                    "metadata": None,
                    "markdown": "",
                    "error": "社交媒体URL需要gallery-dl支持"
                }
        
        # 路由到对应的抓取器
        if url_type == 'video':
            return self._fetch_video_subtitle(url)
        elif url_type == 'media_crawler':
            return self._fetch_media_platform(url)
        elif url_type == 'wechat':
            return {
                "success": False,
                "metadata": None,
                "markdown": "",
                "error": "微信文章请使用WeChatCrawler.fetch_wechat_article()"
            }
        else:
            return self._fetch_web(url)
    
    def _detect_url_type(self, url: str) -> str:
        """检测URL类型"""
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname or ""
            hostname = hostname.lower()
            
            for domain in VIDEO_PLATFORM_DOMAINS:
                if domain in hostname:
                    return 'video'
            
            for domain in MEDIA_CRAWLER_DOMAINS:
                if domain in hostname:
                    return 'media_crawler'
            
            for domain in SOCIAL_MEDIA_DOMAINS:
                if domain in hostname:
                    return 'social_media'
            
            for domain in WECHAT_DOMAINS:
                if domain in hostname:
                    return 'wechat'
            
            return 'web'
        except:
            return 'web'
    
    def _fetch_video_subtitle(self, url: str) -> Dict:
        """提取B站/YouTube视频字幕"""
        if not self.subtitle_extractor or not self.subtitle_extractor.available:
            logger.warning(f"视频字幕提取器不可用，降级为普通抓取: {url}")
            return self._fetch_web(url)
        
        try:
            result = self.subtitle_extractor.extract_subtitle(url)
            
            if not result.get("success"):
                logger.warning(f"字幕提取失败，降级为普通抓取: {result.get('error')}")
                return self._fetch_web(url)
            
            title = result.get("title", "")
            author = result.get("author", "")
            subtitle_text = result.get("subtitle_text", "")
            
            # 如果没有字幕，用视频描述代替
            if not subtitle_text:
                subtitle_text = result.get("description", "")
                if subtitle_text:
                    logger.info(f"视频无字幕，使用描述代替: {title}")
                else:
                    logger.warning(f"视频无字幕且无描述: {title}")
                    return {
                        "success": False,
                        "metadata": None,
                        "markdown": "",
                        "error": "视频无字幕且无描述"
                    }
            
            article_meta = ArticleMetadata(
                url=url,
                title=f"[视频] {title}",
                author=author,
                source=self.subtitle_extractor.detect_platform(url),
            )
            
            # 构建markdown内容
            markdown_parts = []
            markdown_parts.append(f"# {title}")
            if author:
                markdown_parts.append(f"作者: {author}")
            markdown_parts.append(f"来源: {self.subtitle_extractor.detect_platform(url)}")
            markdown_parts.append("")
            markdown_parts.append("## 字幕内容")
            markdown_parts.append(subtitle_text)
            
            markdown = "\n\n".join(markdown_parts)
            
            logger.info(f"视频字幕提取成功: {title} ({len(subtitle_text)}字)")
            return {
                "success": True,
                "metadata": article_meta,
                "markdown": markdown.strip(),
                "content_type": "video_subtitle",
            }
            
        except Exception as e:
            logger.error(f"视频字幕提取异常，降级为普通抓取: {e}")
            return self._fetch_web(url)
    
    def _fetch_media_platform(self, url: str) -> Dict:
        """使用MediaCrawler抓取国内媒体平台"""
        if self.media_crawler and self.media_crawler._playwright_available:
            try:
                result = self.media_crawler.fetch(url)
                
                if result.get("success"):
                    metadata = result.get("metadata", {})
                    content = result.get("content", "")
                    
                    article_meta = ArticleMetadata(
                        url=url,
                        title=metadata.get("title", ""),
                        author=metadata.get("author", ""),
                        source=metadata.get("source", ""),
                    )
                    
                    markdown_parts = []
                    if metadata.get("title"):
                        markdown_parts.append(f"# {metadata['title']}")
                    if metadata.get("author"):
                        markdown_parts.append(f"作者: {metadata['author']}")
                    if content:
                        markdown_parts.append(content)
                    
                    markdown = "\n\n".join(markdown_parts)
                    
                    logger.info(f"MediaCrawler抓取成功: {article_meta.title}")
                    return {
                        "success": True,
                        "metadata": article_meta,
                        "markdown": markdown.strip(),
                        "content_type": result.get("platform", "media"),
                    }
                else:
                    logger.warning(f"MediaCrawler抓取失败，降级为普通抓取: {result.get('error')}")
                    return self._fetch_web(url)
            except Exception as e:
                logger.error(f"MediaCrawler抓取异常，降级为普通抓取: {e}")
                return self._fetch_web(url)
        else:
            logger.warning("MediaCrawler不可用，降级为普通抓取")
            return self._fetch_web(url)
    
    def _fetch_social_media(self, url: str) -> Dict:
        """使用gallery-dl抓取社交媒体内容"""
        if self.gallery_crawler and self.gallery_crawler.available:
            try:
                result = self.gallery_crawler.fetch(url, download=False)
                
                if result.get("success"):
                    metadata = result.get("metadata", {})
                    content = result.get("content", "")
                    images = result.get("images", [])
                    
                    article_meta = ArticleMetadata(
                        url=url,
                        title=metadata.get("title", ""),
                        author=metadata.get("author", ""),
                        source=metadata.get("source", ""),
                        publish_date=self._parse_date(metadata.get("publish_date", ""))
                    )
                    
                    markdown_parts = []
                    if metadata.get("title"):
                        markdown_parts.append(f"# {metadata['title']}")
                    if metadata.get("author"):
                        markdown_parts.append(f"作者: {metadata['author']}")
                    if metadata.get("description"):
                        markdown_parts.append(metadata['description'])
                    if content:
                        markdown_parts.append(content)
                    if images:
                        markdown_parts.append(f"\n## 图片 ({len(images)}张)")
                        for i, img_url in enumerate(images[:10], 1):
                            markdown_parts.append(f"![图片{i}]({img_url})")
                    
                    markdown = "\n\n".join(markdown_parts)
                    
                    logger.info(f"社交媒体抓取成功: {article_meta.title}, {len(images)}张图片")
                    return {
                        "success": True,
                        "metadata": article_meta,
                        "markdown": markdown.strip(),
                        "images": images,
                        "content_type": "social_media"
                    }
                else:
                    logger.warning(f"gallery-dl抓取失败，降级为普通抓取: {result.get('error')}")
                    return self._fetch_web(url)
            except Exception as e:
                logger.error(f"gallery-dl抓取异常，降级为普通抓取: {e}")
                return self._fetch_web(url)
        else:
            logger.warning("gallery-dl不可用，降级为普通抓取")
            return self._fetch_web(url)
    
    def _fetch_web(self, url: str, retry_count: int = 3) -> Dict:
        """使用多引擎降级策略抓取普通网页（带重试）"""
        html_content = None
        
        for attempt in range(retry_count):
            try:
                timeout = 15 + attempt * 5
                ua = _get_random_ua()
                headers = {
                    "User-Agent": ua,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Accept-Encoding": "gzip, deflate",
                    "Connection": "keep-alive",
                }
                
                resp = requests.get(url, timeout=timeout, headers=headers, allow_redirects=True)
                if resp.status_code == 200:
                    html_content = resp.text
                    break
                elif resp.status_code in [403, 429, 503]:
                    wait = (attempt + 1) * 3
                    logger.warning(f"HTTP {resp.status_code}，等待{wait}秒后重试 ({attempt+1}/{retry_count})")
                    time.sleep(wait)
                else:
                    logger.error(f"抓取失败，HTTP {resp.status_code}: {url}")
                    return {"success": False, "metadata": None, "markdown": "", "error": f"HTTP {resp.status_code}"}
            except requests.exceptions.Timeout:
                logger.warning(f"抓取超时 (尝试{attempt+1}/{retry_count}): {url}")
                if attempt < retry_count - 1:
                    time.sleep(2)
            except requests.exceptions.RequestException as e:
                logger.warning(f"请求异常 (尝试{attempt+1}/{retry_count}): {url}, {e}")
                if attempt < retry_count - 1:
                    time.sleep(2)
        
        if not html_content:
            logger.error(f"抓取失败，已重试{retry_count}次: {url}")
            return {"success": False, "metadata": None, "markdown": "", "error": "多次重试后仍无法获取页面"}
        
        result = self._extract_with_fallback(html_content, url)
        if result["success"]:
            return result
        
        return {"success": False, "metadata": None, "markdown": "", "error": "所有引擎提取正文失败"}
    
    def _extract_with_fallback(self, html_content: str, url: str) -> Dict:
        """多引擎降级提取正文：trafilatura → readability → 纯HTML"""
        
        metadata = self._extract_metadata(html_content, url)
        
        result = self._try_trafilatura(html_content)
        if result and len(result) > 100:
            logger.info(f"trafilatura提取成功: {metadata.title} ({len(result)}字符)")
            return {
                "success": True,
                "metadata": metadata,
                "markdown": result.strip()
            }
        
        result = self._try_readability(html_content)
        if result and len(result) > 100:
            logger.info(f"readability提取成功: {metadata.title} ({len(result)}字符)")
            return {
                "success": True,
                "metadata": metadata,
                "markdown": result.strip()
            }
        
        result = self._try_plain_html(html_content)
        if result and len(result) > 50:
            logger.info(f"纯HTML提取成功: {metadata.title} ({len(result)}字符)")
            return {
                "success": True,
                "metadata": metadata,
                "markdown": result.strip()
            }
        
        logger.error(f"所有引擎提取失败: {url}")
        return {"success": False, "metadata": metadata, "markdown": "", "error": "所有引擎提取正文失败"}
    
    def _try_trafilatura(self, html_content: str) -> Optional[str]:
        """尝试用trafilatura提取正文"""
        try:
            result = trafilatura.extract(
                html_content,
                include_comments=False,
                include_tables=True,
                include_images=True,
                include_links=True,
                favor_precision=True,
                output_format="markdown"
            )
            return result
        except Exception as e:
            logger.warning(f"trafilatura提取失败: {e}")
            return None
    
    def _try_readability(self, html_content: str) -> Optional[str]:
        """尝试用readability-lxml提取正文"""
        try:
            from lxml import html
            from readability import Document
            
            doc = Document(html_content)
            title = doc.title() or ""
            content_html = doc.summary(html_partial=True)
            
            if not content_html or len(content_html) < 50:
                return None
            
            parts = []
            if title:
                parts.append(f"# {title}")
            parts.append("")
            
            cleaned = re.sub(r'<script[^>]*>.*?</script>', '', content_html, flags=re.DOTALL)
            cleaned = re.sub(r'<style[^>]*>.*?</style>', '', cleaned, flags=re.DOTALL)
            
            cleaned = re.sub(r'<br\s*/?>', '\n', cleaned)
            cleaned = re.sub(r'</?(?:p|div|article|section|header|footer|h[1-6])[^>]*>', '\n\n', cleaned)
            cleaned = re.sub(r'</?(?:li|dt|dd)[^>]*>', '\n', cleaned)
            cleaned = re.sub(r'<li>', '• ', cleaned)
            
            cleaned = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r'[\2](\1)', cleaned)
            cleaned = re.sub(r'<img[^>]*src="([^"]*)"[^>]*>', r'\n![image](\1)\n', cleaned)
            
            cleaned = re.sub(r'<[^>]+>', '', cleaned)
            cleaned = re.sub(r'&nbsp;', ' ', cleaned)
            cleaned = re.sub(r'&amp;', '&', cleaned)
            cleaned = re.sub(r'&lt;', '<', cleaned)
            cleaned = re.sub(r'&gt;', '>', cleaned)
            cleaned = re.sub(r'&quot;', '"', cleaned)
            cleaned = re.sub(r'&#\d+;', '', cleaned)
            
            cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
            cleaned = cleaned.strip()
            
            if cleaned:
                parts.append(cleaned)
            return '\n'.join(parts)
        except ImportError:
            logger.debug("readability-lxml未安装，跳过")
            return None
        except Exception as e:
            logger.warning(f"readability提取失败: {e}")
            return None
    
    def _try_plain_html(self, html_content: str) -> Optional[str]:
        """从HTML中提取纯文本作为最后降级"""
        try:
            from lxml import html
            
            tree = html.fromstring(html_content)
            
            for tag in tree.xpath('.//script|.//style|.//noscript|.//nav|.//footer|.//header|.//aside'):
                tag.drop_tree()
            
            title_el = tree.xpath('//title')
            title = title_el[0].text.strip() if title_el else ""
            
            body_els = tree.xpath('//body')
            if body_els:
                text = body_els[0].text_content()
            else:
                text = tree.text_content()
            
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            seen = set()
            unique_lines = []
            for line in lines:
                if line not in seen and len(line) > 3:
                    seen.add(line)
                    unique_lines.append(line)
            
            parts = []
            if title:
                parts.append(f"# {title}")
                parts.append("")
            parts.extend(unique_lines[:200])
            
            result = '\n'.join(parts)
            return result if len(result) > 50 else None
        except Exception as e:
            logger.warning(f"纯HTML提取失败: {e}")
            return None
    
    def _extract_metadata(self, html_content: str, url: str) -> ArticleMetadata:
        """提取文章元数据"""
        title = ""
        author = ""
        publish_date = None
        source = ""
        
        try:
            # 使用 trafilatura 的 extract_metadata 函数
            record = extract_metadata(html_content)
            
            if record:
                # record 是 TrafilaturaMetadata 对象，用 getattr 安全访问
                title = getattr(record, 'title', '') or ''
                author = getattr(record, 'author', '') or ''
                source = getattr(record, 'sitename', '') or ''
                
                # 解析日期
                date_str = getattr(record, 'date', '') or ''
                if date_str:
                    try:
                        publish_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    except:
                        try:
                            publish_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
                        except:
                            pass
        except Exception as e:
            logger.warning(f"trafilatura 元数据提取失败: {e}")
        
        # 如果 trafilatura 没提取到标题，尝试从 HTML <title> 标签中提取
        if not title:
            try:
                match = re.search(r'<title[^>]*>(.*?)</title>', html_content, re.DOTALL | re.IGNORECASE)
                if match:
                    title = match.group(1).strip()
                    # 清理标题中的网站名后缀
                    title = re.sub(r'\s*[-|–—]\s*\w+.*$', '', title)
            except:
                pass
        
        # 如果还没提取到标题，从 URL 推断
        if not title:
            title = url.split("/")[-1].split("?")[0] or url
        
        # 如果没提取到来源，从域名推断
        if not source:
            try:
                parsed = urlparse(url)
                source = parsed.hostname or ""
            except:
                pass
        
        return ArticleMetadata(
            url=url,
            title=title,
            author=author,
            publish_date=publish_date,
            source=source
        )
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """解析日期字符串"""
        if not date_str:
            return None
        
        try:
            return datetime.fromisoformat(date_str)
        except:
            try:
                return datetime.strptime(date_str, "%Y-%m-%d")
            except:
                return None
