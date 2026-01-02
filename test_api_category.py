"""
测试药师帮API是否返回商品类别信息
"""
import requests
import json

def test_search_api():
    """测试搜索API返回的字段"""
    
    # 读取token
    with open('.token_cache.json', 'r') as f:
        token = json.load(f)['token']
    
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
        'Origin': 'https://dian.ysbang.cn',
        'Referer': 'https://dian.ysbang.cn/',
        'Token': token,
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    cookies = {'Token': token}
    
    # 测试搜索"片仔癀"
    url = 'https://dian.ysbang.cn/wholesale-drug/sales/getRegularSearchPurchaseListForPc/v5430'
    body = {'keyword': '片仔癀', 'page': 1, 'pageSize': 10}
    
    print("=" * 60)
    print("测试搜索API: 片仔癀")
    print("=" * 60)
    
    resp = requests.post(url, json=body, headers=headers, cookies=cookies, timeout=15)
    data = resp.json()
    
    if data.get('code') in ['0', 0]:
        items = data.get('data', [])
        if isinstance(items, dict):
            items = items.get('list', [])
        
        print(f"\n找到 {len(items)} 个商品\n")
        
        for i, item in enumerate(items[:5], 1):
            drug = item.get('drug', item)
            print(f"\n商品 {i}:")
            print(f"  名称: {drug.get('drugName')}")
            print(f"  规格: {drug.get('specification')}")
            print(f"  厂家: {drug.get('factory')}")
            print(f"  价格: ¥{drug.get('minprice')} ~ ¥{drug.get('maxprice')}")
            
            # 查找类别相关字段
            print(f"\n  所有字段:")
            for key, value in drug.items():
                if any(keyword in key.lower() for keyword in ['type', 'category', 'class', 'kind', '类', '型']):
                    print(f"    ⭐ {key}: {value}")
                elif key not in ['drugName', 'specification', 'factory', 'minprice', 'maxprice']:
                    print(f"    {key}: {value}")
    
    # 测试供应商热销商品API
    print("\n" + "=" * 60)
    print("测试供应商热销商品API")
    print("=" * 60)
    
    # 先获取一个供应商ID
    url2 = 'https://dian.ysbang.cn/wholesale-drug/sales/facetWholesaleListByProvider/v4270'
    body2 = {'keyword': '片仔癀', 'page': 1, 'pageSize': 1}
    resp2 = requests.post(url2, json=body2, headers=headers, cookies=cookies, timeout=15)
    data2 = resp2.json()
    
    if data2.get('code') in ['0', 0]:
        providers = data2.get('data', {}).get('providers', [])
        if providers:
            provider_id = providers[0].get('pid')
            provider_name = providers[0].get('name')
            
            print(f"\n测试供应商: {provider_name} (ID: {provider_id})")
            
            # 获取该供应商的热销商品
            url3 = 'https://dian.ysbang.cn/wholesale-drug/sales/getHotWholesalesForProvider/v4230'
            body3 = {'providerId': provider_id, 'page': 1, 'pageSize': 5}
            resp3 = requests.post(url3, json=body3, headers=headers, cookies=cookies, timeout=15)
            data3 = resp3.json()
            
            if data3.get('code') in ['0', 0]:
                items = data3.get('data', [])
                print(f"\n找到 {len(items)} 个热销商品\n")
                
                for i, item in enumerate(items[:3], 1):
                    print(f"\n商品 {i}:")
                    print(f"  名称: {item.get('drugname')}")
                    print(f"  规格: {item.get('specification')}")
                    print(f"  厂家: {item.get('manufacturer')}")
                    print(f"  价格: ¥{item.get('price')}")
                    
                    print(f"\n  所有字段:")
                    for key, value in item.items():
                        if any(keyword in key.lower() for keyword in ['type', 'category', 'class', 'kind', '类', '型']):
                            print(f"    ⭐ {key}: {value}")
                        elif key not in ['drugname', 'specification', 'manufacturer', 'price']:
                            print(f"    {key}: {value}")

if __name__ == '__main__':
    test_search_api()
