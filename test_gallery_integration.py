"""
测试gallery-dl集成效果 - 用具体URL格式
"""
import sys
import subprocess
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.gallery_crawler import GalleryDLCrawler

def test_gallery_dl_direct():
    """直接使用gallery-dl测试实际抓取能力"""
    print("="*80)
    print("🎯 测试 gallery-dl 实际抓取能力")
    print("="*80)
    
    crawler = GalleryDLCrawler(save_dir="./test_gallery_output")
    
    # 检查可用性
    print(f"\ngallery-dl 可用: {crawler.available}")
    print(f"版本: {crawler.version}")
    
    # 获取支持的站点数量
    sites = crawler.get_supported_sites()
    print(f"支持站点数: {len(sites)}")
    
    # 测试关键平台
    key_platforms = ['weibo', 'twitter', 'instagram', 'pixiv', 'reddit', 'flickr', 'tumblr', 'deviantart', 'artstation', 'pinterest']
    
    print("\n📋 关键平台支持:")
    for platform in key_platforms:
        supported = any(platform in s['name'].lower() for s in sites)
        status = "✅" if supported else "❌"
        print(f"  {status} {platform}")
    
    # 测试is_supported方法
    print("\n🔍 URL类型检测:")
    test_urls = [
        "https://weibo.com/123456",
        "https://twitter.com/user/status/123",
        "https://x.com/user/post/456",
        "https://www.instagram.com/p/ABC/",
        "https://www.pixiv.net/artworks/123",
        "https://www.reddit.com/r/pics/abc/",
        "https://mp.weixin.qq.com/s/abc",
        "https://www.baidu.com",
    ]
    
    for url in test_urls:
        supported = crawler.is_supported(url)
        status = "✅" if supported else "❌"
        print(f"  {status} {url}")

if __name__ == "__main__":
    test_gallery_dl_direct()
