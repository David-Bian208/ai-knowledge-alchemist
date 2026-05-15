"""
归档模块
将处理后的素材自动保存到本地目录和SQLite数据库
"""
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from src.config import config
from src.storage import MaterialStorage

logger = logging.getLogger(__name__)


class Archiver:
    """素材归档处理器"""
    
    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or config.get("storage.output_dir", "data/output")
        self.storage = MaterialStorage()
    
    def archive(self, url: str, markdown: str, result: Dict[str, Any]) -> str:
        """
        归档素材
        Args:
            url: 原始URL
            markdown: 干净的Markdown正文
            result: 处理结果（包含分类、评分、提炼等）
        Returns:
            归档路径
        """
        classification = result.get("classification", {})
        content_dimension = classification.get("content_dimension", "未分类")
        time_dimension = classification.get("time_dimension", "近期趋势")
        
        # 构建目录结构：内容维度/时间维度/
        archive_dir = os.path.join(self.output_dir, content_dimension, time_dimension)
        os.makedirs(archive_dir, exist_ok=True)
        
        # 保存Markdown文件
        title = result.get("metadata", {}).get("title", "untitled")
        safe_title = self._safe_filename(title)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        md_filename = f"{timestamp}_{safe_title}.md"
        md_path = os.path.join(archive_dir, md_filename)
        
        # 写入Markdown文件，附带处理结果作为FrontMatter
        with open(md_path, 'w', encoding='utf-8') as f:
            # 写入FrontMatter
            f.write("---\n")
            f.write(f"title: {title}\n")
            f.write(f"url: {url}\n")
            f.write(f"date: {datetime.now().strftime('%Y-%m-%d')}\n")
            f.write(f"content_dimension: {content_dimension}\n")
            f.write(f"time_dimension: {time_dimension}\n")
            f.write(f"scene_dimension: {classification.get('scene_dimension', '')}\n")
            f.write(f"final_score: {result.get('final_score', 0)}\n")
            f.write(f"star_level: {result.get('star_level', 0)}\n")
            
            # 核心观点
            extraction = result.get("extraction", {})
            core_points = extraction.get("core_points", [])
            if core_points:
                f.write("core_points:\n")
                for point in core_points:
                    f.write(f"  - {point}\n")
            
            # 视频适用场景
            video_usage = extraction.get("video_usage", "")
            if video_usage:
                f.write(f"video_usage: {video_usage}\n")
            
            f.write("---\n\n")
            
            # 写入正文
            f.write(markdown)
        
        # 保存到SQLite
        self.storage.save_material(url, title, markdown, result)
        
        archive_path = os.path.relpath(md_path, self.output_dir)
        logger.info(f"归档完成: {archive_path}")
        
        return archive_path
    
    def _safe_filename(self, filename: str) -> str:
        """安全的文件名，去除特殊字符"""
        # 去除Windows/Linux不支持的字符
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # 限制长度
        if len(filename) > 100:
            filename = filename[:100]
        
        return filename
