import yaml
import uuid
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

@dataclass
class Source:
    id: str
    name: str
    url: str
    tier: str  # T1/T2/T3
    type: str  # web/rss/wechat/weibo/xiaohongshu
    enabled: bool = True
    fetch_interval: int = 30  # 分钟
    description: str = ""  # 信源描述
    tags: List[str] = None  # 标签列表
    direction: str = "ai"  # 领域方向：ai/tech/industry 等

    def __post_init__(self):
        if self.tags is None:
            self.tags = []

class SourceManager:
    def __init__(self, config_path: str = "config/sources.yaml"):
        self.config_path = config_path
        self.sources: List[Source] = []
        self._load_config()
    
    def _load_config(self):
        """加载信源配置"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                if data and 'sources' in data:
                    self.sources = [Source(**s) for s in data['sources']]
        except FileNotFoundError:
            # 配置文件不存在，初始化空
            self.sources = []
            self._save_config()
    
    def _save_config(self):
        """保存信源配置到文件"""
        data = {
            'sources': [asdict(s) for s in self.sources]
        }
        # 确保目录存在
        import os
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
    
    def add_source(self, name: str, url: str, tier: str, type: str, 
                   enabled: bool = True, fetch_interval: int = 30,
                   description: str = "", tags: List[str] = None) -> Source:
        """添加新信源"""
        source = Source(
            id=str(uuid.uuid4()),
            name=name,
            url=url,
            tier=tier,
            type=type,
            enabled=enabled,
            fetch_interval=fetch_interval,
            description=description,
            tags=tags or []
        )
        self.sources.append(source)
        self._save_config()
        return source
    
    def delete_source(self, source_id: str) -> bool:
        """删除信源"""
        for i, s in enumerate(self.sources):
            if s.id == source_id:
                del self.sources[i]
                self._save_config()
                return True
        return False
    
    def update_source(self, source_id: str, **kwargs) -> Optional[Source]:
        """更新信源信息"""
        for s in self.sources:
            if s.id == source_id:
                for k, v in kwargs.items():
                    if hasattr(s, k):
                        setattr(s, k, v)
                self._save_config()
                return s
        return None
    
    def get_source_by_id(self, source_id: str) -> Optional[Source]:
        """根据ID获取信源"""
        for s in self.sources:
            if s.id == source_id:
                return s
        return None
    
    def get_sources_by_tier(self, tier: str) -> List[Source]:
        """按等级筛选信源"""
        return [s for s in self.sources if s.tier == tier and s.enabled]
    
    def get_sources_by_type(self, type: str) -> List[Source]:
        """按类型筛选信源"""
        return [s for s in self.sources if s.type == type and s.enabled]
    
    def get_all_enabled_sources(self) -> List[Source]:
        """获取所有启用的信源"""
        return [s for s in self.sources if s.enabled]
    
    def import_sources(self, sources_data: List[Dict]):
        """批量导入信源"""
        for s in sources_data:
            self.add_source(**s)
    
    def get_all_sources(self) -> List[Source]:
        """获取所有信源（包含未启用的）"""
        return self.sources
    
    def delete_unhealthy_sources(self, unhealthy_ids: List[str]) -> int:
        """
        批量删除失效信源
        
        Args:
            unhealthy_ids: 失效信源 ID 列表
        
        Returns:
            删除的信源数量
        """
        deleted = 0
        for source_id in unhealthy_ids:
            if self.delete_source(source_id):
                deleted += 1
        return deleted
    
    def toggle_source(self, source_id: str, enabled: bool) -> bool:
        """切换信源启用/禁用状态"""
        for source in self.sources:
            if source.id == source_id:
                source.enabled = enabled
                self._save_config()
                return True
        return False
    
    def batch_enable_all(self) -> int:
        """批量启用所有禁用的信源"""
        count = 0
        for source in self.sources:
            if not source.enabled:
                source.enabled = True
                count += 1
        if count > 0:
            self._save_config()
        return count
