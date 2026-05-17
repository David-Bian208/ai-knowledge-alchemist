"""
爬虫模块 - 通用HTML正文提取
使用 trafilatura 库自动抓取网页正文，去除广告/导航/推荐等噪音
提取标题/发布时间/作者/来源等元数据，转为干净的Markdown格式
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


class WebCrawler:
    """通用网页爬虫"""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
    
    def fetch(self, url: str) -> Dict:
        """
        抓取单个URL，提取正文和元数据
        Args:
            url: 网页URL
        Returns:
            {
                "metadata": ArticleMetadata,
                "markdown": str,  # 干净的Markdown正文
                "success": bool
            }
        """
        logger.info(f"开始抓取: {url}")
        
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
