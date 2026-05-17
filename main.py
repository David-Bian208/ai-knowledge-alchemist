#!/usr/bin/env python3
"""
知识炼金术 Agent V1.1 命令行入口
支持：单URL处理、批量URL处理、RSS订阅抓取、日报生成
"""
import os
import sys
import json
import argparse
import logging
from datetime import datetime
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.processor import KnowledgeAlchemist
from src.archiver import Archiver
from src.storage import MaterialStorage
from src.dedup import DeduplicationService
from src.rss_fetcher import RSSFetcher
from src.report import DailyReportGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("main")


def process_url(url: str, output_format: str = "pretty") -> Dict[str, Any]:
    """处理单个URL"""
    logger.info(f"开始处理URL: {url}")
    
    try:
        alchemist = KnowledgeAlchemist()
        archiver = Archiver()
        
        # 检查重复
        storage = MaterialStorage()
        dedup = DeduplicationService()
        dedup.load_existing_urls(storage)
        
        if dedup.is_duplicate(url):
            logger.warning(f"URL已处理过，跳过: {url}")
            return {"skipped": True, "url": url, "reason": "duplicate"}
        
        # 抓取 + 处理
        crawl_result = alchemist.crawler.fetch(url)
        if not crawl_result.get("success"):
            raise RuntimeError(f"抓取失败: {crawl_result.get('error')}")
        
        result = alchemist.process_crawl_result(url, crawl_result)
        
        # 归档
        archive_path = archiver.archive(url, crawl_result["markdown"], result)
        result["archive_path"] = archive_path
        dedup.add_url(url)
        
        if output_format == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            _print_pretty_result(result)
        
        return result
        
    except Exception as e:
        logger.error(f"处理失败: {e}")
        return {"error": str(e)}


def process_batch(file_path: str) -> Dict[str, Any]:
    """批量处理URL列表文件（每行一个URL）"""
    logger.info(f"开始批量处理: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        logger.info(f"共 {len(urls)} 个URL")
        
        results = {"total": len(urls), "success": 0, "fail": 0, "skipped": 0, "details": []}
        
        alchemist = KnowledgeAlchemist()
        archiver = Archiver()
        storage = MaterialStorage()
        dedup = DeduplicationService()
        dedup.load_existing_urls(storage)
        
        for i, url in enumerate(urls, 1):
            logger.info(f"\n[{i}/{len(urls)}] 处理: {url}")
            
            if dedup.is_duplicate(url):
                logger.info(f"跳过重复: {url}")
                results["skipped"] += 1
                results["details"].append({"url": url, "status": "skipped"})
                continue
            
            try:
                crawl_result = alchemist.crawler.fetch(url)
                if not crawl_result.get("success"):
                    logger.warning(f"抓取失败: {url}")
                    results["fail"] += 1
                    results["details"].append({"url": url, "status": "failed", "error": crawl_result.get("error")})
                    continue
                
                result = alchemist.process_crawl_result(url, crawl_result)
                archive_path = archiver.archive(url, crawl_result["markdown"], result)
                dedup.add_url(url)
                
                results["success"] += 1
                results["details"].append({
                    "url": url, 
                    "status": "success", 
                    "score": result.get("final_score", 0),
                    "stars": result.get("star_level", 0),
                    "archive": archive_path
                })
                
            except Exception as e:
                logger.error(f"处理异常: {url}, {e}")
                results["fail"] += 1
                results["details"].append({"url": url, "status": "failed", "error": str(e)})
        
        # 输出统计
        logger.info(f"\n{'='*50}")
        logger.info(f"批量处理完成:")
        logger.info(f"  总计: {results['total']} 个")
        logger.info(f"  成功: {results['success']} 个")
        logger.info(f"  失败: {results['fail']} 个")
        logger.info(f"  跳过: {results['skipped']} 个")
        
        return results
        
    except Exception as e:
        logger.error(f"批量处理失败: {e}")
        return {"error": str(e)}


def generate_report(date_str: str = None) -> str:
    """生成日报"""
    if date_str:
        date = datetime.strptime(date_str, "%Y-%m-%d")
    else:
        date = None
    
    generator = DailyReportGenerator()
    report = generator.generate_report(date)
    filepath = generator.save_report(report, date)
    
    logger.info(f"日报已生成: {filepath}")
    print("\n" + report)
    
    return filepath


def _print_pretty_result(result: Dict[str, Any]) -> None:
    """格式化打印处理结果"""
    print("\n" + "=" * 60)
    print("📄 知识炼金术处理结果")
    print("=" * 60)
    
    metadata = result.get("metadata", {})
    if metadata:
        print(f"\n📁 标题: {metadata.get('title', 'N/A')}")
        print(f"🔗 URL: {result.get('url', 'N/A')}")
        print(f"✍️ 作者: {metadata.get('author', 'N/A')}")
        print(f"🌐 来源: {metadata.get('source', 'N/A')}")
        print(f"📅 发布时间: {metadata.get('publish_date', 'N/A')}")
    
    classification = result.get("classification", {})
    if classification:
        print(f"\n🏷️  三维分类:")
        print(f"  ⏰ 时间维度: {classification.get('time_dimension', 'N/A')}")
        print(f"  📚 内容维度: {classification.get('content_dimension', 'N/A')}")
        print(f"  🎬 场景维度: {classification.get('scene_dimension', 'N/A')}")
    
    scoring = result.get("scoring", {})
    scoring_data = scoring.get("scoring", scoring)
    if scoring_data:
        print(f"\n⭐ 评分结果:")
        print(f"  💡 重要性: {scoring_data.get('importance', 'N/A')}/10 - {scoring_data.get('importance_reason', '')}")
        print(f"  💎 稀缺性: {scoring_data.get('scarcity', 'N/A')}/10 - {scoring_data.get('scarcity_reason', '')}")
        print(f"  🔧 实用性: {scoring_data.get('practicality', 'N/A')}/10 - {scoring_data.get('practicality_reason', '')}")
    
    print(f"\n🏆 最终评分:")
    print(f"  📊 分数: {result.get('final_score', 0)}/100")
    print(f"  ⭐ 星级: {'⭐' * result.get('star_level', 0)}")
    
    extraction = result.get("extraction", {})
    extraction_data = extraction.get("extraction", extraction)
    if extraction_data:
        print(f"\n💡 核心提炼:")
        core_points = extraction_data.get("core_points", [])
        for i, point in enumerate(core_points, 1):
            print(f"  {i}. {point}")
        print(f"\n  🎥 视频适用场景: {extraction_data.get('video_usage', 'N/A')}")
    
    if result.get("archive_path"):
        print(f"\n📦 归档路径: {result['archive_path']}")
    
    print("\n" + "=" * 60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="知识炼金术 Agent V1.1 - 全行业通用素材流水线引擎",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 处理单个URL
  python main.py process --url https://example.com/article
  
  # 批量处理URL列表
  python main.py batch --file urls.txt
  
  # 生成日报
  python main.py report --date 2025-05-16
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # process 命令
    process_parser = subparsers.add_parser("process", help="处理单个URL并归档")
    process_parser.add_argument("--url", "-u", required=True, help="网页URL")
    process_parser.add_argument("--format", choices=["pretty", "json"], default="pretty", help="输出格式")
    
    # batch 命令
    batch_parser = subparsers.add_parser("batch", help="批量处理URL列表")
    batch_parser.add_argument("--file", "-f", required=True, help="URL列表文件（每行一个URL）")
    
    # report 命令
    report_parser = subparsers.add_parser("report", help="生成日报")
    report_parser.add_argument("--date", "-d", help="日期（YYYY-MM-DD），默认昨天")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == "process":
        result = process_url(args.url, args.format)
        if "error" in result:
            sys.exit(1)
    
    elif args.command == "batch":
        results = process_batch(args.file)
        if "error" in results:
            sys.exit(1)
    
    elif args.command == "report":
        generate_report(args.date)


if __name__ == "__main__":
    main()
