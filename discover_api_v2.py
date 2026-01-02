#!/usr/bin/env python3
"""
使用 Playwright 发现 API 接口 - 增强版

目的：拦截浏览器请求，找到获取供应商价格的正确 API
"""
import asyncio
import json
import logging
from scraper.utils.playwright_crawler import YSBangPlaywrightCrawler

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

async def discover_api():
    """发现 API 接口"""
    keyword = '天麻蜜环菌片'
    
    print('='*70)
    print('🔍 使用 Playwright 发现 API 接口')
    print('='*70)
    print(f'药品: {keyword}')
    print('-'*70)
    
    crawler = YSBangPlaywrightCrawler(headless=True)
    
    # 执行采集（会拦截 API）
    logger.info("开始采集，拦截 API 请求...")
    result = await crawler.get_drug_provider_prices(keyword)
    
    logger.info(f"采集完成，拦截到 {len(crawler._api_responses)} 个 API 请求")
    
    # 分析拦截到的 API
    print('\n📡 拦截到的 API 请求:')
    print('-'*70)
    
    if not crawler._api_responses:
        print('⚠️  没有拦截到任何 API 请求')
        print('可能原因:')
        print('  1. Token 失效')
        print('  2. 页面加载失败')
        print('  3. API 拦截器未正常工作')
        await crawler._close_browser()
        return
    
    # 按 API 类型分组
    api_groups = {}
    for resp in crawler._api_responses:
        url = resp['url']
        
        # 提取 API 名称
        api_name = 'unknown'
        for pattern in ['getWholesaleListForPc', 'facetWholesaleList', 
                       'getRegularSearchPurchaseList', 'getHotWholesalesForProvider',
                       'getDrugDetail']:
            if pattern in url:
                api_name = pattern
                break
        
        if api_name not in api_groups:
            api_groups[api_name] = []
        api_groups[api_name].append(resp)
    
    # 显示每个 API 的信息
    for api_name, responses in api_groups.items():
        print(f'\n📌 {api_name}')
        print(f'   调用次数: {len(responses)}')
        
        # 显示第一个请求的详细信息
        if responses:
            first = responses[0]
            url = first['url']
            data = first['data']
            
            print(f'   URL: {url[:100]}...')
            
            # 分析返回数据
            result_data = data.get('data', {})
            
            if isinstance(result_data, list):
                print(f'   返回: 列表，{len(result_data)} 条')
                if result_data and len(result_data) > 0:
                    print(f'   字段: {list(result_data[0].keys())[:8]}...')
            elif isinstance(result_data, dict):
                print(f'   返回: 字典')
                print(f'   字段: {list(result_data.keys())}')
                
                # 检查嵌套的列表
                for key in ['list', 'wholesales', 'items', 'records']:
                    if key in result_data:
                        items = result_data[key]
                        if isinstance(items, list):
                            print(f'   └─ {key}: {len(items)} 条')
                            if items:
                                print(f'      字段: {list(items[0].keys())[:8]}...')
    
    # 重点分析 getWholesaleListForPc
    print('\n' + '='*70)
    print('🎯 重点分析: getWholesaleListForPc（供应商价格列表）')
    print('='*70)
    
    if 'getWholesaleListForPc' in api_groups:
        responses = api_groups['getWholesaleListForPc']
        print(f'\n找到 {len(responses)} 个 getWholesaleListForPc 请求')
        
        for i, resp in enumerate(responses[:3], 1):
            url = resp['url']
            data = resp['data']
            
            print(f'\n请求 {i}:')
            print(f'URL: {url}')
            
            # 提取查询参数
            if '?' in url:
                query = url.split('?')[1]
                print(f'参数: {query}')
            
            # 分析数据
            result_data = data.get('data', {})
            if isinstance(result_data, dict):
                if 'list' in result_data:
                    items = result_data['list']
                    print(f'供应商数: {len(items)}')
                    
                    if items:
                        print(f'\n供应商数据示例:')
                        item = items[0]
                        print(json.dumps(item, ensure_ascii=False, indent=2)[:500])
                        
                        print(f'\n关键字段:')
                        for key in ['drugname', 'price', 'abbreviation', 'providerId', 
                                   'specification', 'manufacturer', 'wholesaleid']:
                            if key in item:
                                print(f'  {key}: {item[key]}')
    else:
        print('\n⚠️  未找到 getWholesaleListForPc API')
        print('可能需要:')
        print('  1. 滚动页面加载更多')
        print('  2. 点击查看更多供应商')
        print('  3. 检查 API 拦截器配置')
    
    await crawler._close_browser()
    
    print('\n' + '='*70)
    print('💡 下一步')
    print('='*70)
    print('1. 找到了 API 接口和参数')
    print('2. 实现纯 API 调用')
    print('3. 替换 Playwright 采集')
    print('='*70)

if __name__ == '__main__':
    asyncio.run(discover_api())
