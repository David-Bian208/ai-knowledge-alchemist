"""
高优先级分层模块
≥4星素材额外做核心摘要+复用价值点
"""
import logging
from typing import Dict, Any, Optional
from src.llm_client import LLMClient

logger = logging.getLogger(__name__)


class PriorityEnhancer:
    """高优先级素材增强器"""
    
    def __init__(self, llm: LLMClient = None):
        self.llm = llm
    
    def should_enhance(self, material: Dict[str, Any]) -> bool:
        """判断是否需要增强（≥4星）"""
        return material.get("star_level", 0) >= 4
    
    def enhance(self, material: Dict[str, Any]) -> Dict[str, Any]:
        """
        增强高优先级素材
        - 生成核心摘要
        - 提取复用价值点
        - 给出视频制作建议
        """
        if not self.should_enhance(material):
            return material
        
        if not self.llm:
            logger.warning("LLM客户端未配置，无法增强素材")
            return material
        
        logger.info(f"开始增强高优先级素材: {material.get('metadata', {}).get('title', 'unknown')}")
        
        markdown_content = material.get("content", "")[:3000]
        
        try:
            result = self.llm.chat_json(
                "只输出JSON，不要任何额外解释。",
                f"""你是资深的自媒体编导，现在需要对一篇高价值素材做深度提炼。

素材信息：
- 标题: {material.get('metadata', {}).get('title', '')}
- 分类: {material.get('classification', {})}
- 评分: {material.get('final_score', 0)}分，{material.get('star_level', 0)}星

请完成以下任务：
1. 用不超过100字生成核心摘要，包含最关键的信息
2. 提取3-5个可以直接复用的价值点（比如金句、案例、数据、方法论等）
3. 给出具体的视频制作建议：开篇怎么引入、中间怎么展开、结尾怎么升华

输出必须是严格的JSON格式，格式如下：
{{
  "enhancement": {{
    "summary": "核心摘要（100字以内）",
    "reuse_points": [
      "复用价值点1",
      "复用价值点2",
      "复用价值点3"
    ],
    "video_suggestions": {{
      "opening": "开篇引入方式",
      "body": "中间展开方式",
      "closing": "结尾升华方式"
    }}
  }}
}}

素材内容：
{markdown_content}""",
                model="pro"
            )
            
            # 将增强结果合并到素材中
            material["enhancement"] = result.get("enhancement", {})
            logger.info("素材增强完成")
            
        except Exception as e:
            logger.error(f"素材增强失败: {e}")
        
        return material
