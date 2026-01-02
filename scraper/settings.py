"""
Scrapy爬虫配置
"""
import os
import sys

# 添加项目根目录到Python路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from config import SCRAPER_CONFIG

# Scrapy基础设置
BOT_NAME = 'pharma_scraper'

SPIDER_MODULES = ['scraper.spiders']
NEWSPIDER_MODULE = 'scraper.spiders'

# 遵守robots.txt规则
ROBOTSTXT_OBEY = True

# 请求配置
USER_AGENT = SCRAPER_CONFIG.get('USER_AGENT', 'Mozilla/5.0 (compatible; PharmaScraper/1.0)')
DOWNLOAD_DELAY = SCRAPER_CONFIG.get('DOWNLOAD_DELAY', 1)
CONCURRENT_REQUESTS = SCRAPER_CONFIG.get('CONCURRENT_REQUESTS', 8)
CONCURRENT_REQUESTS_PER_DOMAIN = 4

# 重试配置
RETRY_ENABLED = True
RETRY_TIMES = SCRAPER_CONFIG.get('RETRY_TIMES', 3)
RETRY_HTTP_CODES = SCRAPER_CONFIG.get('RETRY_HTTP_CODES', [500, 502, 503, 504, 408])

# 超时配置
DOWNLOAD_TIMEOUT = 30

# 启用的管道
ITEM_PIPELINES = {
    'scraper.pipelines.DataCleaningPipeline': 100,
    'scraper.pipelines.ValidationPipeline': 200,
    'scraper.pipelines.DatabasePipeline': 300,
}

# 下载中间件配置
DOWNLOADER_MIDDLEWARES = {
    'scraper.middlewares.ErrorLoggingMiddleware': 100,
    'scraper.middlewares.CustomRetryMiddleware': 550,  # 替换默认重试中间件
    'scraper.middlewares.RequestStatsMiddleware': 900,
    'scrapy.downloadermiddlewares.retry.RetryMiddleware': None,  # 禁用默认重试
}

# 重试延迟配置（指数退避：1秒、2秒、4秒）
RETRY_DELAYS = [1, 2, 4]

# 日志配置
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s [%(name)s] %(levelname)s: %(message)s'
LOG_FILE = None  # 设置为文件路径可将日志写入文件，如 'scraper.log'

# 禁用Telnet控制台
TELNETCONSOLE_ENABLED = False

# 请求头配置
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

# AutoThrottle扩展配置（自动调节请求速率）
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0

# 缓存配置（开发时可启用）
# HTTPCACHE_ENABLED = True
# HTTPCACHE_EXPIRATION_SECS = 3600
# HTTPCACHE_DIR = 'httpcache'
