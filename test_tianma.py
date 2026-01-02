#!/usr/bin/env python3
"""
测试天麻蜜环菌片的智能采集
"""
from app.services.crawl_service import CrawlService
import json

print('='*70)
print('🧠 智能采集测试：天麻蜜环菌片')
print('='*70)

service = CrawlService()

# 执行智能采集
print('\n开始采集...')
result = service.crawl_with_smart_strategy(
    keyword='天麻蜜环菌片',
    min_providers=5,
    save_to_db=False  # 测试时不保存
)

# 显示结果
print('\n' + '='*70)
print('📊 采集结果')
print('='*70)
print(f'成功: {"✅" if result["success"] else "❌"}')
print(f'采集方法: {result["method"]}')
print(f'API 采集: {result["api_count"]} 个供应商')
print(f'Playwright 补充: {result["playwright_count"]} 个供应商')
print(f'总计: {len(result["providers"])} 个供应商')

if result.get('error'):
    print(f'错误信息: {result["error"]}')

# 显示供应商价格
if result['providers']:
    print('\n' + '='*70)
    print('💰 供应商价格列表（按价格排序）')
    print('='*70)
    
    # 按价格排序
    providers = sorted(result['providers'], key=lambda x: x.get('price', 0))
    
    for i, p in enumerate(providers[:15], 1):
        source = p.get('source', 'unknown')
        source_tag = f'[{source.upper()}]'
        price = p.get('price', 0)
        provider_name = p.get('provider_name', '未知')
        drug_name = p.get('drug_name', '')
        
        print(f'{i:2d}. {provider_name:25s} ¥{price:8.2f} {source_tag:8s} {drug_name[:30]}')
    
    if len(providers) > 15:
        print(f'\n... 还有 {len(providers) - 15} 个供应商')
    
    # 价格统计
    if providers:
        prices = [p.get('price', 0) for p in providers if p.get('price', 0) > 0]
        if prices:
            print('\n' + '='*70)
            print('📈 价格统计')
            print('='*70)
            print(f'最低价: ¥{min(prices):.2f}')
            print(f'最高价: ¥{max(prices):.2f}')
            print(f'平均价: ¥{sum(prices)/len(prices):.2f}')
            print(f'价差: ¥{max(prices) - min(prices):.2f}')

print('\n' + '='*70)
