#!/usr/bin/env python3
"""
使用 Playwright 发现 API 接口

目的：拦截浏览器请求，找到获取供应商价格的正确 API
"""
import asyncio
import json
from scraper.utils.playwright_crawler import YSBangPlaywrightCrawler

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
    result = await crawler.get_drug_provider_prices(keyword)
    
    # 分析拦截到的 API
    print('\n📡 拦截到的 API 请求:')
    print('-'*70)
    
    api_summary = {}
    for resp in crawler._api_responses:
        url = resp['url']
        
        # 提取 API 名称
        if 'getWholesaleListForPc' in url:
            api_name = 'getWholesaleListForPc'
        elif 'facetWholesaleList' in url:
            api_name = 'facetWholesaleList'
        elif 'getRegularSearchPurchaseList' in url:
            api_name = 'getRegularSearchPurchaseList'
        elif 'getHotWholesalesForProvider' in url:
            api_name = 'getHotWholesalesForProvider'
        else:
            api_name = 'other'
        
        if api_name not in api_summary:
            api_summary[api_name] = {
                'count': 0,
                'urls': [],
                'sample_data': None
            }
        
        api_summary[api_name]['count'] += 1
        if len(api_summary[api_name]['urls']) < 2:
            api_summary[api_name]['urls'].append(url)
        if not api_summary[api_name]['sample_data']:
            api_summary[api_name]['sample_data'] = resp['data']
    
    # 显示 API 摘要
    for api_name, info in api_summary.items():
        print(f'\n{api_name}:')
        print(f'  调用次数: {info["count"]}')
        print(f'  示例URL: {info["urls"][0] if info["urls"] else "N/A"}')
        
        # 分析数据结构
        if info['sample_data']:
            data = info['sample_data']
            result_data = data.get('data', {})
            
            if isinstance(result_data, list):
                print(f'  返回数据: 列表，{len(result_data)} 条记录')
                if result_data:
                    print(f'  数据示例: {list(result_data[0].keys())[:10]}')
            elif isinstance(result_data, dict):
                print(f'  返回数据: 字典')
                print(f'  字段: {list(result_data.keys())}')
                
                # 检查是否有供应商列表
                if 'list' in result_data:
                    items = result_data['list']
                    print(f'  供应商数量: {len(items)}')
                    if items:
                        print(f'  供应商字段: {list(items[0].keys())[:10]}')
    
    # 重点分析 getWholesaleListForPc
    print('\n' + '='*70)
    print('🎯 重点分析: getWholesaleListForPc（供应商价格列表）')
    print('='*70)
    
    if 'getWholesaleListForPc' in api_summary:
        sample = api_summary['getWholesaleListForPc']['sample_data']
        url = api_summary['getWholesaleListForPc']['urls'][0]
        
        print(f'\nAPI URL: {url}')
        
        # 提取请求参数
        if '?' in url:
            params_str = url.split('?')[1]
            print(f'\n请求参数: {params_str}')
        
        # 分析响应数据
        result_data = sample.get('data', {})
        if isinstance(result_data, dict) and 'list' in result_data:
            items = result_data['list']
            print(f'\n返回供应商数: {len(items)}')
            
            if items:
                print(f'\n供应商数据结构:')
                item = items[0]
                for key, value in list(item.items())[:15]:
                    print(f'  {key}: {value}')
                
                print(f'\n完整字段列表:')
                print(f'  {list(item.keys())}')
    
    await crawler._close_browser()
    
    print('\n' + '='*70)
    print('💡 结论')
    print('='*70)
    print('找到了获取供应商价格的 API: getWholesaleListForPc')
    print('下一步: 实现纯 API 调用，不再依赖 Playwright')
    print('='*70)

if __name__ == '__main__':
    asyncio.run(discover_api())
