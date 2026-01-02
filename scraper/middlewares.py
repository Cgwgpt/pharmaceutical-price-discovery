"""
Scrapy中间件
实现错误处理、重试机制和日志记录
"""
import logging
from datetime import datetime
from typing import Optional

from scrapy import signals
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.http import Request, Response
from scrapy.spiders import Spider
from scrapy.utils.response import response_status_message


logger = logging.getLogger(__name__)


class ErrorLoggingMiddleware:
    """
    错误日志记录中间件
    
    记录所有请求错误和异常，便于监控和调试
    """
    
    def __init__(self, stats):
        self.stats = stats
        self.error_log = []
    
    @classmethod
    def from_crawler(cls, crawler):
        middleware = cls(crawler.stats)
        crawler.signals.connect(middleware.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(middleware.spider_closed, signal=signals.spider_closed)
        return middleware
    
    def spider_opened(self, spider):
        """爬虫启动时初始化"""
        logger.info(f"错误日志中间件已启动: {spider.name}")
        self.error_log = []
    
    def spider_closed(self, spider):
        """爬虫关闭时输出错误统计"""
        if self.error_log:
            logger.warning(f"爬虫 {spider.name} 共发生 {len(self.error_log)} 个错误")
            for error in self.error_log[-10:]:  # 只显示最后10个错误
                logger.warning(f"  - {error['url']}: {error['error']}")
        else:
            logger.info(f"爬虫 {spider.name} 运行完成，无错误")
    
    def process_response(self, request: Request, response: Response, spider: Spider) -> Response:
        """
        处理响应，记录非200状态码
        """
        if response.status >= 400:
            self._log_error(
                url=request.url,
                error=f"HTTP {response.status}: {response_status_message(response.status)}",
                spider=spider
            )
        return response
    
    def process_exception(self, request: Request, exception: Exception, spider: Spider):
        """
        处理异常，记录错误信息
        """
        self._log_error(
            url=request.url,
            error=f"{type(exception).__name__}: {str(exception)}",
            spider=spider
        )
        return None  # 让其他中间件继续处理
    
    def _log_error(self, url: str, error: str, spider: Spider):
        """记录错误到日志"""
        error_entry = {
            'url': url,
            'error': error,
            'timestamp': datetime.now().isoformat(),
            'spider': spider.name
        }
        self.error_log.append(error_entry)
        
        # 更新统计
        self.stats.inc_value('error_log/total')
        
        logger.error(f"[{spider.name}] 请求错误 - URL: {url}, 错误: {error}")


class CustomRetryMiddleware(RetryMiddleware):
    """
    自定义重试中间件
    
    扩展默认重试中间件，添加：
    - 递增延迟（指数退避）
    - 详细的重试日志
    - 重试统计
    """
    
    def __init__(self, settings):
        super().__init__(settings)
        self.retry_delays = settings.getlist('RETRY_DELAYS', [1, 2, 4])
        logger.info(f"重试中间件已初始化，最大重试次数: {self.max_retry_times}")
    
    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)
    
    def _retry(self, request: Request, reason, spider: Spider) -> Optional[Request]:
        """
        执行重试逻辑
        
        Args:
            request: 原始请求
            reason: 重试原因
            spider: 爬虫实例
            
        Returns:
            重试请求或None
        """
        retry_times = request.meta.get('retry_times', 0) + 1
        
        if retry_times <= self.max_retry_times:
            # 计算延迟时间（指数退避）
            delay_index = min(retry_times - 1, len(self.retry_delays) - 1)
            delay = self.retry_delays[delay_index] if self.retry_delays else 1
            
            logger.warning(
                f"重试请求 ({retry_times}/{self.max_retry_times}): {request.url}, "
                f"原因: {reason}, 延迟: {delay}秒"
            )
            
            # 创建重试请求
            retry_request = request.copy()
            retry_request.meta['retry_times'] = retry_times
            retry_request.meta['download_delay'] = delay
            retry_request.dont_filter = True
            
            # 更新统计
            spider.crawler.stats.inc_value('retry/count')
            spider.crawler.stats.inc_value(f'retry/reason/{reason}')
            
            return retry_request
        else:
            logger.error(
                f"放弃请求（已达最大重试次数）: {request.url}, "
                f"原因: {reason}"
            )
            spider.crawler.stats.inc_value('retry/max_reached')
            return None
    
    def process_response(self, request: Request, response: Response, spider: Spider):
        """
        处理响应，检查是否需要重试
        """
        if response.status in self.retry_http_codes:
            reason = response_status_message(response.status)
            return self._retry(request, reason, spider) or response
        return response
    
    def process_exception(self, request: Request, exception: Exception, spider: Spider):
        """
        处理异常，检查是否需要重试
        """
        if isinstance(exception, self.EXCEPTIONS_TO_RETRY):
            return self._retry(request, str(exception), spider)
        return None


class RequestStatsMiddleware:
    """
    请求统计中间件
    
    记录请求的详细统计信息
    """
    
    def __init__(self, stats):
        self.stats = stats
    
    @classmethod
    def from_crawler(cls, crawler):
        middleware = cls(crawler.stats)
        crawler.signals.connect(middleware.spider_closed, signal=signals.spider_closed)
        return middleware
    
    def spider_closed(self, spider):
        """爬虫关闭时输出统计"""
        logger.info("=" * 50)
        logger.info("爬虫统计信息:")
        logger.info(f"  总请求数: {self.stats.get_value('downloader/request_count', 0)}")
        logger.info(f"  成功响应: {self.stats.get_value('downloader/response_status_count/200', 0)}")
        logger.info(f"  重试次数: {self.stats.get_value('retry/count', 0)}")
        logger.info(f"  错误总数: {self.stats.get_value('error_log/total', 0)}")
        logger.info(f"  提取项目: {self.stats.get_value('item_scraped_count', 0)}")
        logger.info(f"  丢弃项目: {self.stats.get_value('item_dropped_count', 0)}")
        logger.info("=" * 50)
    
    def process_request(self, request: Request, spider: Spider):
        """记录请求"""
        self.stats.inc_value('request/total')
        return None
    
    def process_response(self, request: Request, response: Response, spider: Spider) -> Response:
        """记录响应状态"""
        self.stats.inc_value(f'response/status/{response.status}')
        return response
