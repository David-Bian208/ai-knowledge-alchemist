"""
通知模块
抓取失败/处理异常时通知用户
支持多种通知方式：日志、Webhook、文件等
"""
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import requests

logger = logging.getLogger(__name__)


class NotificationService:
    """通知服务"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or "config/notification_config.json"
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载通知配置"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return {
            "enabled": True,
            "channels": ["log", "file"],  # log/file/webhook
            "webhook_url": "",
            "notification_file": "data/notifications.json"
        }
    
    def send_notification(self, title: str, message: str, level: str = "info", data: Dict = None):
        """
        发送通知
        Args:
            title: 通知标题
            message: 通知内容
            level: 级别（info/warning/error）
            data: 附加数据
        """
        if not self.config.get("enabled", True):
            return
        
        notification = {
            "time": datetime.now().isoformat(),
            "title": title,
            "message": message,
            "level": level,
            "data": data or {}
        }
        
        channels = self.config.get("channels", ["log"])
        
        # 日志通知
        if "log" in channels:
            self._send_log(notification)
        
        # 文件通知
        if "file" in channels:
            self._send_file(notification)
        
        # Webhook通知
        if "webhook" in channels and self.config.get("webhook_url"):
            self._send_webhook(notification)
    
    def notify_fetch_failure(self, source_name: str, url: str, error: str):
        """抓取失败通知"""
        self.send_notification(
            title=f"抓取失败: {source_name}",
            message=f"信源 {source_name} 抓取失败\nURL: {url}\n错误: {error}",
            level="error",
            data={"source": source_name, "url": url, "error": error}
        )
    
    def notify_processing_failure(self, url: str, error: str):
        """处理失败通知"""
        self.send_notification(
            title=f"处理失败: {url[:50]}...",
            message=f"素材处理失败\nURL: {url}\n错误: {error}",
            level="error",
            data={"url": url, "error": error}
        )
    
    def notify_task_complete(self, results: Dict[str, Any]):
        """任务完成通知"""
        self.send_notification(
            title="定时抓取任务完成",
            message=f"总计: {results.get('total', 0)}条\n新增: {results.get('new', 0)}条\n失败: {results.get('failed', 0)}条",
            level="info",
            data=results
        )
    
    def notify_daily_report(self, report_path: str):
        """日报生成通知"""
        self.send_notification(
            title="日报已生成",
            message=f"日报已生成并保存\n路径: {report_path}",
            level="info",
            data={"path": report_path}
        )
    
    def _send_log(self, notification: Dict):
        """日志通知"""
        level = notification.get("level", "info")
        title = notification.get("title", "")
        message = notification.get("message", "")
        
        if level == "error":
            logger.error(f"[通知] {title}: {message}")
        elif level == "warning":
            logger.warning(f"[通知] {title}: {message}")
        else:
            logger.info(f"[通知] {title}: {message}")
    
    def _send_file(self, notification: Dict):
        """文件通知（追加到JSON文件）"""
        filepath = self.config.get("notification_file", "data/notifications.json")
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        notifications = []
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    notifications = json.load(f)
            except:
                notifications = []
        
        notifications.append(notification)
        
        # 只保留最近100条
        if len(notifications) > 100:
            notifications = notifications[-100:]
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(notifications, f, ensure_ascii=False, indent=2)
    
    def _send_webhook(self, notification: Dict):
        """Webhook通知"""
        webhook_url = self.config.get("webhook_url", "")
        if not webhook_url:
            return
        
        try:
            payload = {
                "title": notification.get("title", ""),
                "message": notification.get("message", ""),
                "level": notification.get("level", "info"),
                "time": notification.get("time", "")
            }
            requests.post(webhook_url, json=payload, timeout=10)
        except Exception as e:
            logger.warning(f"Webhook通知发送失败: {e}")
