"""
Flask应用初始化
医药价格发现系统Web界面
"""
from flask import Flask
from config import DATABASE_URL


def create_app(config_name: str = 'default') -> Flask:
    """
    创建Flask应用实例
    
    Args:
        config_name: 配置名称
        
    Returns:
        Flask应用实例
    """
    app = Flask(__name__)
    
    # 配置
    app.config['SECRET_KEY'] = 'pharma-price-discovery-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # 注册蓝图
    from app.routes import main_bp
    app.register_blueprint(main_bp)
    
    # 注册API蓝图
    from app.api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # 初始化定时任务调度器（可选）
    if app.config.get('ENABLE_SCHEDULER', False):
        from app.scheduler import init_scheduler
        init_scheduler(app)
    
    return app
