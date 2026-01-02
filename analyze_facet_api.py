#!/usr/bin/env python3
"""
分析 facetWholesaleList API 返回的 providers 数据
"""
import requests
import json

def analyze_facet_api():
    """分析 facetWholesaleList API"""
    
    # 获取 Token
    try:
        with open('.token_cache.json', 'r') as f:
            cache = json.load(f)
            token = cache.get('token', '')
    except:
        print('❌ 无法读取 Token')
        return
    
    keyword = '天麻蜜环菌片'
    
    print('='*70)
    print('🔬 分析 facetWholesaleList API')
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
    
    # 调用 API
    url = 'https://dian.ysbang.cn/wholesale-drug/sales/facetWholesaleList/v4270'
    body = {'keyword': keyword}
    
    try:
        resp = requests.post(url, json=body, headers=headers, cookies=cookies, timeout=15)
        data = resp.json()
        
        if data.get('code') in ['0', 0, '40001']:
            result = data.get('data', {})
            providers = result.get('providers', [])
            
            print(f'\n✅ 找到 {len(providers)} 个供应商')
            print('-'*70)
            
            if providers:
                print(f'\n供应商数据结构:')
                provider = providers[0]
                print(json.dumps(provider, ensure_ascii=False, indent=2))
                
                print(f'\n字段列表:')
                print(list(provider.keys()))
                
                # 检查是否有价格信息
                if 'minPrice' in provider or 'price' in provider:
                    print(f'\n✅ 包含价格信息！')
                    
                    print(f'\n前10个供应商:')
                    for i, p in enumerate(providers[:10], 1):
                        pid = p.get('pid', p.get('providerId', ''))
                        pname = p.get('abbreviation', p.get('name', ''))
                        min_price = p.get('minPrice', p.get('price', 0))
                        wholesale_num = p.get('wholesaleNum', 0)
                        
                        print(f'{i:2d}. {pname:25s} 最低价: ¥{min_price:8.2f} ({wholesale_num}个商品)')
                    
                    # 现在获取每个供应商的具体商品价格
                    print(f'\n' + '='*70)
                    print('🔍 获取供应商的具体商品价格')
                    print('='*70)
                    
                    # 测试第一个供应商
                    first_provider = providers[0]
                    pid = first_provider.get('pid', first_provider.get('providerId', ''))
                    pname = first_provider.get('abbreviation', first_provider.get('name', ''))
                    
                    print(f'\n测试供应商: {pname} (ID: {pid})')
                    
                    # 尝试获取该供应商的热销商品
                    url2 = 'https://dian.ysbang.cn/wholesale-drug/sales/getHotWholesalesForProvider/v4230'
                    body2 = {'providerId': pid, 'page': 1, 'pageSize': 200}
                    
                    resp2 = requests.post(url2, json=body2, headers=headers, cookies=cookies, timeout=15)
                    data2 = resp2.json()
                    
                    if data2.get('code') in ['0', 0, '40001']:
                        items = data2.get('data', [])
                        print(f'✅ 该供应商有 {len(items)} 个热销商品')
                        
                        # 过滤与关键词相关的商品
                        keyword_lower = keyword.lower()
                        related = [item for item in items if keyword_lower in item.get('drugname', '').lower()]
                        
                        print(f'✅ 其中 {len(related)} 个与"{keyword}"相关')
                        
                        if related:
                            print(f'\n相关商品:')
                            for item in related[:5]:
                                print(f'  - {item.get("drugname", "")}: ¥{item.get("price", 0)}')
                        
                        # 结论
                        print(f'\n' + '='*70)
                        print('💡 结论')
                        print('='*70)
                        print('1. facetWholesaleList 返回供应商列表（但只有最低价）')
                        print('2. getHotWholesalesForProvider 返回供应商的热销商品（包含具体价格）')
                        print('3. 但热销商品API有限制：只返回热销的，不是所有商品')
                        print('4. 这就是为什么 API 只能找到少量供应商价格的原因')
                        print('='*70)
                else:
                    print(f'\n❌ 不包含价格信息')
                    print(f'字段: {list(provider.keys())}')
        else:
            print(f'❌ API 返回错误: {data.get("message")}')
            
    except Exception as e:
        print(f'❌ 请求失败: {e}')

if __name__ == '__main__':
    analyze_facet_api()
