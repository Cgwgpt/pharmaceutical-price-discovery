"""
Web路由定义
处理页面请求和渲染
"""
from flask import Blueprint, render_template, request, redirect, url_for
from app.services.price_service import PriceService

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """首页 - 显示最近爬取的药品价格"""
    service = PriceService()
    recent_prices = service.get_recent_prices(limit=20)
    stats = service.get_statistics()
    
    return render_template('index.html', 
                          prices=recent_prices,
                          stats=stats)


@main_bp.route('/drug/<int:drug_id>')
def drug_detail(drug_id: int):
    """药品详情页"""
    service = PriceService()
    drug = service.get_drug_by_id(drug_id)
    
    if not drug:
        return render_template('404.html'), 404
    
    prices = service.get_drug_prices(drug_id)
    history = service.get_price_history(drug_id, days=30)
    
    # 获取采购建议
    from app.services.recommendation_service import RecommendationService
    rec_service = RecommendationService()
    recommendation = rec_service.get_recommendation(drug['name'])
    
    return render_template('drug_detail.html',
                          drug=drug,
                          prices=prices,
                          history=history,
                          recommendation=recommendation)


@main_bp.route('/compare')
def compare():
    """比价页面"""
    drug_name = request.args.get('drug', '').strip()
    category = request.args.get('category', '').strip()  # drug, cosmetic, medical_device
    
    if not drug_name:
        return render_template('compare.html',
                              drug_name='',
                              comparison=None,
                              category='')
    
    from app.services.compare_service import CompareService
    service = CompareService()
    comparison = service.compare_prices(drug_name, category=category or None)
    
    return render_template('compare.html',
                          drug_name=drug_name,
                          comparison=comparison,
                          category=category)


@main_bp.route('/monitor')
def monitor():
    """价格监控页面"""
    threshold = request.args.get('threshold', 5.0, type=float)
    
    from app.services.monitor_service import MonitorService
    service = MonitorService()
    
    summary = service.get_daily_summary()
    alerts = service.get_price_alerts(threshold=threshold)
    
    return render_template('monitor.html',
                          summary=summary,
                          alerts=alerts,
                          threshold=threshold,
                          watch_list=[])


@main_bp.route('/crawl')
def crawl():
    """采集管理页面"""
    from app.services.crawl_service import CrawlService
    service = CrawlService()
    
    watch_list = service.get_watch_list()
    categories = service.get_categories()
    tasks = service.get_crawl_tasks(limit=10)
    statistics = service.get_crawl_statistics()
    
    return render_template('crawl.html',
                          watch_list=watch_list,
                          categories=categories,
                          tasks=tasks,
                          statistics=statistics)


@main_bp.route('/procurement')
def procurement():
    """采购建议页面"""
    drug_name = request.args.get('drug', '').strip()
    drug_id = request.args.get('drug_id', type=int)
    quantity = request.args.get('quantity', 1, type=int)
    
    recommendation = None
    provider_prices = None
    
    if drug_name:
        from app.services.recommendation_service import RecommendationService
        from app.services.price_service import PriceService
        
        rec_service = RecommendationService()
        price_service = PriceService()
        
        # 获取采购建议
        recommendation = rec_service.get_recommendation(drug_name, quantity)
        
        # 获取供应商价格列表
        if recommendation and recommendation.get('drug_id'):
            prices = price_service.get_drug_prices(recommendation['drug_id'])
            # 按价格排序，过滤出有供应商名称的记录
            provider_prices = sorted(
                [p for p in prices if '药师帮-' in p.get('source_name', '')],
                key=lambda x: x.get('price', 0)
            )
            # 转换格式
            provider_prices = [
                {
                    'provider_name': p['source_name'].replace('药师帮-', ''),
                    'price': p['price']
                }
                for p in provider_prices
            ]
    
    return render_template('procurement.html',
                          drug_name=drug_name,
                          drug_id=drug_id,
                          quantity=quantity,
                          recommendation=recommendation,
                          provider_prices=provider_prices)


@main_bp.route('/drugs')
def drugs_list():
    """已采集药品列表页面（统一的药品浏览和搜索入口）"""
    from app.services.price_service import PriceService
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    sort_by = request.args.get('sort', 'updated')  # updated, name, price_count
    keyword = request.args.get('q', '').strip()  # 搜索关键词
    view_mode = request.args.get('view', 'table')  # table or card
    
    service = PriceService()
    result = service.get_all_drugs_with_stats(
        page=page, 
        per_page=per_page, 
        sort_by=sort_by,
        keyword=keyword
    )
    
    return render_template('drugs_list.html', 
                         drugs=result['drugs'],
                         total=result['total'],
                         page=page,
                         pages=result['pages'],
                         sort_by=sort_by,
                         keyword=keyword,
                         view_mode=view_mode)


@main_bp.route('/search')
def search():
    """搜索页面 - 重定向到药品库"""
    keyword = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    
    # 重定向到药品库页面，使用卡片视图
    return redirect(url_for('main.drugs_list', q=keyword, page=page, view='card'))

