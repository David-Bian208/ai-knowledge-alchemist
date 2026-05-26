"""
LLM 调用封装 - 支持多模型调用
按任务复杂度选择模型：
- 便宜模型（deepseek-chat）：预筛、分类、打标
- 好模型（deepseek-reasoner）：评分、核心提炼、复杂理解
"""
import os
import json
import re
from typing import Optional
from openai import OpenAI


def extract_json(text: str) -> dict:
    """从 LLM 返回中提取 JSON，处理前后废话/markdown包裹等情况"""
    # 先去掉```json和```包裹
    text = re.sub(r'^```json\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'\s*```$', '', text, flags=re.MULTILINE)
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    raise ValueError(f"No valid JSON found in: {text[:300]}")


class LLMClient:
    """LLM 客户端封装，支持多模型切换"""

    # 模型映射 - 可在config.yaml中覆盖
    MODEL_MAP = {
        "cheap": "deepseek-chat",      # 便宜模型，用于分类/预筛
        "pro": "deepseek-reasoner"     # 好模型，用于评分/提炼
    }

    def __init__(self, api_key: str = None, base_url: str = "https://api.deepseek.com", 
                 model_map: dict = None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY not set in environment or config")
        
        self.base_url = base_url
        self.model_map = model_map or self.MODEL_MAP
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=60
        )
    
    def chat(self, system_prompt: str, user_prompt: str, model: str = "cheap") -> str:
        """
        简单对话
        Args:
            system_prompt: 系统提示词
            user_prompt: 用户输入
            model: 模型类型，cheap 或 pro
        Returns:
            LLM 返回的文本
        """
        model_name = self.model_map.get(model, self.model_map["cheap"])
        
        response = self.client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1
        )
        return response.choices[0].message.content
    
    def chat_json(self, system_prompt: str, user_prompt: str, model: str = "cheap", 
                  retries: int = 2) -> dict:
        """
        对话 + JSON 提取 + 自动重试
        Args:
            system_prompt: 系统提示词
            user_prompt: 用户输入
            model: 模型类型，cheap 或 pro
            retries: 重试次数
        Returns:
            解析后的 JSON 字典
        """
        for i in range(retries + 1):
            try:
                text = self.chat(system_prompt, user_prompt, model)
                return extract_json(text)
            except (ValueError, json.JSONDecodeError) as e:
                if i == retries:
                    raise RuntimeError(f"JSON parse failed after {retries + 1} attempts: {e}")
        return {}
