"""
定时任务调度器
每天北京时间8:00自动生成前一日日报
"""
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Callable
from src.daily_generator import generate_daily_report
from src.storage import HotStorage


class DailyScheduler:
    """日报定时调度器"""

    def __init__(self, hour: int = 8, minute: int = 0, timezone_offset: int = 8):
        """
        Args:
            hour: 执行小时（北京时间）
            minute: 执行分钟
            timezone_offset: 时区偏移（UTC+8）
        """
        self.hour = hour
        self.minute = minute
        self.timezone_offset = timezone_offset
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_run_date: Optional[str] = None
        self._last_sync_time: Optional[datetime] = None
        self._last_full_fetch_date: Optional[str] = None
        self._last_full_sync_date: Optional[str] = None

    def start(self, storage: HotStorage = None, llm_config: dict = None):
        """启动定时任务"""
        if self._running:
            print("[定时任务] 已在运行中")
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop,
            args=(storage, llm_config),
            daemon=True,
            name="daily-report-scheduler"
        )
        self._thread.start()
        print(f"[定时任务] 已启动，每天北京时间 {self.hour:02d}:{self.minute:02d} 生成日报")

    def stop(self):
        """停止定时任务"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        print("[定时任务] 已停止")

    def _sync_aihot_task(self):
        """定时同步AI HOT内容任务"""
        from src.sync_aihot import sync_items
        try:
            print("[定时任务] AI HOT同步开始...")
            saved_selected = sync_items("selected")
            saved_all = sync_items("all")
            total_saved = saved_selected + saved_all
            print(f"[定时任务] AI HOT同步完成，新增 {total_saved} 条内容")
        except Exception as e:
            print(f"[定时任务] AI HOT同步失败: {e}")

    def _dual_fetch_task(self):
        """双数据源并行抓取任务"""
        from src.fetch import quick_fetch_task
        from src.storage import HotStorage
        
        storage = HotStorage()
        aihot_enabled = storage.get_config("aihot_enabled", "true") == "true"
        
        threads = []
        # 只有开关开启的时候才执行AI HOT同步
        if aihot_enabled:
            t2 = threading.Thread(target=self._sync_aihot_task)
            threads.append(t2)
            t2.start()
        
        # 原有爬虫始终执行
        t1 = threading.Thread(target=quick_fetch_task)
        threads.append(t1)
        t1.start()
        
        # 等待所有任务完成
        for t in threads:
            t.join()

    def _run_loop(self, storage: HotStorage, llm_config: dict):
        """主循环"""
        from src.fetch import full_fetch_task
        while self._running:
            now = datetime.utcnow() + timedelta(hours=self.timezone_offset)
            
            # 读取间隔更新配置
            interval_enabled = storage.get_config("interval_enabled", "true") == "true"
            if interval_enabled:
                sync_interval = int(storage.get_config("sync_interval", "60"))
                if self._last_sync_time is None or (now - self._last_sync_time) >= timedelta(minutes=sync_interval):
                    self._last_sync_time = now
                    print(f"[定时任务] 开始执行{sync_interval}分钟双数据源同步...")
                    self._dual_fetch_task()
                    
                    # 更新后自动生成日报
                    auto_generate = storage.get_config("auto_generate_report", "true") == "true"
                    if auto_generate:
                        self._execute(storage, llm_config)
            
            # 读取定时更新配置
            scheduled_enabled = storage.get_config("scheduled_enabled", "false") == "true"
            if scheduled_enabled:
                scheduled_time_str = storage.get_config("scheduled_time", "08:00")
            if ":" in str(scheduled_time_str):
                scheduled_hour = int(scheduled_time_str.split(":")[0])
                scheduled_minute = int(scheduled_time_str.split(":")[1])
            else:
                scheduled_hour = int(scheduled_time_str)
                scheduled_minute = 0
                scheduled_minute = 0
                today_date = now.strftime("%Y-%m-%d")
                
                if now.hour == scheduled_hour and now.minute == scheduled_minute:
                    # 确保每天只执行一次
                    if today_date != self._last_run_date:
                        self._last_run_date = today_date
                        print(f"[定时任务] 开始执行定时更新（每天{scheduled_hour:02d}:{scheduled_minute:02d}）...")
                        self._dual_fetch_task()
                        
                        # 更新后自动生成日报
                        auto_generate = storage.get_config("auto_generate_report", "true") == "true"
                        if auto_generate:
                            self._execute(storage, llm_config)
            
            # 手动模式：仍然支持每天凌晨2点的全量抓取
            if now.hour == 2 and now.minute == 0:
                today_date = now.strftime("%Y-%m-%d")
                if today_date != self._last_full_fetch_date:
                    self._last_full_fetch_date = today_date
                    print("[定时任务] 开始执行全量抓取...")
                    full_fetch_task()
                    
                    # 全量抓取后自动生成日报
                    auto_generate = storage.get_config("auto_generate_report", "true") == "true"
                    if auto_generate:
                        self._execute(storage, llm_config)
            
            # 每天凌晨2点05分清理过期L1缓存
            if now.hour == 2 and now.minute == 5:
                today_date = now.strftime("%Y-%m-%d")
                cleanup_key = f"cleanup_{today_date}"
                if cleanup_key != getattr(self, '_last_cleanup_key', None):
                    self._last_cleanup_key = cleanup_key
                    retention_days = int(storage.get_config("l1_retention_days", "7"))
                    cleaned = storage.clean_raw_cache_expired(retention_days)
                    print(f"[定时任务] L1缓存清理完成，清理 {cleaned} 条过期数据（保留{retention_days}天）")
            
            # 每天凌晨2点10分执行一次AI HOT全量同步（开关开启才执行）
            if now.hour == 2 and now.minute == 10:
                today_date = now.strftime("%Y-%m-%d")
                if today_date != self._last_full_sync_date:
                    aihot_enabled = storage.get_config("aihot_enabled", "true") == "true"
                    if aihot_enabled:
                        self._last_full_sync_date = today_date
                        print("[定时任务] 开始执行AI HOT全量同步...")
                        self._sync_aihot_task()
            
            # 每分钟检查一次
            time.sleep(60)

    def _execute(self, storage: HotStorage, llm_config: dict):
        """执行日报生成任务"""
        try:
            # 生成昨天的日报
            yesterday = (datetime.utcnow() + timedelta(hours=self.timezone_offset) - timedelta(days=1)).strftime("%Y-%m-%d")
            
            print(f"[定时任务] 开始生成 {yesterday} 的日报...")
            result = generate_daily_report(yesterday, storage, llm_config)
            
            if "error" in result:
                print(f"[定时任务] 日报生成失败: {result['error']}")
            else:
                print(f"[定时任务] ✅ 日报生成成功: {result['date']}, {result['total_items']} 条内容")
        except Exception as e:
            print(f"[定时任务] 异常: {e}")
            import traceback
            traceback.print_exc()

    def run_now(self, storage: HotStorage = None, llm_config: dict = None):
        """立即执行一次（用于测试）"""
        print("[定时任务] 手动触发执行...")
        self._execute(storage, llm_config)

    def is_running(self) -> bool:
        """检查是否在运行"""
        return self._running


# 全局实例
_scheduler: Optional[DailyScheduler] = None


def get_scheduler() -> DailyScheduler:
    """获取全局调度器实例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = DailyScheduler(hour=8, minute=0)
    return _scheduler


def start_scheduler(storage: HotStorage = None, llm_config: dict = None):
    """启动全局调度器"""
    scheduler = get_scheduler()
    scheduler.start(storage, llm_config)
    return scheduler


def stop_scheduler():
    """停止全局调度器"""
    global _scheduler
    if _scheduler:
        _scheduler.stop()
        _scheduler = None


if __name__ == "__main__":
    # 测试定时任务
    print("=== 测试定时任务 ===")
    scheduler = DailyScheduler(hour=8, minute=0)
    
    # 手动触发一次
    scheduler.run_now()
    
    print("\n提示：定时任务需要持续运行，建议使用 systemd 或 cron 来管理生产环境的定时任务")
    print("Gradio应用内可使用scheduler.start()启动后台线程")
