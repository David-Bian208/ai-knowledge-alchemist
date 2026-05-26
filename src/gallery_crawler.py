"""
gallery-dl 图片/社交媒体抓取器
支持微博、Twitter、Instagram、Pixiv等267个站点
自动下载图片、分类保存、返回结构化数据
"""
import os
import re
import json
import logging
import subprocess
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class GalleryDLCrawler:
    """gallery-dl 图片/社交媒体抓取器"""
    
    # 支持的站点域名列表（主要平台）
    SUPPORTED_DOMAINS = {
        'weibo.com': 'weibo',
        'twitter.com': 'twitter',
        'x.com': 'twitter',
        'instagram.com': 'instagram',
        'pixiv.net': 'pixiv',
        'flickr.com': 'flickr',
        'tumblr.com': 'tumblr',
        'deviantart.com': 'deviantart',
        'artstation.com': 'artstation',
        'pinterest.com': 'pinterest',
        'reddit.com': 'reddit',
        'danbooru.donmai.us': 'danbooru',
        'gelbooru.com': 'gelbooru',
        'nhentai.net': 'nhentai',
        'fanbox.cc': 'fanbox',
        'fanbox.fanbox.cc': 'fanbox',
        'bilibili.com': 'bilibili',
        'tiktok.com': 'tiktok',
    }
    
    # gallery-dl不支持但需要特殊处理的平台
    UNSUPPORTED_DOMAINS = {
        'xiaohongshu.com': 'xiaohongshu',
        'xhslink.com': 'xiaohongshu',
        'douyin.com': 'douyin',
        'iesdouyin.com': 'douyin',
        'zhihu.com': 'zhihu',
        'toutiao.com': 'toutiao',
        'sohu.com': 'sohu',
        '163.com': 'netease',
        'qq.com': 'tencent',
    }
    
    def __init__(self, save_dir: str = "./gallery_dl_output"):
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        
        # 检查gallery-dl是否可用
        self._check_availability()
    
    def _check_availability(self):
        """检查gallery-dl是否安装"""
        try:
            result = subprocess.run(
                ["gallery-dl", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            self.available = result.returncode == 0
            self.version = result.stdout.strip() if self.available else None
            logger.info(f"gallery-dl {'可用' if self.available else '不可用'} (版本: {self.version})")
        except Exception as e:
            self.available = False
            self.version = None
            logger.warning(f"gallery-dl检查失败: {e}")
    
    def is_supported(self, url: str) -> bool:
        """
        检查URL是否被gallery-dl支持
        Args:
            url: 目标URL
        Returns:
            是否支持
        """
        if not self.available:
            return False
        
        for domain in self.SUPPORTED_DOMAINS.keys():
            if domain in url.lower():
                return True
        
        return False
    
    def fetch(self, url: str, download: bool = False) -> Dict:
        """
        抓取社交媒体/图片内容
        Args:
            url: 目标URL
            download: 是否下载图片到本地（默认只获取元数据）
        Returns:
            {
                "success": bool,
                "metadata": 元数据（标题、作者、发布时间等）,
                "images": 图片URL列表,
                "content": 文本内容（如果有）,
                "downloaded_files": 本地下载的文件列表,
                "error": 错误信息（如果有）
            }
        """
        logger.info(f"gallery-dl抓取: {url}")
        
        if not self.available:
            return {"success": False, "error": "gallery-dl不可用"}
        
        if not self.is_supported(url):
            return {"success": False, "error": "该站点不被gallery-dl支持"}
        
        try:
            # 创建临时目录用于下载
            temp_dir = self.save_dir / datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_dir.mkdir(exist_ok=True)
            
            # 构建gallery-dl命令
            cmd = [
                "gallery-dl",
                "--dump-json",  # 输出JSON元数据
            ]
            
            if download:
                # 下载到指定目录
                output_template = str(temp_dir / "%T%/%U_%i.%e")
                cmd.extend([
                    "-d", str(temp_dir),
                    "--filename", "%U_%i.%e",
                ])
            
            cmd.append(url)
            
            # 执行gallery-dl
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120  # 2分钟超时
            )
            
            if result.returncode != 0:
                error_msg = result.stderr[:500]
                logger.warning(f"gallery-dl执行失败: {error_msg}")
                return {"success": False, "error": error_msg}
            
            # 解析输出（每行一个JSON对象）
            images = []
            metadata_list = []
            
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        data = json.loads(line)
                        metadata_list.append(data)
                        
                        # 提取图片URL
                        if 'url' in data:
                            images.append(data['url'])
                    except json.JSONDecodeError:
                        continue
            
            if not metadata_list:
                return {"success": False, "error": "未获取到任何数据"}
            
            # 提取主要元数据
            first_item = metadata_list[0]
            metadata = {
                "title": first_item.get("title", ""),
                "author": first_item.get("user", first_item.get("username", "")),
                "source": self._get_source_name(url),
                "url": url,
                "publish_date": first_item.get("date", ""),
                "description": first_item.get("description", ""),
            }
            
            # 获取下载的文件列表
            downloaded_files = []
            if download:
                downloaded_files = [
                    str(f) for f in temp_dir.rglob("*")
                    if f.is_file() and not f.name.endswith('.json')
                ]
            
            # 提取文本内容（如果有）
            content = first_item.get("content", "")
            
            logger.info(f"gallery-dl抓取成功: {len(images)} 张图片")
            
            return {
                "success": True,
                "metadata": metadata,
                "images": images,
                "content": content,
                "downloaded_files": downloaded_files,
                "image_count": len(images),
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"gallery-dl超时: {url}")
            return {"success": False, "error": "抓取超时"}
        except Exception as e:
            logger.error(f"gallery-dl抓取异常: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_source_name(self, url: str) -> str:
        """从URL获取站点名称"""
        for domain, name in self.SUPPORTED_DOMAINS.items():
            if domain in url.lower():
                return name
        return "unknown"
    
    def get_supported_sites(self) -> List[Dict]:
        """获取所有支持的站点列表"""
        if not self.available:
            return []
        
        try:
            result = subprocess.run(
                ["gallery-dl", "--list-modules"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                modules = result.stdout.strip().split('\n')
                return [{"name": m, "available": True} for m in modules]
        except:
            pass
        
        return []
