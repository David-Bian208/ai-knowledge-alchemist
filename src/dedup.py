"""
事件聚类去重模块
使用Embedding语义匹配，避免同一事件重复入库
"""
import os
import json
import logging
import numpy as np
from typing import List, Dict, Any, Optional
from openai import OpenAI
from src.config import config

logger = logging.getLogger(__name__)


class DeduplicationService:
    """重复检测服务"""
    
    def __init__(self):
        # V1.0先用URL精确匹配
        # V1.1新增Embedding语义相似度匹配
        self.seen_urls = set()
        self.content_vectors = []  # 存储(内容向量, 内容ID, 标题, 分数)
        self.embedding_client = None
        self._init_embedding_client()
        self.similarity_threshold = 0.75  # 相似度阈值，高于此值判定为重复
    
    def _init_embedding_client(self):
        """初始化Embedding客户端"""
        try:
            api_key = config.get("llm.api_key") or os.getenv("DEEPSEEK_API_KEY", "")
            base_url = config.get("llm.base_url", "https://api.deepseek.com")
            self.embedding_client = OpenAI(
                api_key=api_key,
                base_url=base_url
            )
            logger.info("Embedding客户端初始化成功")
        except Exception as e:
            logger.warning(f"Embedding客户端初始化失败: {e}，仅使用URL去重")
            self.embedding_client = None
    
    def load_existing_urls(self, storage) -> int:
        """
        从数据库加载已有URL
        Args:
            storage: MaterialStorage实例
        Returns:
            加载的URL数量
        """
        try:
            materials = storage.query_materials(limit=10000)
            self.seen_urls = {m["url"] for m in materials}
            logger.info(f"加载已有URL: {len(self.seen_urls)} 条")
            return len(self.seen_urls)
        except Exception as e:
            logger.warning(f"加载已有URL失败: {e}")
            return 0
    
    def is_duplicate(self, url: str) -> bool:
        """检查URL是否已存在"""
        return url in self.seen_urls
    
    def add_url(self, url: str):
        """标记URL为已处理"""
        self.seen_urls.add(url)
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """生成文本的Embedding向量"""
        if not self.embedding_client:
            return None
        
        try:
            # 只取前2000字符生成向量，兼顾效果和速度
            text = text[:2000].strip()
            if not text:
                return None
            
            response = self.embedding_client.embeddings.create(
                input=text,
                model="deepseek-text-embedding"
            )
            return response.data[0].embedding
        except Exception as e:
            logger.warning(f"生成Embedding失败: {e}")
            return None
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算两个向量的余弦相似度"""
        try:
            vec1 = np.array(vec1)
            vec2 = np.array(vec2)
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            return dot_product / (norm1 * norm2) if (norm1 * norm2) != 0 else 0.0
        except Exception as e:
            logger.warning(f"计算相似度失败: {e}")
            return 0.0
    
    def check_semantic_duplicate(self, title: str, content: str = "", score: float = 0) -> Dict[str, Any]:
        """
        检查是否存在语义重复内容
        返回: {"is_duplicate": bool, "duplicate_info": Optional[Dict]}
        duplicate_info包含: 重复内容的ID、标题、分数、相似度
        """
        if not self.embedding_client or len(self.content_vectors) == 0:
            return {"is_duplicate": False, "duplicate_info": None}
        
        # 生成当前内容的向量（标题+内容前1000字）
        text_for_embedding = f"标题: {title}\n内容: {content[:1000]}" if content else title
        current_vec = self.generate_embedding(text_for_embedding)
        if not current_vec:
            return {"is_duplicate": False, "duplicate_info": None}
        
        # 计算与所有已有向量的相似度
        max_similarity = 0.0
        duplicate_item = None
        
        for vec, item_id, existing_title, existing_score in self.content_vectors:
            similarity = self.cosine_similarity(current_vec, vec)
            if similarity > max_similarity:
                max_similarity = similarity
                duplicate_item = {
                    "id": item_id,
                    "title": existing_title,
                    "score": existing_score,
                    "similarity": similarity
                }
        
        # 判断是否超过阈值
        if max_similarity >= self.similarity_threshold:
            logger.info(f"检测到语义重复内容: 当前标题[{title}]，重复标题[{duplicate_item['title']}]，相似度{max_similarity:.2f}")
            return {"is_duplicate": True, "duplicate_info": duplicate_item}
        else:
            # 新内容，存入向量库
            self.content_vectors.append((current_vec, None, title, score))
            return {"is_duplicate": False, "duplicate_info": None}
    
    def load_existing_vectors(self, storage) -> int:
        """从数据库加载已有内容的向量"""
        if not self.embedding_client:
            return 0
        
        try:
            # 加载最近1000条已入库的内容
            materials = storage.query_materials(limit=1000)
            count = 0
            for mat in materials:
                title = mat.get("title", "")
                content = mat.get("content", "") or mat.get("full_content", "")
                score = mat.get("final_score", 0)
                item_id = mat.get("id")
                
                if not title:
                    continue
                
                # 生成向量并存储
                text_for_embedding = f"标题: {title}\n内容: {content[:1000]}" if content else title
                vec = self.generate_embedding(text_for_embedding)
                if vec:
                    self.content_vectors.append((vec, item_id, title, score))
                    count += 1
            
            logger.info(f"加载已有内容向量: {count} 条")
            return count
        except Exception as e:
            logger.warning(f"加载已有内容向量失败: {e}")
            return 0
