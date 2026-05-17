"""
爬虫代理配置模块
支持HTTP代理解决海外信源访问问题
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ProxyConfig:
    """HTTP代理配置"""
    
    def __init__(self, proxy_url: str = None):
        self.proxy_url = proxy_url or os.getenv("HTTP_PROXY", "")
        self.proxies = {}
        
        if self.proxy_url:
            self.proxies = {
                "http": self.proxy_url,
                "https": self.proxy_url
            }
            logger.info(f"HTTP代理已配置: {self.proxy_url}")
        else:
            logger.info("未配置HTTP代理")
    
    def get_proxies(self) -> dict:
        """获取代理配置"""
        return self.proxies
    
    def is_enabled(self) -> bool:
        """代理是否启用"""
        return bool(self.proxy_url)
