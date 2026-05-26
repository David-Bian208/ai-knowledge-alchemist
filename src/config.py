"""
配置加载模块，统一管理所有配置项
"""
import os
import yaml
from typing import Dict, Any


class Config:
    _instance = None
    _config: Dict[str, Any] = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self) -> None:
        """加载yaml配置文件"""
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "config.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            self._config = yaml.safe_load(f)
        
        # 支持环境变量覆盖API Key
        if os.getenv("DEEPSEEK_API_KEY"):
            # 确保llm配置存在
            if "llm" not in self._config:
                self._config["llm"] = {}
            self._config["llm"]["api_key"] = os.getenv("DEEPSEEK_API_KEY")

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项，支持点号分隔，比如get("llm.model")"""
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value


# 全局配置实例
config = Config()
