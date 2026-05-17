"""
定时任务调度模块
支持每天固定时间自动跑RSS/信源抓取
"""
import os
import json
import time
import logging
import schedule
from datetime import datetime
from typing import List, Dict, Any, Callable

from src.rss_fetcher import RSSFetcher
from src.dedup import DeduplicationService
from src.storage import MaterialStorage

logger = logging.getLogger(__name__)


class TaskScheduler:
    """定时任务调度器"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or "config/schedule_config.json"
        self.config = self._load_config()
        self.fetcher = RSSFetcher()
        self.storage = MaterialStorage()
        self.dedup = DeduplicationService()
        self.dedup.load_existing_urls(self.storage)
        
        # 任务回调函数
        self.process_callback = None
    
    def _load_config(self) -> Dict[str, Any]:
        """加载定时任务配置"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # 默认配置
        return {
            "enabled": True,
            "schedule_times": ["10:00", "16:00", "22:00"],
            "sources": [],
            "proxy": None
        }
    
    def save_config(self):
        """保存配置到本地文件"""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
    def add_schedule(self, time_str: str):
        """添加定时时间（格式：HH:MM）"""
        if time_str not in self.config["schedule_times"]:
            self.config["schedule_times"].append(time_str)
            self.save_config()
            logger.info(f"添加定时时间: {time_str}")
    
    def remove_schedule(self, time_str: str):
        """移除定时时间"""
        if time_str in self.config["schedule_times"]:
            self.config["schedule_times"].remove(time_str)
            self.save_config()
            logger.info(f"移除定时时间: {time_str}")
    
    def add_source(self, name: str, url: str, source_type: str = "rss"):
        """添加信源"""
        source = {"name": name, "url": url, "type": source_type}
        self.config["sources"].append(source)
        self.save_config()
        logger.info(f"添加信源: {name}")
    
    def remove_source(self, url: str):
        """移除信源"""
        self.config["sources"] = [s for s in self.config["sources"] if s["url"] != url]
        self.save_config()
    
    def set_process_callback(self, callback: Callable):
        """
        设置处理回调函数
        当抓取到新内容时，调用此函数进行处理
        """
        self.process_callback = callback
    
    def run_fetch_task(self):
        """执行一次抓取任务"""
        logger.info("=" * 50)
        logger.info(f"开始定时抓取任务: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 50)
        
        results = {
            "time": datetime.now().isoformat(),
            "total": 0,
            "new": 0,
            "failed": 0,
            "details": []
        }
        
        for source in self.config.get("sources", []):
            try:
                logger.info(f"抓取信源: {source['name']} ({source['url']})")
                
                if source.get("type") == "rss":
                    entries = self.fetcher.fetch_feed(source["url"])
                    results["total"] += len(entries)
                    
                    for entry in entries:
                        url = entry.get("link", "")
                        if not url:
                            continue
                        
                        if self.dedup.is_duplicate(url):
                            continue
                        
                        results["new"] += 1
                        
                        # 调用处理回调
                        if self.process_callback:
                            try:
                                self.process_callback(entry)
                                self.dedup.add_url(url)
                            except Exception as e:
                                logger.error(f"处理失败: {url}, 错误: {e}")
                                results["failed"] += 1
                                results["details"].append({
                                    "url": url,
                                    "status": "failed",
                                    "error": str(e)
                                })
                
            except Exception as e:
                logger.error(f"信源抓取失败: {source['name']}, 错误: {e}")
                results["failed"] += 1
                results["details"].append({
                    "source": source["name"],
                    "status": "failed",
                    "error": str(e)
                })
        
        logger.info(f"定时抓取任务完成: 总计{results['total']}条, 新增{results['new']}条, 失败{results['failed']}条")
        
        return results
    
    def start(self):
        """启动定时任务调度"""
        if not self.config.get("enabled", True):
            logger.info("定时任务未启用")
            return
        
        # 注册定时任务
        for time_str in self.config.get("schedule_times", []):
            schedule.every().day.at(time_str).do(self.run_fetch_task)
            logger.info(f"注册定时任务: {time_str}")
        
        logger.info("定时任务调度器已启动，等待执行...")
        
        # 持续运行
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
