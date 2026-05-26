"""
通用工具函数
"""
import os
from typing import Dict
from src.config import config


def load_prompt(prompt_name: str, variables: Dict[str, str] = None) -> str:
    """加载提示词模板，替换变量
    Args:
        prompt_name: 提示词文件名，不带后缀，比如classification
        variables: 需要替换的变量字典，key是模板里的变量名，不带{{}}
    Returns:
        替换后的提示词
    """
    prompt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), config.get(f"prompts.{prompt_name}"))
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt = f.read()
    
    if variables:
        for k, v in variables.items():
            prompt = prompt.replace(f"{{{{ {k} }}}}", str(v))
            # 兼容不带空格的写法
            prompt = prompt.replace(f"{{{{{k}}}}}", str(v))
    
    return prompt
