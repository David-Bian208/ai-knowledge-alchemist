"""
信源健康检测模块
负责检测信源的可访问性，记录健康日志，标记失效信源
"""
import time
import requests
import logging
from datetime import datetime
from src.storage import HotStorage

logger = logging.getLogger(__name__)

UNHEALTHY_THRESHOLD = 3  # 连续失败3次标记为失效


class SourceHealthChecker:
    """信源健康检测器"""

    def __init__(self, storage: HotStorage = None):
        self.storage = storage or HotStorage()

    def check_source(self, source_id: str, source_name: str, source_url: str, source_type: str = "web"):
        """
        检测单个信源的健康状态
        返回检测结果字典
        """
        start_time = time.time()
        result = {
            "source_id": source_id,
            "source_name": source_name,
            "source_url": source_url,
            "check_time": datetime.now().isoformat(),
            "reachable": False,
            "status": "unknown",
            "error_message": None,
            "response_time_ms": 0,
            "content_count": 0
        }

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            if source_type == 'rss':
                response = requests.head(source_url, headers=headers, timeout=10, allow_redirects=True)
            else:
                response = requests.get(source_url, headers=headers, timeout=10, stream=True)
                response.content[:1024]  # 只读取前1KB

            elapsed_ms = int((time.time() - start_time) * 1000)
            status_code = response.status_code

            result["response_time_ms"] = elapsed_ms
            result["status"] = f"HTTP_{status_code}"

            if status_code < 400:
                result["reachable"] = True
                logger.info(f"[健康检测] ✅ {source_name}: {status_code} ({elapsed_ms}ms)")
            else:
                result["error_message"] = f"HTTP {status_code}"
                logger.warning(f"[健康检测] ❌ {source_name}: HTTP {status_code}")

        except requests.exceptions.Timeout:
            result["status"] = "timeout"
            result["error_message"] = "请求超时"
            logger.warning(f"[健康检测] ❌ {source_name}: 超时")

        except requests.exceptions.ConnectionError:
            result["status"] = "connection_error"
            result["error_message"] = "连接失败"
            logger.warning(f"[健康检测] ❌ {source_name}: 连接失败")

        except Exception as e:
            result["status"] = "error"
            result["error_message"] = str(e)[:100]
            logger.warning(f"[健康检测] ❌ {source_name}: {e}")

        # 记录健康日志
        self.storage.save_source_health_log(
            source_id=source_id,
            source_name=source_name,
            source_url=source_url,
            status=result["status"],
            reachable=result["reachable"],
            error_message=result["error_message"],
            content_count=result["content_count"],
            response_time_ms=result["response_time_ms"]
        )

        # 更新状态汇总
        self.storage.update_source_status(
            source_id=source_id,
            source_name=source_name,
            source_url=source_url,
            is_healthy=result["reachable"],
            error_message=result["error_message"]
        )

        return result

    def check_all_sources(self, sources: list):
        """
        批量检测所有信源
        sources: 信源对象列表（包含id, name, url, type属性）
        返回检测结果列表
        """
        results = []
        for source in sources:
            source_id = getattr(source, 'id', None) or source.get('id', '')
            source_name = getattr(source, 'name', None) or source.get('name', '')
            source_url = getattr(source, 'url', None) or source.get('url', '')
            source_type = getattr(source, 'type', None) or source.get('type', 'web')

            if not source_id or not source_url:
                continue

            result = self.check_source(source_id, source_name, source_url, source_type)
            results.append(result)

        return results

    def get_unhealthy_sources(self):
        """获取所有失效信源列表"""
        return self.storage.get_unhealthy_sources()

    def get_source_health(self, source_id: str):
        """获取指定信源的健康状态"""
        return self.storage.get_source_health(source_id)
