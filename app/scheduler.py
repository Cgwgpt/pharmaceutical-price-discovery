"""
定时任务调度器
使用APScheduler实现每日自动爬取和监控
"""
import logging
import subprocess
from datetime import datetime
from typing import List, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from config import DATABASE_URL
from app.models import Drug, init_db

logger = logging.getLogger(__name__)


class TaskScheduler:
    """
    定时任务调度器
    
    功能:
    - 定时爬取药品价格
    - 定时检测价格变动
    - 定时生成监控报告
    """
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.engine, SessionLocal = init_db(DATABASE_URL)
        self.session = SessionLocal()
        self._setup_jobs()
    
    def _setup_jobs(self):
        """配置定时任务"""
        # 每天早上8点爬取药品价格
        self.scheduler.add_job(
            self.crawl_prices,
            CronTrigger(hour=8, minute=0),
            id='daily_crawl',
            name='每日价格爬取',
            replace_existing=True
        )
        
        # 每小时检测价格变动
        self.scheduler.add_job(
            self.check_price_alerts,
            IntervalTrigger(hours=1),
            id='hourly_alert_check',
            name='每小时价格告警检测',
            replace_existing=True
        )
        
        # 每天晚上10点生成日报
        self.scheduler.add_job(
            self.generate_daily_report,
            CronTrigger(hour=22, minute=0),
            id='daily_report',
            name='每日监控报告',
            replace_existing=True
        )
    
    def start(self):
        """启动调度器"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("定时任务调度器已启动")
    
    def stop(self):
        """停止调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("定时任务调度器已停止")
    
    def crawl_prices(self, keywords: List[str] = None):
        """
        执行价格爬取任务
        
        Args:
            keywords: 要爬取的药品关键词列表
        """
        logger.info(f"[{datetime.now()}] 开始执行价格爬取任务")
        
        if not keywords:
            # 从监控列表获取关键词
            keywords = self._get_watch_list()
        
        if not keywords:
            keywords = ['感冒', '阿莫西林', '布洛芬']  # 默认关键词
        
        for keyword in keywords:
            try:
                logger.info(f"爬取关键词: {keyword}")
                # 调用Scrapy爬虫
                result = subprocess.run(
                    ['scrapy', 'crawl', 'ysbang_spider', '-a', f'keyword={keyword}', '-a', 'max_pages=3'],
                    cwd='.',
                    capture_output=True,
                    text=True,
                    timeout=300  # 5分钟超时
                )
                if result.returncode == 0:
                    logger.info(f"关键词 '{keyword}' 爬取完成")
                else:
                    logger.error(f"关键词 '{keyword}' 爬取失败: {result.stderr}")
            except subprocess.TimeoutExpired:
                logger.error(f"关键词 '{keyword}' 爬取超时")
            except Exception as e:
                logger.error(f"关键词 '{keyword}' 爬取异常: {e}")
        
        logger.info(f"[{datetime.now()}] 价格爬取任务完成")
    
    def check_price_alerts(self, threshold: float = 5.0):
        """
        检测价格变动告警
        
        Args:
            threshold: 价格变动阈值百分比
        """
        logger.info(f"[{datetime.now()}] 开始检测价格变动")
        
        from app.services.monitor_service import MonitorService
        from app.services.alert_service import AlertService
        
        monitor = MonitorService()
        alert_service = AlertService()
        
        alerts = monitor.get_price_alerts(threshold=threshold)
        
        if alerts:
            logger.info(f"发现 {len(alerts)} 个价格变动告警")
            for alert in alerts:
                # 记录告警
                alert_service.create_alert(
                    drug_id=alert['drug_id'],
                    alert_type='price_change',
                    message=f"{alert['drug_name']} 价格变动 {alert['change_percent']:.2f}%",
                    data=alert
                )
        else:
            logger.info("未发现价格变动告警")
    
    def generate_daily_report(self):
        """生成每日监控报告"""
        logger.info(f"[{datetime.now()}] 开始生成每日报告")
        
        from app.services.monitor_service import MonitorService
        from app.services.report_service import ReportService
        
        monitor = MonitorService()
        report_service = ReportService()
        
        summary = monitor.get_daily_summary()
        report = report_service.generate_daily_report(summary)
        
        logger.info(f"每日报告已生成: {report}")
    
    def _get_watch_list(self) -> List[str]:
        """获取监控药品列表"""
        # 从数据库获取所有药品名称
        drugs = self.session.query(Drug.name).distinct().limit(50).all()
        return [d[0] for d in drugs]
    
    def add_crawl_job(self, keyword: str, cron_expr: str = None, interval_hours: int = None):
        """
        添加自定义爬取任务
        
        Args:
            keyword: 药品关键词
            cron_expr: Cron表达式 (如 "0 8 * * *")
            interval_hours: 间隔小时数
        """
        job_id = f'crawl_{keyword}'
        
        if cron_expr:
            trigger = CronTrigger.from_crontab(cron_expr)
        elif interval_hours:
            trigger = IntervalTrigger(hours=interval_hours)
        else:
            trigger = IntervalTrigger(hours=24)  # 默认每天一次
        
        self.scheduler.add_job(
            lambda: self.crawl_prices([keyword]),
            trigger,
            id=job_id,
            name=f'爬取 {keyword}',
            replace_existing=True
        )
        logger.info(f"已添加爬取任务: {keyword}")
    
    def remove_job(self, job_id: str):
        """移除定时任务"""
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"已移除任务: {job_id}")
        except Exception as e:
            logger.error(f"移除任务失败: {e}")
    
    def get_jobs(self) -> List[dict]:
        """获取所有定时任务"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        return jobs


# 全局调度器实例
scheduler = None


def get_scheduler() -> TaskScheduler:
    """获取调度器单例"""
    global scheduler
    if scheduler is None:
        scheduler = TaskScheduler()
    return scheduler


def init_scheduler(app):
    """初始化调度器（Flask集成）"""
    global scheduler
    scheduler = TaskScheduler()
    scheduler.start()
    
    # 注册关闭钩子
    import atexit
    atexit.register(lambda: scheduler.stop())
    
    return scheduler
