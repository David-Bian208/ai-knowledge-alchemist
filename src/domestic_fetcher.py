"""
RSS源标题匹配模块
用AI HOT标题在国内RSS源中匹配文章，获取URL后再抓取全文
RSS比搜索页面更稳定，反爬弱
"""
import re
import time
import logging
from typing import Optional, Dict, List, Tuple
from urllib.parse import urlparse
import feedparser
import requests

logger = logging.getLogger(__name__)

# 国内RSS源配置
DOMESTIC_RSS_SOURCES = [
    {
        "name": "IT之家AI",
        "url": "https://www.ithome.com/rss/",
        "domain": "ithome.com",
        "enabled": True,
    },
    {
        "name": "量子位",
        "url": "https://www.qbitai.com/feed",
        "domain": "qbitai.com",
        "enabled": True,
    },
    {
        "name": "机器之心",
        "url": "https://www.jiqizhixin.com/feed",
        "domain": "jiqizhixin.com",
        "enabled": True,
    },
    {
        "name": "36氪",
        "url": "https://36kr.com/feed",
        "domain": "36kr.com",
        "enabled": True,
    },
    {
        "name": "极客公园",
        "url": "https://www.geekpark.net/rss",
        "domain": "geekpark.net",
        "enabled": True,
    },
    {
        "name": "开源中国",
        "url": "https://www.oschina.net/rss",
        "domain": "oschina.net",
        "enabled": True,
    },
]

# 关键词停用词
STOP_WORDS = set([
    "的", "了", "是", "在", "我", "有", "和", "就", "不", "人", "都", "一", "一个",
    "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好",
    "自己", "这", "那", "里", "啊", "吧", "呢", "吗", "啦", "哦", "呀",
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could", "should",
    "may", "might", "must", "shall", "can", "need", "dare", "ought", "used",
    "to", "of", "in", "for", "on", "with", "at", "by", "from", "as", "into",
    "through", "during", "before", "after", "above", "below", "between",
    "out", "off", "over", "under", "again", "further", "then", "once",
    "and", "but", "or", "nor", "not", "so", "yet", "both", "either", "neither",
    "each", "every", "all", "any", "few", "more", "most", "other", "some", "such",
    "no", "only", "own", "same", "than", "too", "very", "just", "because",
    "发布", "正式", "更新", "推出", "上线", "功能", "全新", "支持",
    "app", "version", "v2", "v3",
])


def extract_keywords(title: str, max_keywords: int = 3) -> List[str]:
    """从标题提取关键词"""
    if not title:
        return []
    
    title = re.sub(r'[【】\[\]{}（）\(\)]', ' ', title)
    title = re.sub(r'[\'"「」『』]', '', title)
    
    chinese_words = re.findall(r'[\u4e00-\u9fff]{2,6}', title)
    english_words = re.findall(r'[A-Za-z][A-Za-z0-9\-\.\+]{1,}', title)
    english_words = [w for w in english_words if len(w) > 2 and w.lower() not in STOP_WORDS]
    
    keywords = []
    seen = set()
    
    for word in english_words:
        lower = word.lower()
        if lower not in seen and lower not in STOP_WORDS:
            keywords.append(word)
            seen.add(lower)
    
    for word in chinese_words:
        if word not in seen and word not in STOP_WORDS:
            keywords.append(word)
            seen.add(word)
        
        if len(keywords) >= max_keywords:
            break
    
    return keywords[:max_keywords]


def calculate_title_similarity(title1: str, title2: str) -> float:
    """计算两个标题的相似度"""
    if not title1 or not title2:
        return 0.0
    
    t1 = title1.lower().strip()
    t2 = title2.lower().strip()
    
    if t1 == t2:
        return 1.0
    
    words1 = set(extract_keywords(t1))
    words2 = set(extract_keywords(t2))
    
    if not words1 or not words2:
        return 0.0
    
    overlap = len(words1 & words2)
    union = len(words1 | words2)
    
    if union == 0:
        return 0.0
    
    jaccard = overlap / union
    
    common = len(words1 & words2)
    min_len = min(len(words1), len(words2))
    
    if min_len == 0:
        return 0.0
    
    recall = common / min_len
    
    return 0.4 * jaccard + 0.6 * recall


def fetch_rss_items(rss_url: str, max_items: int = 50) -> List[Dict]:
    """获取RSS文章列表"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        resp = requests.get(rss_url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return []
        
        feed = feedparser.parse(resp.content)
        
        items = []
        for entry in feed.entries[:max_items]:
            items.append({
                "title": entry.get("title", ""),
                "url": entry.get("link", ""),
                "published": entry.get("published", ""),
                "summary": entry.get("summary", ""),
            })
        
        return items
    except Exception as e:
        logger.warning(f"RSS获取失败 {rss_url}: {e}")
        return []


def match_articles(aihot_title: str, rss_items: List[Dict], threshold: float = 0.5) -> Optional[Dict]:
    """在国内RSS文章中匹配AI HOT标题"""
    best_match = None
    best_score = 0.0
    
    for item in rss_items:
        score = calculate_title_similarity(aihot_title, item["title"])
        if score > best_score:
            best_score = score
            best_match = item
    
    if best_score >= threshold:
        return {
            "title": best_match["title"],
            "url": best_match["url"],
            "score": best_score,
        }
    
    return None


class RSSContentFetcher:
    """基于RSS的内容匹配抓取器"""
    
    def __init__(self):
        self._cache = {}
        self._cache_time = 0
        self._cache_ttl = 1800
    
    def _get_cached_items(self, source_name: str, rss_url: str) -> List[Dict]:
        """缓存RSS内容"""
        now = time.time()
        cache_key = f"{source_name}:{rss_url}"
        
        if cache_key in self._cache:
            cached_time, cached_items = self._cache[cache_key]
            if now - cached_time < self._cache_ttl:
                return cached_items
        
        items = fetch_rss_items(rss_url)
        self._cache[cache_key] = (now, items)
        return items
    
    def fetch_content(self, title: str, original_url: str = "") -> Optional[Dict]:
        """
        用标题在国内RSS源匹配并获取全文
        Returns:
            {"url": str, "title": str, "content": str, "source": str} or None
        """
        for source in DOMESTIC_RSS_SOURCES:
            if not source.get("enabled"):
                continue
            
            rss_items = self._get_cached_items(source["name"], source["url"])
            if not rss_items:
                continue
            
            match = match_articles(title, rss_items, threshold=0.4)
            if match:
                content = self._fetch_article_content(match["url"])
                if content and len(content) > 200:
                    return {
                        "url": match["url"],
                        "title": match["title"],
                        "content": content,
                        "source": source["name"],
                        "match_score": match["score"],
                    }
            
            time.sleep(1)
        
        return None
    
    def _fetch_article_content(self, url: str) -> Optional[str]:
        """抓取文章内容"""
        try:
            from src.crawler import WebCrawler
            crawler = WebCrawler(use_gallery_dl=False, use_media_crawler=False)
            
            domain = urlparse(url).hostname or ""
            if "x.com" in domain or "twitter.com" in domain:
                return None
            
            result = crawler._fetch_web(url, retry_count=2)
            if result.get("success"):
                content = result.get("markdown", "")
                if len(content) > 200:
                    return content
            
            return None
        except Exception as e:
            logger.warning(f"文章内容抓取失败: {e}")
            return None


_fetcher_instance = None

def get_fetcher() -> RSSContentFetcher:
    """获取抓取器实例"""
    global _fetcher_instance
    if _fetcher_instance is None:
        _fetcher_instance = RSSContentFetcher()
    return _fetcher_instance


def fetch_domestic_content(title: str, original_url: str = "") -> Optional[Dict]:
    """
    便捷函数：用标题在国内RSS源匹配并获取全文
    Returns:
        {"url": str, "title": str, "content": str, "source": str} or None
    """
    return get_fetcher().fetch_content(title, original_url)


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    
    test_titles = [
        "智谱GLM-5.1高速版发布：刷新全球大模型API速度纪录",
        "美团开源LongCat-Video-Avatar 1.5",
    ]
    
    fetcher = RSSContentFetcher()
    
    for title in test_titles:
        print(f"\n测试: {title}")
        result = fetcher.fetch_content(title)
        if result:
            print(f"  成功! 来源: {result['source']}")
            print(f"  URL: {result['url'][:70]}")
            print(f"  匹配度: {result.get('match_score', 0):.2f}")
            print(f"  内容长度: {len(result['content'])} 字符")
            print(f"  预览: {result['content'][:150]}...")
        else:
            print("  未找到匹配")
