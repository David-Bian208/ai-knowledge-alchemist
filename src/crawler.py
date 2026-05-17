"""
爬虫模块 - 智能路由 + 通用HTML正文提取
支持自动识别URL类型，路由到最合适的抓取器：
1. 社交媒体/图片站 → gallery-dl
2. 微信文章 → WeChatCrawler
3. 普通网页 → trafilatura
"""
import logging
import re
from typing import Dict, Optional
from datetime import datetime
from urllib.parse import urlparse

import trafilatura
from trafilatura.metadata import extract_metadata

logger = logging.getLogger(__name__)


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
    'bilibili.com', 'b23.tv',  # B站
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
    
    def fetch(self, url: str) -> Dict:
        """
        智能抓取 - 根据URL类型自动选择最合适的抓取器
        路由优先级：
        1. 国内媒体平台（小红书/抖音/知乎等）→ MediaCrawler
        2. 国际社交媒体（Twitter/Instagram等）→ gallery-dl
        3. 微信文章 → WeChatCrawler（提示）
        4. 普通网页 → trafilatura
        """
        logger.info(f"开始抓取: {url}")
        
        # 检测URL类型
        url_type = self._detect_url_type(url)
        logger.info(f"URL类型: {url_type}")
        
        # 路由到对应的抓取器
        if url_type == 'media_crawler':
            return self._fetch_media_platform(url)
        elif url_type == 'social_media':
            return self._fetch_social_media(url)
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
    
    def _fetch_web(self, url: str) -> Dict:
        """使用trafilatura抓取普通网页"""
        try:
            # 下载网页内容
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                logger.error(f"抓取失败，无法下载: {url}")
                return {"success": False, "metadata": None, "markdown": "", "error": "无法下载网页"}
            
            # 提取正文
            result = trafilatura.extract(
                downloaded,
                include_comments=False,
                include_tables=True,
                include_images=False,
                include_links=False,
                favor_precision=True,
                output_format="txt"
            )
            
            if not result:
                logger.error(f"提取正文失败: {url}")
                return {"success": False, "metadata": None, "markdown": "", "error": "无法提取正文内容"}
            
            # 提取元数据
            metadata = self._extract_metadata(downloaded, url)
            
            logger.info(f"抓取成功: {metadata.title}")
            return {
                "success": True,
                "metadata": metadata,
                "markdown": result.strip()
            }
            
        except Exception as e:
            logger.error(f"抓取异常: {url}, 错误: {e}")
            return {"success": False, "metadata": None, "markdown": "", "error": str(e)}
    
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
