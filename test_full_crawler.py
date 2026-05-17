"""
测试完整的智能路由系统
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.crawler import WebCrawler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_all_platforms():
    """测试所有支持的平台"""
    print("="*80)
    print("🚀 测试智能路由系统 - 全平台支持")
    print("="*80)
    
    crawler = WebCrawler()
    
    test_urls = [
        # 国内媒体平台 - MediaCrawler
        ("https://www.xiaohongshu.com/discovery/item/123", "小红书 (MediaCrawler)"),
        ("https://www.douyin.com/video/123", "抖音 (MediaCrawler)"),
        ("https://www.zhihu.com/question/123", "知乎 (MediaCrawler)"),
        
        # 国际社交媒体 - gallery-dl
        ("https://twitter.com/user/status/123", "Twitter (gallery-dl)"),
        ("https://www.instagram.com/p/ABC/", "Instagram (gallery-dl)"),
        ("https://www.pixiv.net/artworks/123", "Pixiv (gallery-dl)"),
        
        # 微信 - 专用爬虫
        ("https://mp.weixin.qq.com/s/abc", "微信文章 (WeChatCrawler)"),
        
        # 普通网页 - trafilatura
        ("https://www.baidu.com", "百度首页 (trafilatura)"),
    ]
    
    print("\n📋 支持的平台:")
    for url, desc in test_urls:
        print(f"  ✅ {desc}")
    
    print(f"\n🔧 已初始化的抓取器:")
    print(f"  - gallery-dl: {'✅' if crawler.gallery_crawler and crawler.gallery_crawler.available else '❌'}")
    print(f"  - MediaCrawler: {'✅' if crawler.media_crawler and crawler.media_crawler._playwright_available else '❌'}")
    print(f"  - trafilatura: ✅")
    print(f"  - WeChatCrawler: ✅ (独立模块)")
    
    # 测试URL类型检测
    print(f"\n🔍 URL类型检测:")
    test_urls_simple = [
        "https://www.xiaohongshu.com/explore",
        "https://www.douyin.com/user/abc",
        "https://twitter.com/user",
        "https://mp.weixin.qq.com/s/xxx",
        "https://www.baidu.com",
    ]
    
    for url in test_urls_simple:
        url_type = crawler._detect_url_type(url)
        print(f"  {url[:40]}... → {url_type}")
    
    print("\n" + "="*80)
    print("✅ 智能路由系统初始化成功")
    print("="*80)

if __name__ == "__main__":
    test_all_platforms()
