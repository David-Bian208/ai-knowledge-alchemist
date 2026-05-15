#!/usr/bin/env python3
"""
知识炼金术 Agent V1.0 命令行入口
支持URL抓取处理和本地文件处理两种模式
"""
import os
import sys
import json
import argparse
import logging
from typing import Dict, Any

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.processor import KnowledgeAlchemist
from src.archiver import Archiver

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("main")


def process_url(url: str, output_format: str = "pretty") -> Dict[str, Any]:
    """
    处理URL，跑完6步全流程并归档
    """
    logger.info(f"开始处理URL: {url}")
    
    try:
        # 创建处理引擎
        alchemist = KnowledgeAlchemist()
        archiver = Archiver()
        
        # 先抓取网页获取正文
        crawl_result = alchemist.crawler.fetch(url)
        if not crawl_result.get("success"):
            raise RuntimeError(f"抓取失败: {crawl_result.get('error')}")
        
        markdown_content = crawl_result["markdown"]
        
        # 执行处理（processor内部会重新抓取，但我们需要正文用于归档）
        result = alchemist.process_url(url)
        
        # 归档
        archive_path = archiver.archive(url, markdown_content, result)
        result["archive_path"] = archive_path
        
        # 输出结果
        if output_format == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            _print_pretty_result(result)
        
        return result
        
    except Exception as e:
        logger.error(f"处理失败: {e}")
        return {"error": str(e)}


def _print_pretty_result(result: Dict[str, Any]) -> None:
    """格式化打印处理结果"""
    print("\n" + "=" * 60)
    print("📄 知识炼金术处理结果")
    print("=" * 60)
    
    # 元数据
    metadata = result.get("metadata", {})
    if metadata:
        print(f"\n📁 标题: {metadata.get('title', 'N/A')}")
        print(f"🔗 URL: {result.get('url', 'N/A')}")
        print(f"✍️ 作者: {metadata.get('author', 'N/A')}")
        print(f"🌐 来源: {metadata.get('source', 'N/A')}")
        print(f"📅 发布时间: {metadata.get('publish_date', 'N/A')}")
    
    # 分类结果
    classification = result.get("classification", {})
    if classification:
        print(f"\n🏷️  三维分类:")
        print(f"  ⏰ 时间维度: {classification.get('time_dimension', 'N/A')}")
        print(f"  📚 内容维度: {classification.get('content_dimension', 'N/A')}")
        print(f"  🎬 场景维度: {classification.get('scene_dimension', 'N/A')}")
    
    # 评分结果
    scoring = result.get("scoring", {})
    scoring_data = scoring.get("scoring", scoring)
    if scoring_data:
        print(f"\n⭐ 评分结果:")
        print(f"  💡 重要性: {scoring_data.get('importance', 'N/A')}/10 - {scoring_data.get('importance_reason', '')}")
        print(f"  💎 稀缺性: {scoring_data.get('scarcity', 'N/A')}/10 - {scoring_data.get('scarcity_reason', '')}")
        print(f"  🔧 实用性: {scoring_data.get('practicality', 'N/A')}/10 - {scoring_data.get('practicality_reason', '')}")
    
    # 最终分
    print(f"\n🏆 最终评分:")
    print(f"  📊 分数: {result.get('final_score', 0)}/100")
    print(f"  ⭐ 星级: {'⭐' * result.get('star_level', 0)}")
    
    # 核心提炼
    extraction = result.get("extraction", {})
    extraction_data = extraction.get("extraction", extraction)
    if extraction_data:
        print(f"\n💡 核心提炼:")
        core_points = extraction_data.get("core_points", [])
        for i, point in enumerate(core_points, 1):
            print(f"  {i}. {point}")
        print(f"\n  🎥 视频适用场景: {extraction_data.get('video_usage', 'N/A')}")
    
    # 归档路径
    if result.get("archive_path"):
        print(f"\n📦 归档路径: {result['archive_path']}")
    
    print("\n" + "=" * 60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="知识炼金术 Agent V1.0 - 将杂乱信息转化为高价值资产",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 处理单个URL
  python main.py process --url https://example.com/article
  
  # 以JSON格式输出
  python main.py process --url https://example.com/article --format json
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # process 命令
    process_parser = subparsers.add_parser("process", help="处理URL并归档")
    process_parser.add_argument("--url", "-u", required=True, help="网页URL")
    process_parser.add_argument("--format", choices=["pretty", "json"], default="pretty", 
                                help="输出格式（默认：pretty）")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == "process":
        result = process_url(args.url, args.format)
        if "error" in result:
            sys.exit(1)


if __name__ == "__main__":
    main()
