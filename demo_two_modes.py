#!/usr/bin/env python3
"""
两种模式对比演示

展示快速模式和完整模式的区别和应用场景
"""
import time
from app.services.crawl_service import CrawlService

def demo_two_modes():
    """对比两种模式"""
    service = CrawlService()
    keyword = '天麻蜜环菌片'
    
    print('\n' + '='*70)
    print('🎯 两种采集模式对比演示')
    print('='*70)
    print(f'测试药品: {keyword}')
    print('='*70)
    
    # 模式1: 快速模式
    print('\n⚡ 模式1: 快速模式（API 热销价格）')
    print('-'*70)
    print('适用场景: 快速查询、批量采集、日常使用')
    print('特点: 速度快、资源占用低')
    print('-'*70)
    
    start = time.time()
    quick_result = service.crawl_quick_mode(
        keyword=keyword,
        save_to_db=False
    )
    quick_time = time.time() - start
    
    print(f'\n结果:')
    print(f'  成功: {"✅" if quick_result["success"] else "❌"}')
    print(f'  耗时: {quick_time:.2f} 秒')
    print(f'  供应商数: {len(quick_result["providers"])}')
    print(f'  数据来源: API（热销商品）')
    
    if quick_result['providers']:
        providers = sorted(quick_result['providers'], key=lambda x: x.get('price', 0))
        print(f'\n  前5个供应商:')
        for i, p in enumerate(providers[:5], 1):
            print(f'    {i}. {p["provider_name"]}: ¥{p["price"]:.2f}')
    
    if quick_result.get('error'):
        print(f'  提示: {quick_result["error"]}')
    
    # 模式2: 完整模式
    print('\n' + '='*70)
    print('📊 模式2: 完整模式（所有供应商价格）')
    print('-'*70)
    print('适用场景: 重要决策、价格对比、完整分析')
    print('特点: 数据完整、速度较慢')
    print('-'*70)
    
    start = time.time()
    complete_result = service.crawl_complete_mode(
        keyword=keyword,
        save_to_db=False
    )
    complete_time = time.time() - start
    
    print(f'\n结果:')
    print(f'  成功: {"✅" if complete_result["success"] else "❌"}')
    print(f'  耗时: {complete_time:.2f} 秒')
    print(f'  供应商数: {len(complete_result["providers"])}')
    print(f'  数据来源: Playwright（页面完整数据）')
    
    if complete_result['providers']:
        providers = sorted(complete_result['providers'], key=lambda x: x.get('price', 0))
        print(f'\n  前5个供应商:')
        for i, p in enumerate(providers[:5], 1):
            print(f'    {i}. {p["provider_name"]}: ¥{p["price"]:.2f}')
        
        # 价格统计
        prices = [p['price'] for p in providers if p.get('price', 0) > 0]
        if prices:
            print(f'\n  价格统计:')
            print(f'    最低: ¥{min(prices):.2f}')
            print(f'    最高: ¥{max(prices):.2f}')
            print(f'    平均: ¥{sum(prices)/len(prices):.2f}')
            print(f'    价差: ¥{max(prices) - min(prices):.2f}')
    
    # 对比总结
    print('\n' + '='*70)
    print('📊 对比总结')
    print('='*70)
    
    print(f'\n{"指标":<20} {"快速模式":<25} {"完整模式":<25}')
    print('-'*70)
    print(f'{"耗时":<20} {f"{quick_time:.2f}秒":<25} {f"{complete_time:.2f}秒":<25}')
    print(f'{"供应商数":<20} {f"{len(quick_result["providers"])}个":<25} {f"{len(complete_result["providers"])}个":<25}')
    print(f'{"数据来源":<20} {"API（热销）":<25} {"Playwright（完整）":<25}')
    print(f'{"速度":<20} {"⭐⭐⭐⭐⭐":<25} {"⭐⭐":<25}')
    print(f'{"完整性":<20} {"⭐⭐⭐":<25} {"⭐⭐⭐⭐⭐":<25}')
    print(f'{"资源占用":<20} {"⭐":<25} {"⭐⭐⭐⭐⭐":<25}')
    
    # 应用场景建议
    print('\n' + '='*70)
    print('💡 应用场景建议')
    print('='*70)
    
    print('\n⚡ 快速模式适用于:')
    print('  1. 日常价格查询')
    print('  2. 批量采集大量药品')
    print('  3. 快速了解市场行情')
    print('  4. 对数据完整性要求不高的场景')
    print('  5. 需要高频率采集的场景')
    
    print('\n📊 完整模式适用于:')
    print('  1. 重要药品的采购决策')
    print('  2. 需要完整价格对比分析')
    print('  3. 寻找最优供应商')
    print('  4. 价格趋势分析')
    print('  5. 对数据完整性要求高的场景')
    
    print('\n🧠 智能模式（推荐）:')
    print('  自动根据数据量选择最优方案')
    print('  - 数据充足时使用快速模式')
    print('  - 数据不足时自动切换完整模式')
    print('  - 适合大多数场景')
    
    print('\n' + '='*70)
    print('🎯 价值体现')
    print('='*70)
    
    quick_count = len(quick_result['providers'])
    complete_count = len(complete_result['providers'])
    
    if quick_count > 0:
        print(f'\n✅ 快速模式: {quick_time:.1f}秒获取{quick_count}个热销供应商价格')
        print(f'   价值: 快速决策、批量采集、日常查询')
    else:
        print(f'\n⚠️  快速模式: 未找到热销商品价格')
        print(f'   建议: 使用完整模式或智能模式')
    
    if complete_count > 0:
        print(f'\n✅ 完整模式: {complete_time:.1f}秒获取{complete_count}个供应商完整价格')
        print(f'   价值: 完整对比、最优选择、重要决策')
        
        if quick_count > 0:
            coverage = (quick_count / complete_count) * 100
            print(f'\n📈 数据覆盖率: 快速模式覆盖了 {coverage:.1f}% 的供应商')
            if coverage >= 80:
                print(f'   结论: 快速模式已足够，无需完整模式')
            elif coverage >= 50:
                print(f'   结论: 快速模式可用，完整模式更佳')
            else:
                print(f'   结论: 建议使用完整模式获取更多数据')
    
    print('\n' + '='*70)

if __name__ == '__main__':
    demo_two_modes()
