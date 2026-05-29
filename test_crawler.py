#!/usr/bin/env python3
"""测试爬虫能否正常抓取指定URL"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.crawler import WebCrawler

urls_to_test = [
    "https://huggingface.co/blog/agent-glossary",
    "https://www.theverge.com/news/936945/pope-leo-letter-encyclical-ai-anthropic-labor-warfare",
    "https://runwayml.com/news/project-luxo",
    "https://x.com/Alibaba_Qwen/status/2058932656797368619",
]

crawler = WebCrawler(use_gallery_dl=True, use_media_crawler=True)

for url in urls_to_test:
    print(f"\n{'='*60}")
    print(f"测试: {url}")
    print("="*60)
    result = crawler.fetch(url)
    
    if result.get("success"):
        content = result.get("markdown", "")
        print(f"状态: ✅ 成功")
        print(f"内容长度: {len(content)} 字符")
        print(f"内容预览: {content[:200]}...")
    else:
        print(f"状态: ❌ 失败")
        print(f"错误: {result.get('error', 'unknown')}")
    print("="*60)
