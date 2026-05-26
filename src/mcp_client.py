"""
MCP客户端模块
支持读取Obsidian知识库+回写标签到FrontMatter
通过MCP协议与Obsidian交互
"""
import os
import json
import re
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ObsidianMCPClient:
    """Obsidian MCP客户端"""
    
    def __init__(self, vault_path: str = None):
        self.vault_path = vault_path or os.getenv("OBSIDIAN_VAULT_PATH", "")
        if not self.vault_path:
            logger.warning("OBSIDIAN_VAULT_PATH 未配置，MCP功能不可用")
            self.enabled = False
        else:
            self.enabled = True
            logger.info(f"Obsidian MCP客户端初始化完成: {self.vault_path}")
    
    def read_note(self, note_path: str) -> Optional[str]:
        """读取Obsidian笔记内容"""
        if not self.enabled:
            return None
        
        full_path = os.path.join(self.vault_path, note_path)
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"读取笔记失败: {note_path}, 错误: {e}")
            return None
    
    def write_note(self, note_path: str, content: str, update_frontmatter: Dict = None) -> bool:
        """
        写入笔记，支持更新FrontMatter
        Args:
            note_path: 笔记路径（相对于vault）
            content: 笔记正文内容
            update_frontmatter: 要更新的FrontMatter字段
        Returns:
            是否成功
        """
        if not self.enabled:
            return False
        
        full_path = os.path.join(self.vault_path, note_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        try:
            # 如果文件已存在，保留原有FrontMatter
            existing_content = ""
            existing_frontmatter = {}
            
            if os.path.exists(full_path):
                existing_content = self.read_note(note_path) or ""
                existing_frontmatter = self._parse_frontmatter(existing_content)
                # 移除原有FrontMatter
                content_only = re.sub(r'^---\n.*?\n---\n?', '', existing_content, flags=re.DOTALL)
            else:
                content_only = content
            
            # 合并FrontMatter
            merged_frontmatter = {**existing_frontmatter, **(update_frontmatter or {})}
            
            # 写入新内容
            with open(full_path, 'w', encoding='utf-8') as f:
                if merged_frontmatter:
                    f.write("---\n")
                    for key, value in merged_frontmatter.items():
                        if isinstance(value, list):
                            f.write(f"{key}:\n")
                            for item in value:
                                f.write(f"  - {item}\n")
                        else:
                            f.write(f"{key}: {value}\n")
                    f.write("---\n\n")
                
                f.write(content_only)
            
            logger.info(f"笔记写入成功: {note_path}")
            return True
            
        except Exception as e:
            logger.error(f"写入笔记失败: {note_path}, 错误: {e}")
            return False
    
    def search_notes(self, query: str = None, tag: str = None) -> List[Dict[str, Any]]:
        """
        搜索Obsidian笔记
        Args:
            query: 搜索关键词
            tag: 按标签搜索
        Returns:
            匹配的笔记列表
        """
        if not self.enabled:
            return []
        
        results = []
        for root, dirs, files in os.walk(self.vault_path):
            for file in files:
                if file.endswith('.md'):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.vault_path)
                    
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # 关键词搜索
                        if query and query.lower() in content.lower():
                            results.append({"path": rel_path, "title": file[:-3]})
                        
                        # 标签搜索
                        if tag:
                            frontmatter = self._parse_frontmatter(content)
                            tags = frontmatter.get("tags", [])
                            if isinstance(tags, str):
                                tags = [tags]
                            if tag in tags:
                                results.append({"path": rel_path, "title": file[:-3]})
                                
                    except Exception as e:
                        logger.warning(f"搜索笔记失败: {rel_path}, 错误: {e}")
        
        return results
    
    def update_tags(self, note_path: str, tags: List[str]) -> bool:
        """更新笔记标签"""
        return self.write_note(note_path, "", update_frontmatter={"tags": tags})
    
    def _parse_frontmatter(self, content: str) -> Dict[str, Any]:
        """解析FrontMatter"""
        match = re.match(r'^---\n(.*?)\n---\n?', content, re.DOTALL)
        if not match:
            return {}
        
        frontmatter = {}
        for line in match.group(1).split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                value = value.strip()
                frontmatter[key.strip()] = value
        
        return frontmatter
    
    def archive_material(self, material: Dict[str, Any]) -> bool:
        """
        归档素材到Obsidian
        Args:
            material: 处理后的素材数据
        Returns:
            是否成功
        """
        if not self.enabled:
            return False
        
        # 构建笔记路径：AI素材库/内容维度/时间维度/标题.md
        classification = material.get("classification", {})
        content_dimension = classification.get("content_dimension", "未分类")
        time_dimension = classification.get("time_dimension", "近期趋势")
        
        title = material.get("metadata", {}).get("title", "untitled")
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)[:100]
        
        note_path = f"AI素材库/{content_dimension}/{time_dimension}/{safe_title}.md"
        
        # 构建FrontMatter
        frontmatter = {
            "url": material.get("url", ""),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "content_dimension": content_dimension,
            "time_dimension": time_dimension,
            "scene_dimension": classification.get("scene_dimension", ""),
            "final_score": material.get("final_score", 0),
            "star_level": material.get("star_level", 0),
            "tags": [
                f"AI素材",
                f"{content_dimension}",
                f"{time_dimension}",
                f"{classification.get('scene_dimension', '')}"
            ]
        }
        
        # 核心观点
        extraction = material.get("extraction", {})
        core_points = extraction.get("core_points", [])
        video_usage = extraction.get("video_usage", "")
        
        # 构建笔记内容
        content = f"# {title}\n\n"
        if core_points:
            content += "## 核心观点\n\n"
            for i, point in enumerate(core_points, 1):
                content += f"{i}. {point}\n"
            content += "\n"
        
        if video_usage:
            content += f"## 视频适用场景\n\n{video_usage}\n\n"
        
        content += "---\n\n"
        content += material.get("content", "")
        
        return self.write_note(note_path, content, update_frontmatter=frontmatter)
