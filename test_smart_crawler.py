"""
测试智能路由爬虫 - 验证gallery-dl集成
"""
import logging
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.crawler import WebCrawler, detect_url_type

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_url_detection():
    """测试URL类型检测"""
    print("\n" + "="*80)
    print("🎯 测试URL类型检测")
    print("="*80)
    
    test_urls = [
        ("https://weibo.com/123456", "微博"),
        ("https://twitter.com/user/status/123", "Twitter"),
        ("https://x.com/user/post/456", "X/Twitter"),
        ("https://www.instagram.com/p/ABC123/", "Instagram"),
        ("https://www.pixiv.net/artworks/123456", "Pixiv"),
        ("https://mp.weixin.qq.com/s/abc123", "微信公众号"),
        ("https://www.baidu.com", "普通网页"),
        ("https://github.com/user/repo", "GitHub"),
    ]
    
    for url, desc in test_urls:
        url_type = detect_url_type(url)
        print(f"  {desc}: {url_type}")


def test_gallery_dl_integration():
    """测试gallery-dl集成"""
    print("\n" + "="*80)
    print("🎯 测试gallery-dl集成（社交媒体抓取）")
    print("="*80)
    
    crawler = WebCrawler(use_gallery_dl=True)
    
    # 测试微博（ gallery-dl支持的站点）
    test_url = "https://weibo.com"
    print(f"\n📱 测试: 微博")
    print(f"URL: {test_url}")
    
    result = crawler.fetch(test_url)
    print(f"成功: {result.get('success')}")
    if result.get('success'):
        metadata = result.get('metadata')
        if metadata:
            print(f"标题: {metadata.title}")
            print(f"作者: {metadata.author}")
            print(f"来源: {metadata.source}")
        print(f"内容类型: {result.get('content_type', 'web')}")
        print(f"Markdown长度: {len(result.get('markdown', ''))}")
    else:
        print(f"错误: {result.get('error')}")


def test_web_crawling():
    """测试普通网页抓取"""
    print("\n" + "="*80)
    print("🎯 测试普通网页抓取（trafilatura）")
    print("="*80)
    
    crawler = WebCrawler(use_gallery_dl=True)
    
    # 测试普通网页
    test_url = "https://www.baidu.com"
    print(f"\n🌐 测试: 百度首页")
    print(f"URL: {test_url}")
    
    result = crawler.fetch(test_url)
    print(f"成功: {result.get('success')}")
    if result.get('success'):
        metadata = result.get('metadata')
        if metadata:
            print(f"标题: {metadata.title}")
            print(f"作者: {metadata.author}")
            print(f"来源: {metadata.source}")
        print(f"内容类型: {result.get('content_type', 'web')}")
        print(f"Markdown长度: {len(result.get('markdown', ''))}")
    else:
        print(f"错误: {result.get('error')}")


def test_wechat_detection():
    """测试微信文章检测"""
    print("\n" + "="*80)
    print("🎯 测试微信文章检测")
    print("="*80)
    
    crawler = WebCrawler(use_gallery_dl=True)
    
    test_url = "https://mp.weixin.qq.com/s/r6CE2U3Y0-pU05wF3_PuTQ"
    print(f"\n💬 测试: 微信文章")
    print(f"URL: {test_url}")
    
    result = crawler.fetch(test_url)
    print(f"成功: {result.get('success')}")
    if not result.get('success'):
        print(f"提示: {result.get('error')}")


def main():
    """运行所有测试"""
    print("🚀 开始测试智能路由爬虫")
    
    test_url_detection()
    test_gallery_dl_integration()
    test_web_crawling()
    test_wechat_detection()
    
    print("\n" + "="*80)
    print("✅ 测试完成")
    print("="*80)


if __name__ == "__main__":
    main()
