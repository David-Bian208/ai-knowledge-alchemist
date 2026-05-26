"""
自动日报生成模块
不需要LLM，直接把已处理的内容按分类/分数排序生成日报
"""
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any

from src.storage import MaterialStorage


class DailyReportGenerator:
    """日报生成器"""
    
    def __init__(self, storage: MaterialStorage = None):
        self.storage = storage or MaterialStorage()
    
    def generate_report(self, date: datetime = None) -> str:
        """
        生成指定日期的日报
        Args:
            date: 日期，默认昨天
        Returns:
            Markdown格式的日报
        """
        if date is None:
            date = datetime.now() - timedelta(days=1)
        
        # 查询昨天的素材
        materials = self.storage.query_materials(limit=200)
        
        # 按内容维度分组
        categories = {}
        for m in materials:
            cat = m.get("content_dimension", "未分类")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(m)
        
        # 生成报告
        report = f"# 📰 AI行业日报 - {date.strftime('%Y年%m月%d日')}\n\n"
        
        for cat, items in categories.items():
            # 按分数降序
            items.sort(key=lambda x: x.get("final_score", 0), reverse=True)
            
            report += f"## {cat}\n\n"
            for i, item in enumerate(items[:5], 1):  # 每个分类最多5条
                title = item.get("title", "无标题")
                score = item.get("final_score", 0)
                stars = "⭐" * item.get("star_level", 0)
                url = item.get("url", "")
                
                # 核心观点
                core_points = item.get("core_points", [])
                first_point = core_points[0] if core_points else ""
                
                report += f"{i}. **{title}** ({score}分 {stars})\n"
                if first_point:
                    report += f"   > {first_point}\n"
                if url:
                    report += f"   🔗 {url}\n\n"
        
        report += f"\n---\n*日报生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
        
        return report
    
    def save_report(self, report: str, date: datetime = None) -> str:
        """保存日报到文件"""
        if date is None:
            date = datetime.now() - timedelta(days=1)
        
        report_dir = "data/reports"
        os.makedirs(report_dir, exist_ok=True)
        
        filename = f"{date.strftime('%Y%m%d')}_daily_report.md"
        filepath = os.path.join(report_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)
        
        return filepath
