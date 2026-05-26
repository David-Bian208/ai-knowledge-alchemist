"""
搜索引擎模块
支持：
1. 搜狗微信搜索
2. DuckDuckGo通用搜索（免费，需代理）
3. Tavily搜索（AI Agent专用）
4. Serper.dev（Google搜索代理）
5. Brave Search API
6. Exa.ai（语义搜索）
7. Jina Reader（URL转Markdown）
"""
import re
import os
import time
import logging
import requests
from typing import List, Dict, Optional
from urllib.parse import quote, urlparse

logger = logging.getLogger(__name__)


class SearchEngineFactory:
    """搜索引擎工厂 - 根据配置创建搜索引擎实例"""
    
    @staticmethod
    def create(engine: str, **kwargs) -> Optional['BaseSearchEngine']:
        """
        创建搜索引擎实例
        Args:
            engine: 搜索引擎名称
            **kwargs: 配置参数
        Returns:
            搜索引擎实例
        """
        engines = {
            'sogou': SogouWechatSearch,
            'duckduckgo': DuckDuckGoSearch,
            'tavily': TavilySearch,
            'serper': SerperSearch,
            'brave': BraveSearch,
            'exa': ExaSearch,
            'jina': JinaReader,
        }
        
        if engine.lower() in engines:
            return engines[engine.lower()](**kwargs)
        else:
            logger.warning(f"不支持的搜索引擎: {engine}")
            return None


class BaseSearchEngine:
    """搜索引擎基类"""
    
    def search(self, keyword: str, max_count: int = 10) -> List[Dict]:
        raise NotImplementedError
    
    def fetch_url(self, url: str) -> Optional[Dict]:
        raise NotImplementedError


class SogouWechatSearch(BaseSearchEngine):
    """搜狗微信搜索引擎"""
    
    def __init__(self, **kwargs):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        self.timeout = 30
    
    def search(self, keyword: str, max_count: int = 10) -> List[Dict]:
        """
        搜索微信公众号文章
        """
        logger.info(f"搜狗微信搜索: {keyword}")
        
        search_url = f"https://weixin.sogou.com/weixin?type=2&query={quote(keyword)}"
        
        try:
            response = requests.get(
                search_url,
                headers=self.headers,
                timeout=self.timeout,
                allow_redirects=True
            )
            response.raise_for_status()
            
            if 'captcha' in response.url or 'verify' in response.url:
                logger.warning("搜狗微信搜索被验证码拦截")
                return []
            
            html = response.text
            results = self._parse_search_results(html)
            
            return results[:max_count]
            
        except Exception as e:
            logger.error(f"搜狗微信搜索失败: {e}")
            return []
    
    def _parse_search_results(self, html: str) -> List[Dict]:
        """解析搜狗搜索结果"""
        results = []
        
        try:
            # 搜狗返回的链接格式是 /link?url=xxx（重定向链接）
            links = re.findall(r'href="(/link\?url=[^"]+)"', html)
            
            # 提取标题 - 在 h3 > a 标签内
            title_pattern = r'<h3[^>]*>.*?<a[^>]*>(.*?)</a>.*?</h3>'
            titles = re.findall(title_pattern, html, re.DOTALL)
            
            # 提取摘要 - 在 class="txt-info" 或类似区域
            summaries = re.findall(r'class="txt-info"[^>]*>(.*?)(?:</p>|</div>)', html, re.DOTALL)
            
            for i in range(min(len(links), len(titles))):
                # 每个链接出现两次（图片和文本），取唯一
                if i % 2 == 0:
                    link = f"https://weixin.sogou.com{links[i]}"
                    title = re.sub(r'<[^>]+>', '', titles[i]).strip()
                    # 清理HTML实体
                    title = title.replace('&ldquo;', '"').replace('&rdquo;', '"').replace('&middot;', '·')
                    title = title.replace('&nbsp;', ' ')
                    
                    summary = ""
                    summary_idx = i // 2
                    if summary_idx < len(summaries):
                        summary = re.sub(r'<[^>]+>', '', summaries[summary_idx]).strip()
                    
                    if title:
                        results.append({
                            "title": title,
                            "url": link,
                            "author": "",
                            "read_count": 0,
                            "date": "",
                            "summary": summary[:200],
                            "source": "微信公众号"
                        })
        except Exception as e:
            logger.error(f"解析搜狗搜索结果失败: {e}")
        
        return results
    
    def fetch_url(self, url: str) -> Optional[Dict]:
        """搜狗不支持直接抓取URL"""
        return None


class DuckDuckGoSearch(BaseSearchEngine):
    """DuckDuckGo搜索引擎（免费，需代理）"""
    
    def __init__(self, proxy: str = "http://127.0.0.1:7890", **kwargs):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        self.timeout = 30
        self.proxies = {
            "http": proxy,
            "https": proxy
        } if proxy else None
    
    def search(self, keyword: str, max_count: int = 10) -> List[Dict]:
        """
        通用网页搜索
        """
        logger.info(f"DuckDuckGo搜索: {keyword}")
        
        search_url = f"https://html.duckduckgo.com/html/?q={quote(keyword)}"
        
        try:
            response = requests.get(
                search_url,
                headers=self.headers,
                timeout=self.timeout,
                proxies=self.proxies
            )
            response.raise_for_status()
            
            html = response.text
            results = self._parse_results(html)
            
            return results[:max_count]
            
        except Exception as e:
            logger.error(f"DuckDuckGo搜索失败: {e}")
            return []
    
    def _parse_results(self, html: str) -> List[Dict]:
        """解析DuckDuckGo搜索结果"""
        results = []
        
        try:
            items = re.findall(
                r'<a[^>]*?class="result__a"[^>]*?href="([^"]+)".*?>(.*?)</a>.*?<a[^>]*?class="result__snippet".*?>(.*?)</a>',
                html,
                re.DOTALL
            )
            
            for url, title, snippet in items:
                title = re.sub(r'<[^>]+>', '', title).strip()
                snippet = re.sub(r'<[^>]+>', '', snippet).strip()
                
                if title and url:
                    domain = urlparse(url).hostname or ""
                    results.append({
                        "title": title,
                        "url": url,
                        "author": domain,
                        "read_count": 0,
                        "date": "",
                        "summary": snippet[:200],
                        "source": domain
                    })
        except Exception as e:
            logger.error(f"解析DuckDuckGo搜索结果失败: {e}")
        
        return results
    
    def fetch_url(self, url: str) -> Optional[Dict]:
        """DuckDuckGo不支持直接抓取URL"""
        return None


class TavilySearch(BaseSearchEngine):
    """Tavily搜索引擎（AI Agent专用）"""
    
    def __init__(self, api_key: str = None, **kwargs):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        self.base_url = "https://api.tavily.com/search"
        self.timeout = 30
    
    def search(self, keyword: str, max_count: int = 10) -> List[Dict]:
        """Tavily搜索"""
        if not self.api_key:
            logger.warning("TAVILY_API_KEY 未配置")
            return []
        
        logger.info(f"Tavily搜索: {keyword}")
        
        try:
            response = requests.post(
                self.base_url,
                json={
                    "api_key": self.api_key,
                    "query": keyword,
                    "max_results": max_count,
                    "include_answer": True,
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            for item in data.get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "author": "",
                    "read_count": 0,
                    "date": "",
                    "summary": item.get("content", "")[:200],
                    "source": urlparse(item.get("url", "")).hostname or ""
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Tavily搜索失败: {e}")
            return []
    
    def fetch_url(self, url: str) -> Optional[Dict]:
        """Tavily不支持直接抓取URL"""
        return None


class SerperSearch(BaseSearchEngine):
    """Serper.dev（Google搜索代理）"""
    
    def __init__(self, api_key: str = None, **kwargs):
        self.api_key = api_key or os.getenv("SERPER_API_KEY")
        self.base_url = "https://google.serper.dev/search"
        self.timeout = 30
    
    def search(self, keyword: str, max_count: int = 10) -> List[Dict]:
        """Serper搜索"""
        if not self.api_key:
            logger.warning("SERPER_API_KEY 未配置")
            return []
        
        logger.info(f"Serper搜索: {keyword}")
        
        try:
            response = requests.post(
                self.base_url,
                headers={"X-API-KEY": self.api_key, "Content-Type": "application/json"},
                json={"q": keyword, "num": max_count},
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            for item in data.get("organic", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "author": "",
                    "read_count": 0,
                    "date": item.get("date", ""),
                    "summary": item.get("snippet", "")[:200],
                    "source": urlparse(item.get("link", "")).hostname or ""
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Serper搜索失败: {e}")
            return []
    
    def fetch_url(self, url: str) -> Optional[Dict]:
        """Serper不支持直接抓取URL"""
        return None


class BraveSearch(BaseSearchEngine):
    """Brave Search API"""
    
    def __init__(self, api_key: str = None, **kwargs):
        self.api_key = api_key or os.getenv("BRAVE_API_KEY")
        self.base_url = "https://api.search.brave.com/res/v1/web/search"
        self.timeout = 30
    
    def search(self, keyword: str, max_count: int = 10) -> List[Dict]:
        """Brave搜索"""
        if not self.api_key:
            logger.warning("BRAVE_API_KEY 未配置")
            return []
        
        logger.info(f"Brave搜索: {keyword}")
        
        try:
            response = requests.get(
                self.base_url,
                headers={"X-Subscription-Token": self.api_key},
                params={"q": keyword, "count": max_count},
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            for item in data.get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "author": "",
                    "read_count": 0,
                    "date": "",
                    "summary": item.get("description", "")[:200],
                    "source": urlparse(item.get("url", "")).hostname or ""
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Brave搜索失败: {e}")
            return []
    
    def fetch_url(self, url: str) -> Optional[Dict]:
        """Brave不支持直接抓取URL"""
        return None


class ExaSearch(BaseSearchEngine):
    """Exa.ai（语义搜索）"""
    
    def __init__(self, api_key: str = None, **kwargs):
        self.api_key = api_key or os.getenv("EXA_API_KEY")
        self.base_url = "https://api.exa.ai/search"
        self.timeout = 30
    
    def search(self, keyword: str, max_count: int = 10) -> List[Dict]:
        """Exa语义搜索"""
        if not self.api_key:
            logger.warning("EXA_API_KEY 未配置")
            return []
        
        logger.info(f"Exa搜索: {keyword}")
        
        try:
            response = requests.post(
                f"{self.base_url}/search",
                headers={
                    "x-api-key": self.api_key,
                    "Content-Type": "application/json"
                },
                json={
                    "query": keyword,
                    "numResults": max_count,
                    "useAutoprompt": True,
                    "contents": {"highlights": True, "summary": True},
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            for item in data.get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "author": "",
                    "read_count": 0,
                    "date": "",
                    "summary": item.get("highlight", item.get("summary", ""))[:200],
                    "source": urlparse(item.get("url", "")).hostname or ""
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Exa搜索失败: {e}")
            return []
    
    def fetch_url(self, url: str) -> Optional[Dict]:
        """Exa不支持直接抓取URL"""
        return None


class JinaReader(BaseSearchEngine):
    """Jina Reader（URL转Markdown）"""
    
    def __init__(self, api_key: str = None, **kwargs):
        self.api_key = api_key or os.getenv("JINA_API_KEY")
        self.base_url = "https://r.jina.ai/"
        self.timeout = 60
        self.headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
        }
    
    def search(self, keyword: str, max_count: int = 10) -> List[Dict]:
        """Jina Reader不支持搜索，只支持URL提取"""
        logger.warning("Jina Reader不支持搜索，请使用其他搜索引擎")
        return []
    
    def fetch_url(self, url: str) -> Optional[Dict]:
        """
        提取URL内容为干净的Markdown
        """
        if not url:
            return None
        
        logger.info(f"Jina Reader提取URL: {url}")
        
        try:
            response = requests.get(
                f"{self.base_url}{url}",
                headers=self.headers,
                timeout=self.timeout,
                allow_redirects=True
            )
            response.raise_for_status()
            
            data = response.json()
            
            return {
                "title": data.get("title", ""),
                "url": url,
                "markdown": data.get("content", ""),
                "author": data.get("author", ""),
                "source": urlparse(url).hostname or "",
            }
            
        except Exception as e:
            logger.error(f"Jina Reader提取失败: {e}")
            return None
