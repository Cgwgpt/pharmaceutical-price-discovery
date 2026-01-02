"""
API接口定义
提供JSON格式的数据接口
"""
from flask import Blueprint, jsonify, request
from app.services.price_service import PriceService

api_bp = Blueprint('api', __name__)


@api_bp.route('/prices')
def get_prices():
    """获取最新价格列表"""
    limit = request.args.get('limit', 50, type=int)
    
    service = PriceService()
    prices = service.get_recent_prices(limit=limit)
    
    return jsonify({
        'code': 0,
        'data': prices,
        'total': len(prices)
    })


@api_bp.route('/search')
def search_drugs():
    """搜索药品"""
    keyword = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    if not keyword:
        return jsonify({
            'code': 400,
            'message': '请输入搜索关键词'
        }), 400
    
    service = PriceService()
    result = service.search_drugs(keyword, page=page, per_page=per_page)
    
    return jsonify({
        'code': 0,
        'data': result['drugs'],
        'total': result['total'],
        'page': page,
        'pages': result['pages']
    })


@api_bp.route('/drug/<int:drug_id>')
def get_drug(drug_id: int):
    """获取药品详情"""
    service = PriceService()
    drug = service.get_drug_by_id(drug_id)
    
    if not drug:
        return jsonify({
            'code': 404,
            'message': '药品不存在'
        }), 404
    
    prices = service.get_drug_prices(drug_id)
    
    return jsonify({
        'code': 0,
        'data': {
            'drug': drug,
            'prices': prices
        }
    })


@api_bp.route('/compare')
def compare_prices():
    """比价接口"""
    drug_name = request.args.get('drug', '').strip()
    specification = request.args.get('spec', '').strip()
    category = request.args.get('category', '').strip()  # drug, cosmetic, medical_device
    
    if not drug_name:
        return jsonify({
            'code': 400,
            'message': '请输入药品名称'
        }), 400
    
    from app.services.compare_service import CompareService
    service = CompareService()
    comparison = service.compare_prices(drug_name, specification or None, category or None)
    
    return jsonify({
        'code': 0,
        'data': comparison
    })


@api_bp.route('/compare/savings')
def calculate_savings():
    """计算批量采购节省金额"""
    drug_name = request.args.get('drug', '').strip()
    quantity = request.args.get('quantity', 1, type=int)
    
    if not drug_name:
        return jsonify({
            'code': 400,
            'message': '请输入药品名称'
        }), 400
    
    from app.services.compare_service import CompareService
    service = CompareService()
    savings = service.calculate_batch_savings(drug_name, quantity)
    
    return jsonify({
        'code': 0,
        'data': savings
    })


@api_bp.route('/compare/ranking')
def price_ranking():
    """获取价差最大的药品排名"""
    limit = request.args.get('limit', 20, type=int)
    
    from app.services.compare_service import CompareService
    service = CompareService()
    ranking = service.get_price_ranking(limit)
    
    return jsonify({
        'code': 0,
        'data': ranking,
        'total': len(ranking)
    })


@api_bp.route('/statistics')
def get_statistics():
    """获取统计信息"""
    service = PriceService()
    stats = service.get_statistics()
    
    return jsonify({
        'code': 0,
        'data': stats
    })



@api_bp.route('/monitor/alerts')
def get_alerts():
    """获取价格变动告警"""
    threshold = request.args.get('threshold', 5.0, type=float)
    limit = request.args.get('limit', 50, type=int)
    
    from app.services.monitor_service import MonitorService
    service = MonitorService()
    alerts = service.get_price_alerts(threshold=threshold, limit=limit)
    
    return jsonify({
        'code': 0,
        'data': alerts,
        'total': len(alerts)
    })


@api_bp.route('/monitor/summary')
def get_daily_summary():
    """获取每日监控汇总"""
    from app.services.monitor_service import MonitorService
    service = MonitorService()
    summary = service.get_daily_summary()
    
    return jsonify({
        'code': 0,
        'data': summary
    })


@api_bp.route('/monitor/trend/<int:drug_id>')
def get_price_trend(drug_id: int):
    """获取药品价格趋势"""
    days = request.args.get('days', 30, type=int)
    
    from app.services.monitor_service import MonitorService
    service = MonitorService()
    trend = service.get_price_trend(drug_id, days)
    
    return jsonify({
        'code': 0,
        'data': trend
    })


@api_bp.route('/recommendation/<drug_name>')
def get_recommendation(drug_name: str):
    """获取采购建议"""
    quantity = request.args.get('quantity', 1, type=int)
    
    from app.services.recommendation_service import RecommendationService
    service = RecommendationService()
    recommendation = service.get_recommendation(drug_name, quantity)
    
    return jsonify({
        'code': 0,
        'data': recommendation
    })


@api_bp.route('/recommendation/opportunities')
def get_opportunities():
    """获取最佳采购机会"""
    limit = request.args.get('limit', 20, type=int)
    
    from app.services.recommendation_service import RecommendationService
    service = RecommendationService()
    opportunities = service.get_top_savings_opportunities(limit)
    
    return jsonify({
        'code': 0,
        'data': opportunities,
        'total': len(opportunities)
    })



# ==================== 告警API ====================

@api_bp.route('/alerts')
def list_alerts():
    """获取告警列表"""
    days = request.args.get('days', 7, type=int)
    is_read = request.args.get('is_read', type=lambda x: x.lower() == 'true')
    limit = request.args.get('limit', 100, type=int)
    
    from app.services.alert_service import AlertService
    service = AlertService()
    alerts = service.get_alerts(days=days, is_read=is_read, limit=limit)
    
    return jsonify({
        'code': 0,
        'data': alerts,
        'total': len(alerts)
    })


@api_bp.route('/alerts/unread-count')
def get_unread_alert_count():
    """获取未读告警数量"""
    from app.services.alert_service import AlertService
    service = AlertService()
    count = service.get_unread_count()
    
    return jsonify({
        'code': 0,
        'data': {'count': count}
    })


@api_bp.route('/alerts/<int:alert_id>/read', methods=['POST'])
def mark_alert_read(alert_id: int):
    """标记告警为已读"""
    from app.services.alert_service import AlertService
    service = AlertService()
    success = service.mark_as_read(alert_id)
    
    return jsonify({
        'code': 0 if success else 404,
        'message': '已标记为已读' if success else '告警不存在'
    })


@api_bp.route('/alerts/read-all', methods=['POST'])
def mark_all_alerts_read():
    """标记所有告警为已读"""
    from app.services.alert_service import AlertService
    service = AlertService()
    count = service.mark_all_as_read()
    
    return jsonify({
        'code': 0,
        'data': {'count': count},
        'message': f'已标记{count}条告警为已读'
    })


@api_bp.route('/alerts/statistics')
def get_alert_statistics():
    """获取告警统计"""
    days = request.args.get('days', 7, type=int)
    
    from app.services.alert_service import AlertService
    service = AlertService()
    stats = service.get_alert_statistics(days)
    
    return jsonify({
        'code': 0,
        'data': stats
    })


# ==================== 调度API ====================

@api_bp.route('/scheduler/jobs')
def get_scheduler_jobs():
    """获取定时任务列表"""
    from app.scheduler import get_scheduler
    scheduler = get_scheduler()
    jobs = scheduler.get_jobs()
    
    return jsonify({
        'code': 0,
        'data': jobs,
        'total': len(jobs)
    })


@api_bp.route('/scheduler/crawl', methods=['POST'])
def trigger_crawl():
    """手动触发爬取任务"""
    data = request.get_json() or {}
    keywords = data.get('keywords', [])
    
    from app.scheduler import get_scheduler
    scheduler = get_scheduler()
    
    # 异步执行爬取
    import threading
    thread = threading.Thread(target=scheduler.crawl_prices, args=(keywords,))
    thread.start()
    
    return jsonify({
        'code': 0,
        'message': '爬取任务已启动',
        'keywords': keywords or ['默认关键词']
    })


@api_bp.route('/scheduler/add-job', methods=['POST'])
def add_scheduler_job():
    """添加定时爬取任务"""
    data = request.get_json() or {}
    keyword = data.get('keyword')
    interval_hours = data.get('interval_hours', 24)
    
    if not keyword:
        return jsonify({
            'code': 400,
            'message': '请提供药品关键词'
        }), 400
    
    from app.scheduler import get_scheduler
    scheduler = get_scheduler()
    scheduler.add_crawl_job(keyword, interval_hours=interval_hours)
    
    return jsonify({
        'code': 0,
        'message': f'已添加定时任务: {keyword}',
        'interval_hours': interval_hours
    })


# ==================== 报告API ====================

@api_bp.route('/reports')
def list_reports():
    """获取报告列表"""
    report_type = request.args.get('type')
    
    from app.services.report_service import ReportService
    service = ReportService()
    reports = service.list_reports(report_type)
    
    return jsonify({
        'code': 0,
        'data': reports,
        'total': len(reports)
    })


@api_bp.route('/reports/daily', methods=['POST'])
def generate_daily_report():
    """生成每日报告"""
    from app.services.report_service import ReportService
    service = ReportService()
    report_path = service.generate_daily_report()
    
    return jsonify({
        'code': 0,
        'message': '报告已生成',
        'path': report_path
    })


@api_bp.route('/reports/price-analysis', methods=['POST'])
def generate_price_analysis_report():
    """生成价格分析报告"""
    data = request.get_json() or {}
    drug_name = data.get('drug_name')
    days = data.get('days', 30)
    
    if not drug_name:
        return jsonify({
            'code': 400,
            'message': '请提供药品名称'
        }), 400
    
    from app.services.report_service import ReportService
    service = ReportService()
    report_path = service.generate_price_analysis_report(drug_name, days)
    
    if not report_path:
        return jsonify({
            'code': 404,
            'message': '未找到该药品数据'
        }), 404
    
    return jsonify({
        'code': 0,
        'message': '报告已生成',
        'path': report_path
    })


# ==================== 标准化API ====================

@api_bp.route('/normalize/drug-name')
def normalize_drug_name():
    """标准化药品名称"""
    name = request.args.get('name', '')
    
    if not name:
        return jsonify({
            'code': 400,
            'message': '请提供药品名称'
        }), 400
    
    from app.services.normalize_service import NormalizeService
    service = NormalizeService()
    
    normalized = service.normalize_name(name)
    generic, brand = service.extract_generic_name(normalized)
    standard_generic = service.get_generic_name(name)
    aliases = service.get_all_aliases(standard_generic)
    
    return jsonify({
        'code': 0,
        'data': {
            'original': name,
            'normalized': normalized,
            'generic_name': generic,
            'brand_name': brand,
            'standard_generic': standard_generic,
            'aliases': aliases
        }
    })


@api_bp.route('/normalize/find-similar')
def find_similar_drugs():
    """查找相似药品"""
    name = request.args.get('name', '')
    
    if not name:
        return jsonify({
            'code': 400,
            'message': '请提供药品名称'
        }), 400
    
    from app.services.normalize_service import NormalizeService
    from app.services.price_service import PriceService
    
    normalize = NormalizeService()
    price_service = PriceService()
    
    # 搜索药品
    result = price_service.search_drugs(name, per_page=50)
    drugs = result.get('drugs', [])
    
    # 查找相似药品
    similar = normalize.find_similar_drugs(name, drugs)
    
    return jsonify({
        'code': 0,
        'data': {
            'query': name,
            'generic_name': normalize.get_generic_name(name),
            'similar_drugs': similar,
            'total': len(similar)
        }
    })


# ==================== 采集任务API ====================

@api_bp.route('/crawl/watch-list', methods=['GET'])
def get_watch_list():
    """获取药品监控列表"""
    category = request.args.get('category')
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    
    from app.services.crawl_service import CrawlService
    service = CrawlService()
    watch_list = service.get_watch_list(category=category, active_only=active_only)
    categories = service.get_categories()
    
    return jsonify({
        'code': 0,
        'data': watch_list,
        'categories': categories,
        'total': len(watch_list)
    })


@api_bp.route('/crawl/watch-list', methods=['POST'])
def add_to_watch_list():
    """添加药品到监控列表"""
    data = request.get_json() or {}
    
    # 支持单个或批量添加
    keywords = data.get('keywords', [])
    keyword = data.get('keyword')
    category = data.get('category')
    priority = data.get('priority', 0)
    
    from app.services.crawl_service import CrawlService
    service = CrawlService()
    
    if keyword:
        # 单个添加
        item = service.add_to_watch_list(keyword, category, priority)
        return jsonify({
            'code': 0,
            'message': f'已添加: {keyword}',
            'data': item.to_dict()
        })
    elif keywords:
        # 批量添加
        count = service.add_batch_to_watch_list(keywords, category)
        return jsonify({
            'code': 0,
            'message': f'已添加 {count} 个药品',
            'count': count
        })
    else:
        return jsonify({
            'code': 400,
            'message': '请提供药品关键词'
        }), 400


@api_bp.route('/crawl/watch-list/<int:item_id>', methods=['DELETE'])
def remove_from_watch_list(item_id: int):
    """从监控列表移除"""
    from app.services.crawl_service import CrawlService
    service = CrawlService()
    success = service.remove_from_watch_list(item_id)
    
    return jsonify({
        'code': 0 if success else 404,
        'message': '已移除' if success else '未找到该项'
    })


@api_bp.route('/crawl/tasks', methods=['GET'])
def get_crawl_tasks():
    """获取采集任务列表"""
    status = request.args.get('status')
    limit = request.args.get('limit', 20, type=int)
    
    from app.services.crawl_service import CrawlService
    service = CrawlService()
    tasks = service.get_crawl_tasks(status=status, limit=limit)
    
    return jsonify({
        'code': 0,
        'data': tasks,
        'total': len(tasks)
    })


@api_bp.route('/crawl/tasks', methods=['POST'])
def create_crawl_task():
    """创建采集任务"""
    data = request.get_json() or {}
    keywords = data.get('keywords', [])
    task_name = data.get('task_name')
    use_watch_list = data.get('use_watch_list', False)
    category = data.get('category')
    
    from app.services.crawl_service import CrawlService
    service = CrawlService()
    
    try:
        task = service.create_crawl_task(
            keywords=keywords if keywords else None,
            task_name=task_name,
            use_watch_list=use_watch_list,
            category=category
        )
        return jsonify({
            'code': 0,
            'message': '任务已创建',
            'data': task.to_dict()
        })
    except ValueError as e:
        return jsonify({
            'code': 400,
            'message': str(e)
        }), 400


@api_bp.route('/crawl/tasks/<int:task_id>')
def get_crawl_task(task_id: int):
    """获取采集任务详情"""
    from app.services.crawl_service import CrawlService
    service = CrawlService()
    task = service.get_crawl_task(task_id)
    
    if not task:
        return jsonify({
            'code': 404,
            'message': '任务不存在'
        }), 404
    
    return jsonify({
        'code': 0,
        'data': task
    })


@api_bp.route('/crawl/tasks/<int:task_id>/start', methods=['POST'])
def start_crawl_task(task_id: int):
    """启动采集任务"""
    from app.services.crawl_service import CrawlService
    service = CrawlService()
    success = service.start_crawl_task(task_id, async_mode=True)
    
    return jsonify({
        'code': 0 if success else 400,
        'message': '任务已启动' if success else '无法启动任务（可能已在运行中或不存在）'
    })


@api_bp.route('/crawl/tasks/<int:task_id>/cancel', methods=['POST'])
def cancel_crawl_task(task_id: int):
    """取消采集任务"""
    from app.services.crawl_service import CrawlService
    service = CrawlService()
    success = service.cancel_crawl_task(task_id)
    
    return jsonify({
        'code': 0 if success else 400,
        'message': '任务已取消' if success else '无法取消任务'
    })


@api_bp.route('/crawl/quick', methods=['POST'])
def quick_crawl():
    """快速采集"""
    data = request.get_json() or {}
    keywords = data.get('keywords', [])
    max_pages = data.get('max_pages', 3)
    
    if not keywords:
        return jsonify({
            'code': 400,
            'message': '请提供药品关键词'
        }), 400
    
    from app.services.crawl_service import CrawlService
    service = CrawlService()
    result = service.quick_crawl(keywords, max_pages)
    
    return jsonify({
        'code': 0,
        'data': result
    })


@api_bp.route('/crawl/statistics')
def get_crawl_statistics():
    """获取采集统计"""
    from app.services.crawl_service import CrawlService
    service = CrawlService()
    stats = service.get_crawl_statistics()
    
    return jsonify({
        'code': 0,
        'data': stats
    })


# ==================== Token管理API ====================

@api_bp.route('/crawl/token/status')
def get_token_status():
    """检查Token状态"""
    from scraper.utils.token_manager import TokenManager
    manager = TokenManager()
    
    cached_token = manager._load_cached_token()
    if cached_token:
        valid = manager._verify_token(cached_token)
        return jsonify({
            'code': 0,
            'data': {
                'valid': valid,
                'has_token': True
            }
        })
    
    return jsonify({
        'code': 0,
        'data': {
            'valid': False,
            'has_token': False
        }
    })


@api_bp.route('/crawl/token/auto', methods=['POST'])
def auto_get_token():
    """自动获取Token（通过浏览器模拟登录）"""
    data = request.get_json() or {}
    phone = data.get('phone', '').strip()
    password = data.get('password', '').strip()
    
    if not phone or not password:
        return jsonify({
            'code': 400,
            'message': '请输入手机号和密码'
        }), 400
    
    try:
        from scraper.utils.auto_login import AutoLoginService
        service = AutoLoginService()
        success, message, result = service.login_and_get_token(phone, password, headless=True)
        
        if success:
            return jsonify({
                'code': 0,
                'message': message,
                'data': {'token': result.get('token', '')[:8] + '***'}  # 只返回部分token
            })
        else:
            return jsonify({
                'code': 400,
                'message': message
            }), 400
    except ImportError:
        return jsonify({
            'code': 500,
            'message': '自动登录功能需要安装: pip install selenium webdriver-manager'
        }), 500
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'登录失败: {str(e)}'
        }), 500


@api_bp.route('/crawl/token/manual', methods=['POST'])
def save_manual_token():
    """手动保存Token（直接保存，不验证）"""
    data = request.get_json() or {}
    token = data.get('token', '').strip()
    
    if not token:
        return jsonify({
            'code': 400,
            'message': '请输入Token'
        }), 400
    
    # 从Cookie字符串中提取Token
    if 'Token=' in token:
        # 用户粘贴的是完整Cookie字符串
        import re
        match = re.search(r'Token=([a-zA-Z0-9]+)', token)
        if match:
            token = match.group(1)
    
    # 直接保存，不验证（因为验证可能因为各种原因失败）
    from scraper.utils.token_manager import TokenManager
    manager = TokenManager()
    manager._save_token(token)
    
    return jsonify({
        'code': 0,
        'message': f'Token已保存！（{token[:8]}...）'
    })


# ==================== Playwright采集API ====================

@api_bp.route('/crawl/playwright', methods=['POST'])
def crawl_with_playwright():
    """使用Playwright采集供应商价格"""
    data = request.get_json() or {}
    keyword = data.get('keyword', '').strip()
    drug_id = data.get('drug_id')
    max_providers = data.get('max_providers', 50)
    
    if not keyword:
        return jsonify({
            'code': 400,
            'message': '请提供药品关键词'
        }), 400
    
    from app.services.crawl_service import CrawlService
    service = CrawlService()
    
    result = service.crawl_with_playwright(
        keyword=keyword,
        drug_id=drug_id,
        max_items=max_providers,
        save_to_db=True
    )
    
    return jsonify({
        'code': 0 if result.get('success') else 500,
        'data': result,
        'message': '采集成功' if result.get('success') else result.get('error', '采集失败')
    })


@api_bp.route('/crawl/playwright/search', methods=['POST'])
def playwright_search():
    """使用Playwright搜索并采集多个药品的供应商价格"""
    data = request.get_json() or {}
    keyword = data.get('keyword', '').strip()
    max_items = data.get('max_items', 10)
    
    if not keyword:
        return jsonify({
            'code': 400,
            'message': '请提供搜索关键词'
        }), 400
    
    try:
        from scraper.utils.playwright_crawler import search_and_crawl_sync
        from app.services.crawl_service import CrawlService
        
        service = CrawlService()
        token = service._get_cached_token()
        
        result = search_and_crawl_sync(
            keyword=keyword,
            token=token,
            max_items=max_items,
            headless=True
        )
        
        # 保存到数据库
        if result.get('success'):
            saved_count = service._save_playwright_results(result, keyword)
            result['saved_count'] = saved_count
        
        return jsonify({
            'code': 0 if result.get('success') else 500,
            'data': result,
            'message': '搜索成功' if result.get('success') else result.get('error', '搜索失败')
        })
    except ImportError:
        return jsonify({
            'code': 500,
            'message': 'Playwright 未安装，请运行: pip install playwright && playwright install chromium'
        }), 500


@api_bp.route('/crawl/quick', methods=['POST'])
def crawl_quick_mode():
    """
    快速模式：仅使用 API 获取热销商品价格
    
    适用场景：
    - 快速查询价格参考
    - 批量采集大量药品
    - 对数据完整性要求不高
    
    特点：速度快（1-3秒），获取热销供应商价格（1-10个）
    """
    data = request.get_json() or {}
    keyword = data.get('keyword', '').strip()
    drug_id = data.get('drug_id')
    
    if not keyword and not drug_id:
        return jsonify({
            'code': 400,
            'message': '请提供药品关键词或药品ID'
        }), 400
    
    try:
        from app.services.crawl_service import CrawlService
        
        service = CrawlService()
        result = service.crawl_quick_mode(
            keyword=keyword or '',
            drug_id=drug_id,
            save_to_db=True
        )
        
        return jsonify({
            'code': 0 if result.get('success') else 500,
            'data': result,
            'message': '快速采集成功' if result.get('success') else result.get('error', '未找到数据')
        })
    except Exception as e:
        logger.error(f"快速采集异常: {e}")
        return jsonify({
            'code': 500,
            'message': f'采集异常: {str(e)}'
        }), 500


@api_bp.route('/crawl/complete', methods=['POST'])
def crawl_complete_mode():
    """
    完整模式：使用 Playwright 获取所有供应商价格
    
    适用场景：
    - 需要完整的供应商价格数据
    - 重要药品的采购决策
    - 价格对比分析
    
    特点：数据完整（50-100个供应商），速度较慢（10-30秒）
    """
    data = request.get_json() or {}
    keyword = data.get('keyword', '').strip()
    drug_id = data.get('drug_id')
    
    if not keyword and not drug_id:
        return jsonify({
            'code': 400,
            'message': '请提供药品关键词或药品ID'
        }), 400
    
    try:
        from app.services.crawl_service import CrawlService
        
        service = CrawlService()
        result = service.crawl_complete_mode(
            keyword=keyword or '',
            drug_id=drug_id,
            save_to_db=True
        )
        
        return jsonify({
            'code': 0 if result.get('success') else 500,
            'data': result,
            'message': '完整采集成功' if result.get('success') else result.get('error', '采集失败')
        })
    except Exception as e:
        logger.error(f"完整采集异常: {e}")
        return jsonify({
            'code': 500,
            'message': f'采集异常: {str(e)}'
        }), 500


@api_bp.route('/crawl/smart', methods=['POST'])
def crawl_with_smart_strategy():
    """
    智能采集：API 优先，Playwright 作为备选（推荐）
    
    这是最优的采集方式：
    1. 优先使用快速的 API 采集
    2. 如果 API 数据不足，自动使用 Playwright 补充
    3. 自动保存到数据库
    """
    data = request.get_json() or {}
    keyword = data.get('keyword', '').strip()
    drug_id = data.get('drug_id')
    force_playwright = data.get('force_playwright', False)
    min_providers = data.get('min_providers', 5)
    
    if not keyword and not drug_id:
        return jsonify({
            'code': 400,
            'message': '请提供药品关键词或药品ID'
        }), 400
    
    try:
        from app.services.crawl_service import CrawlService
        
        service = CrawlService()
        result = service.crawl_with_smart_strategy(
            keyword=keyword or '',
            drug_id=drug_id,
            force_playwright=force_playwright,
            min_providers=min_providers,
            save_to_db=True
        )
        
        return jsonify({
            'code': 0 if result.get('success') else 500,
            'data': result,
            'message': '采集成功' if result.get('success') else result.get('error', '采集失败')
        })
    except Exception as e:
        logger.error(f"智能采集异常: {e}")
        return jsonify({
            'code': 500,
            'message': f'采集异常: {str(e)}'
        }), 500


@api_bp.route('/crawl/playwright/detail', methods=['POST'])
def playwright_drug_detail():
    """使用Playwright获取单个药品的所有供应商价格（推荐）"""
    data = request.get_json() or {}
    keyword = data.get('keyword', '').strip()
    drug_id = data.get('drug_id')
    max_providers = data.get('max_providers', 100)
    
    if not keyword and not drug_id:
        return jsonify({
            'code': 400,
            'message': '请提供药品关键词或药品ID'
        }), 400
    
    try:
        from scraper.utils.playwright_crawler import crawl_drug_detail_sync
        from app.services.crawl_service import CrawlService
        
        service = CrawlService()
        token = service._get_cached_token()
        
        result = crawl_drug_detail_sync(
            keyword=keyword or '',
            drug_id=drug_id,
            token=token,
            max_providers=max_providers,
            headless=True
        )
        
        # 保存到数据库
        if result.get('success'):
            saved_count = service._save_playwright_results(result, keyword)
            result['saved_count'] = saved_count
        
        return jsonify({
            'code': 0 if result.get('success') else 500,
            'data': result,
            'message': '获取成功' if result.get('success') else result.get('error', '获取失败')
        })
    except ImportError:
        return jsonify({
            'code': 500,
            'message': 'Playwright 未安装，请运行: pip install playwright && playwright install chromium'
        }), 500


@api_bp.route('/crawl/batch-search', methods=['POST'])
def crawl_batch_search():
    """
    批量采集：采集搜索结果中的所有药品
    
    适用场景：
    - 想要获取某个品类的所有药品数据
    - 比如搜索"天麻蜜环菌片"，获取所有品牌/规格的数据
    
    请求参数：
    - keyword: 搜索关键词（必填）
    - max_drugs: 最多采集多少个药品（默认10）
    - max_providers_per_drug: 每个药品最多采集多少个供应商（默认50）
    
    返回：
    - total_drugs: 采集的药品总数
    - total_providers: 采集的供应商总数
    - total_saved: 保存的记录总数
    - drugs: 每个药品的详细信息
    """
    data = request.get_json() or {}
    keyword = data.get('keyword', '').strip()
    max_drugs = data.get('max_drugs', 10)
    max_providers_per_drug = data.get('max_providers_per_drug', 50)
    
    if not keyword:
        return jsonify({
            'code': 400,
            'message': '请提供搜索关键词'
        }), 400
    
    # 限制最大值，避免采集时间过长
    if max_drugs > 50:
        max_drugs = 50
    if max_providers_per_drug > 200:
        max_providers_per_drug = 200
    
    try:
        from app.services.crawl_service import CrawlService
        
        service = CrawlService()
        result = service.crawl_all_search_results(
            keyword=keyword,
            max_drugs=max_drugs,
            max_providers_per_drug=max_providers_per_drug,
            save_to_db=True
        )
        
        return jsonify({
            'code': 0 if result.get('success') else 500,
            'data': result,
            'message': f"批量采集完成：{result.get('total_drugs', 0)}个药品，{result.get('total_providers', 0)}个供应商" if result.get('success') else result.get('error', '采集失败')
        })
    except Exception as e:
        logger.error(f"批量采集异常: {e}")
        return jsonify({
            'code': 500,
            'message': f'采集异常: {str(e)}'
        }), 500
