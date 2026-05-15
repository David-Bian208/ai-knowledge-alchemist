"""
知识炼金术核心处理流水线
实现6步确定性流程：抓取→分类→评分→提炼→计算→归档
"""
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from src.llm_client import LLMClient
from src.config import config
from src.utils import load_prompt
from src.crawler import WebCrawler

logger = logging.getLogger(__name__)


class KnowledgeAlchemist:
    """知识炼金术处理引擎"""

    def __init__(self):
        # LLM客户端
        model_map = {
            "cheap": config.get("llm.cheap_model", "deepseek-chat"),
            "pro": config.get("llm.pro_model", "deepseek-chat")
        }
        self.llm = LLMClient(
            api_key=os.getenv("DEEPSEEK_API_KEY", ""),
            base_url=config.get("llm.base_url", "https://api.deepseek.com"),
            model_map=model_map
        )
        
        # 爬虫
        self.crawler = WebCrawler()
        
        # 分类选项
        self.content_options = config.get("classification_options.content_dimension", [])
        self.scene_options = config.get("classification_options.scene_dimension", [])
        
        # 评分权重
        self.scoring_weights = config.get("scoring_weights", {
            "importance": 0.4, "scarcity": 0.3, "practicality": 0.3
        })
        
        # 时效性权重
        self.time_weights = config.get("time_weights", {
            "7天内": 1.5, "1个月内": 1.2, "3个月内": 1.0, "1年内": 0.9, "超过1年": 0.8
        })
        
        # 星级映射
        self.star_mapping = config.get("star_mapping", {90: 5, 80: 4, 70: 3, 60: 2, 0: 1})
        
        logger.info("知识炼金术处理引擎初始化完成")

    def process_url(self, url: str) -> Dict[str, Any]:
        """
        处理URL，跑完6步全流程
        Args:
            url: 网页URL
        Returns:
            完整的处理结果
        """
        result = {
            "url": url,
            "metadata": {},
            "classification": {},
            "scoring": {},
            "extraction": {},
            "final_score": 0,
            "star_level": 0,
            "archive_path": ""
        }
        
        # 步骤1：抓取网页
        logger.info("步骤1：开始抓取网页...")
        crawl_result = self.crawler.fetch(url)
        if not crawl_result.get("success"):
            raise RuntimeError(f"抓取失败: {crawl_result.get('error')}")
        
        result["metadata"] = crawl_result["metadata"].to_dict()
        markdown_content = crawl_result["markdown"]
        logger.info(f"抓取成功: {result['metadata'].get('title', 'unknown')}")
        
        # 步骤2：三维分类
        logger.info("步骤2：开始三维分类...")
        result["classification"] = self._do_classification(
            markdown_content, 
            publish_date=result["metadata"].get("publish_date")
        )
        logger.info(f"分类结果: {json.dumps(result['classification'], ensure_ascii=False)}")
        
        # 步骤3：LLM三维评分
        logger.info("步骤3：开始LLM评分...")
        result["scoring"] = self._do_scoring(markdown_content)
        logger.info(f"评分结果: {json.dumps(result['scoring'], ensure_ascii=False)}")
        
        # 步骤4：代码综合计算最终分
        logger.info("步骤4：计算最终分...")
        result["final_score"] = self._calculate_final_score(
            result["scoring"], 
            publish_date=result["metadata"].get("publish_date")
        )
        result["star_level"] = self._score_to_star(result["final_score"])
        logger.info(f"最终分: {result['final_score']}, 星级: {result['star_level']}")
        
        # 步骤5：核心提炼
        logger.info("步骤5：开始核心提炼...")
        result["extraction"] = self._do_extraction(markdown_content)
        logger.info(f"提炼结果: {json.dumps(result['extraction'], ensure_ascii=False)}")
        
        return result

    def _do_classification(self, content: str, publish_date: Optional[str] = None) -> Dict[str, Any]:
        """执行三维分类"""
        # 时间维度用代码判断，不需要LLM
        time_dimension = self._judge_time_dimension(publish_date)
        
        # 内容维度和场景维度调用LLM
        prompt_template = load_prompt("classification", {
            "content_dimension_options": "、".join(self.content_options),
            "scene_dimension_options": "、".join(self.scene_options),
            "content": content[:5000]
        })
        
        llm_result = self.llm.chat_json(
            "只输出JSON，不要任何额外解释。",
            prompt_template,
            model="cheap"
        )
        
        classification = llm_result.get("classification", {})
        classification["time_dimension"] = time_dimension
        
        return classification

    def _judge_time_dimension(self, publish_date: Optional[str]) -> str:
        """根据发布时间判断时间维度"""
        if not publish_date:
            return "近期趋势"
        
        try:
            pub_date = datetime.fromisoformat(publish_date.replace("Z", "+00:00"))
            now = datetime.now(pub_date.tzinfo) if pub_date.tzinfo else datetime.now()
            delta = now - pub_date
            
            if delta.days <= 1:
                return "即时热点"
            elif delta.days <= 30:
                return "近期趋势"
            else:
                return "经典常青"
        except:
            return "近期趋势"

    def _do_scoring(self, content: str) -> Dict[str, Any]:
        """执行LLM三维评分"""
        prompt_template = load_prompt("scoring", {
            "content": content[:5000]
        })
        
        return self.llm.chat_json(
            "只输出JSON，不要任何额外解释。",
            prompt_template,
            model="pro"
        )

    def _do_extraction(self, content: str) -> Dict[str, Any]:
        """执行核心提炼"""
        prompt_template = load_prompt("extraction", {
            "content": content[:5000]
        })
        
        return self.llm.chat_json(
            "只输出JSON，不要任何额外解释。",
            prompt_template,
            model="pro"
        )

    def _calculate_final_score(self, scoring: Dict[str, Any], publish_date: Optional[str] = None) -> float:
        """
        计算最终分（100分制）
        公式：(重要性×0.4 + 稀缺性×0.3 + 实用性×0.3) × 10 × 时效性权重
        """
        scoring_data = scoring.get("scoring", scoring)
        
        importance = scoring_data.get("importance", 5)
        scarcity = scoring_data.get("scarcity", 5)
        practicality = scoring_data.get("practicality", 5)
        
        # 基础分（0-10分制）
        base_score = (
            importance * self.scoring_weights["importance"] +
            scarcity * self.scoring_weights["scarcity"] +
            practicality * self.scoring_weights["practicality"]
        )
        
        # 时效性权重
        time_weight = self._get_time_weight(publish_date)
        
        # 最终分（0-100分制）
        final_score = base_score * 10 * time_weight
        
        return round(final_score, 1)

    def _get_time_weight(self, publish_date: Optional[str]) -> float:
        """根据发布时间获取时效性权重"""
        if not publish_date:
            return 1.2  # 默认1个月内
        
        try:
            pub_date = datetime.fromisoformat(publish_date.replace("Z", "+00:00"))
            now = datetime.now(pub_date.tzinfo) if pub_date.tzinfo else datetime.now()
            delta = now - pub_date
            
            if delta.days <= 7:
                return 1.5
            elif delta.days <= 30:
                return 1.2
            elif delta.days <= 90:
                return 1.0
            elif delta.days <= 365:
                return 0.9
            else:
                return 0.8
        except:
            return 1.2

    def _score_to_star(self, score: float) -> int:
        """最终分映射到星级"""
        thresholds = sorted(self.star_mapping.keys(), reverse=True)
        for threshold in thresholds:
            if score >= threshold:
                return self.star_mapping[threshold]
        return 1
