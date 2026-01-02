#!/usr/bin/env python3
"""
测试直接调用 getWholesaleListForPc API

根据药师帮网站的逻辑，搜索页面应该会调用这个 API 来获取供应商列表
"""
import requests
import json

def test_wholesale_list_api():
    """测试 getWholesaleListForPc API"""
    
    # 读取 Token
    try:
        with open('.token_cache.json', 'r') as f:
            cache = json.load(f)
            token = cache.get('token', '')
    except:
        print('❌ 无法读取 Token')
        return
    
    if not token:
        print('❌ Token 为空')
        return
    
    keyword = '天麻蜜环菌片'
    
    print('='*70)
    print('🧪 测试 getWholesaleListForPc API')
    print('='*70)
    print(f'药品: {keyword}')
    print(f'Token: {token[:20]}...')
    print('-'*70)
    
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
        'Origin': 'https://dian.ysbang.cn',
        'Referer': 'https://dian.ysbang.cn/',
        'Token': token,
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    cookies = {'Token': token}
    
    # 尝试不同的 API 端点和参数组合
    test_cases = [
        {
            'name': 'getWholesaleListForPc (基础)',
            'url': 'https://dian.ysbang.cn/wholesale-drug/sales/getWholesaleListForPc/v4270',
            'body': {'keyword': keyword, 'page': 1, 'pageSize': 100}
        },
        {
            'name': 'getWholesaleListForPc (带排序)',
            'url': 'https://dian.ysbang.cn/wholesale-drug/sales/getWholesaleListForPc/v4270',
            'body': {'keyword': keyword, 'page': 1, 'pageSize': 100, 'sortType': 1}
        },
        {
            'name': 'facetWholesaleList',
            'url': 'https://dian.ysbang.cn/wholesale-drug/sales/facetWholesaleList/v4270',
            'body': {'keyword': keyword}
        },
        {
            'name': 'getRegularSearchPurchaseListForPc',
            'url': 'https://dian.ysbang.cn/wholesale-drug/sales/getRegularSearchPurchaseListForPc/v5430',
            'body': {'keyword': keyword, 'page': 1, 'pageSize': 100}
        },
    ]
    
    for test in test_cases:
        print(f'\n📡 测试: {test["name"]}')
        print(f'URL: {test["url"]}')
        print(f'参数: {test["body"]}')
        
        try:
            resp = requests.post(
                test['url'],
                json=test['body'],
                headers=headers,
                cookies=cookies,
                timeout=15
            )
            
            data = resp.json()
            code = data.get('code')
            message = data.get('message', '')
            
            print(f'状态码: {resp.status_code}')
            print(f'返回code: {code}')
            print(f'返回message: {message}')
            
            if code in ['0', 0, '40001']:
                result = data.get('data', {})
                
                if isinstance(result, list):
                    print(f'✅ 返回列表: {len(result)} 条')
                    if result:
                        print(f'   字段: {list(result[0].keys())[:10]}')
                        # 检查是否有价格信息
                        if 'price' in result[0]:
                            print(f'   ✅ 包含价格字段')
                            print(f'   示例: {result[0].get("drugname", "")}: ¥{result[0].get("price", 0)}')
                
                elif isinstance(result, dict):
                    print(f'✅ 返回字典')
                    print(f'   字段: {list(result.keys())}')
                    
                    # 检查嵌套列表
                    for key in ['list', 'wholesales', 'items', 'records']:
                        if key in result:
                            items = result[key]
                            if isinstance(items, list):
                                print(f'   └─ {key}: {len(items)} 条')
                                if items:
                                    print(f'      字段: {list(items[0].keys())[:10]}')
                                    if 'price' in items[0]:
                                        print(f'      ✅ 包含价格字段')
                                        print(f'      示例: {items[0].get("drugname", "")}: ¥{items[0].get("price", 0)}')
            else:
                print(f'❌ API 返回错误: {message}')
                
        except Exception as e:
            print(f'❌ 请求失败: {e}')
    
    print('\n' + '='*70)
    print('💡 结论')
    print('='*70)
    print('找到能返回供应商价格的 API，就可以替换 Playwright')
    print('='*70)

if __name__ == '__main__':
    test_wholesale_list_api()
