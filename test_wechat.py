"""
测试微信文章抓取功能
测试URL: https://mp.weixin.qq.com/s/r6CE2U3Y0-pU05wF3_PuTQ
"""
import logging
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.wechat_crawler import WeChatCrawler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_wechat_crawler():
    """测试微信文章抓取"""
    
    test_url = "https://mp.weixin.qq.com/s/r6CE2U3Y0-pU05wF3_PuTQ"
    
    print("=" * 80)
    print("测试微信文章抓取功能")
    print(f"测试URL: {test_url}")
    print("=" * 80)
    
    # 创建爬虫实例
    crawler = WeChatCrawler(use_playwright=True)
    
    try:
        # 抓取文章
        result = crawler.fetch_wechat_article(test_url)
        
        print("\n" + "=" * 80)
        print("抓取结果:")
        print("=" * 80)
        print(f"成功: {result.get('success')}")
        
        if result.get('success'):
            metadata = result.get('metadata')
            if metadata:
                print(f"\n标题: {metadata.title}")
                print(f"作者: {metadata.author}")
                print(f"发布日期: {metadata.publish_date}")
                print(f"来源: {metadata.source}")
                print(f"URL: {metadata.url}")
            
            markdown = result.get('markdown', '')
            print(f"\n正文长度: {len(markdown)} 字符")
            print(f"\n正文预览 (前500字符):")
            print("-" * 80)
            print(markdown[:500])
            print("-" * 80)
        else:
            print(f"\n错误: {result.get('error')}")
        
        print("=" * 80)
        
    finally:
        # 关闭浏览器
        crawler.close()

if __name__ == "__main__":
    test_wechat_crawler()
