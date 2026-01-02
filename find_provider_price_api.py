#!/usr/bin/env python3
"""
寻找获取单个供应商价格的 API

策略：
1. 先获取药品的 drugId
2. 再获取该药品的所有供应商价格
"""
import requests
import json

def get_token():
    """获取 Token"""
    try:
        with open('.token_cache.json', 'r') as f:
            cache = json.load(f)
            return cache.get('token', '')
    except:
        return ''

def test_provider_price_api():
    """测试获取供应商价格的 API"""
    
    token = get_token()
    if not token:
        print('❌ 无法读取 Token')
        return
    
    keyword = '天麻蜜环菌片'
    
    print('='*70)
    print('🔍 寻找获取供应商价格的 API')
    print('='*70)
    print(f'药品: {keyword}')
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
    
    # 步骤1: 获取药品信息（包含 drugId）
    print('\n步骤1: 获取药品信息')
    print('-'*70)
    
    url1 = 'https://dian.ysbang.cn/wholesale-drug/sales/getRegularSearchPurchaseListForPc/v5430'
    body1 = {'keyword': keyword, 'page': 1, 'pageSize': 10}
    
    try:
        resp1 = requests.post(url1, json=body1, headers=headers, cookies=cookies, timeout=15)
        data1 = resp1.json()
        
        if data1.get('code') in ['0', 0, '40001']:
            items = data1.get('data', [])
            if items:
                # 取第一个药品
                first_item = items[0]
                drug = first_item.get('drug', {})
                drug_id = drug.get('drugId')
                drug_name = drug.get('drugName', '')
                min_price = drug.get('minprice', '')
                max_price = drug.get('maxprice', '')
                wholesale_num = drug.get('wholesaleNum', 0)
                
                print(f'✅ 找到药品:')
                print(f'   drugId: {drug_id}')
                print(f'   名称: {drug_name}')
                print(f'   价格范围: ¥{min_price} - ¥{max_price}')
                print(f'   供应商数: {wholesale_num}')
                
                # 步骤2: 使用 drugId 获取供应商列表
                print(f'\n步骤2: 获取该药品的所有供应商价格')
                print('-'*70)
                
                # 尝试多个可能的 API
                test_apis = [
                    {
                        'name': 'getWholesaleListForPc (带drugId)',
                        'url': 'https://dian.ysbang.cn/wholesale-drug/sales/getWholesaleListForPc',
                        'body': {'drugId': drug_id, 'page': 1, 'pageSize': 100}
                    },
                    {
                        'name': 'facetWholesaleList (带drugId)',
                        'url': 'https://dian.ysbang.cn/wholesale-drug/sales/facetWholesaleList/v4270',
                        'body': {'drugId': drug_id}
                    },
                    {
                        'name': 'getWholesalesByDrugId',
                        'url': 'https://dian.ysbang.cn/wholesale-drug/sales/getWholesalesByDrugId',
                        'body': {'drugId': drug_id, 'page': 1, 'pageSize': 100}
                    },
                    {
                        'name': 'getDrugWholesales',
                        'url': 'https://dian.ysbang.cn/wholesale-drug/sales/getDrugWholesales',
                        'body': {'drugId': drug_id, 'page': 1, 'pageSize': 100}
                    },
                ]
                
                for test in test_apis:
                    print(f'\n📡 测试: {test["name"]}')
                    print(f'   URL: {test["url"]}')
                    
                    try:
                        resp = requests.post(
                            test['url'],
                            json=test['body'],
                            headers=headers,
                            cookies=cookies,
                            timeout=15
                        )
                        
                        if resp.status_code == 404:
                            print(f'   ❌ 404 Not Found')
                            continue
                        
                        data = resp.json()
                        code = data.get('code')
                        message = data.get('message', '')
                        
                        print(f'   状态: {resp.status_code}, code: {code}')
                        
                        if code in ['0', 0, '40001']:
                            result = data.get('data', {})
                            
                            if isinstance(result, list):
                                print(f'   ✅ 返回列表: {len(result)} 条')
                                if result and 'price' in result[0]:
                                    print(f'   ✅✅ 找到供应商价格！')
                                    print(f'   示例: {result[0].get("drugname", "")}: ¥{result[0].get("price", 0)}')
                                    print(f'   供应商: {result[0].get("abbreviation", "")}')
                                    return  # 找到了！
                            
                            elif isinstance(result, dict):
                                print(f'   ✅ 返回字典: {list(result.keys())}')
                                
                                # 检查嵌套列表
                                for key in ['list', 'wholesales', 'items', 'records']:
                                    if key in result:
                                        items = result[key]
                                        if isinstance(items, list) and items:
                                            print(f'   └─ {key}: {len(items)} 条')
                                            if 'price' in items[0]:
                                                print(f'   ✅✅ 找到供应商价格！')
                                                print(f'   示例: {items[0].get("drugname", "")}: ¥{items[0].get("price", 0)}')
                                                print(f'   供应商: {items[0].get("abbreviation", "")}')
                                                
                                                # 显示更多示例
                                                print(f'\n   前5个供应商:')
                                                for i, item in enumerate(items[:5], 1):
                                                    print(f'   {i}. {item.get("abbreviation", "未知")}: ¥{item.get("price", 0)}')
                                                return  # 找到了！
                        else:
                            print(f'   ❌ 错误: {message}')
                            
                    except Exception as e:
                        print(f'   ❌ 异常: {e}')
                
                print(f'\n❌ 未找到获取供应商价格的 API')
                
    except Exception as e:
        print(f'❌ 步骤1失败: {e}')
    
    print('\n' + '='*70)

if __name__ == '__main__':
    test_provider_price_api()
