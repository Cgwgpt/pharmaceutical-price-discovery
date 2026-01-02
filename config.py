"""
医药价格发现系统配置文件
"""
import os

# 基础路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 数据库配置
DATABASE_URL = os.environ.get('DATABASE_URL', f'sqlite:///{os.path.join(BASE_DIR, "pharma_prices.db")}')

# Flask配置
class Config:
    """Flask应用配置"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

# 爬虫配置
SCRAPER_CONFIG = {
    'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'DOWNLOAD_DELAY': 1,  # 请求间隔（秒）
    'CONCURRENT_REQUESTS': 8,  # 并发请求数
    'RETRY_TIMES': 3,  # 重试次数
    'RETRY_HTTP_CODES': [500, 502, 503, 504, 408],
}

# 测试配置
class TestConfig(Config):
    """测试环境配置"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
