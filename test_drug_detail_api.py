"""
测试药品详情API，查看是否有更详细的分类信息
"""
import requests
import json

def test_drug_detail():
    """测试药品详情API"""
    
    try:
        with open('.token_cache.json', 'r') as f:
            token = json.load(f)['token']
    except:
        print("❌ 无法读取token")
        return
    
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
        'Origin': 'https://dian.ysbang.cn',
        'Referer': 'https://dian.ysbang.cn/',
        'Token': token,
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    cookies = {'Token': token}
    
    # 测试不同类型商品的drugId
    test_cases = [
        {'name': '片仔癀3g*1粒(药品)', 'drugId': None},  # 需要先搜索获取
        {'name': '片仔癀珍珠霜(化妆品)', 'keyword': '片仔癀珍珠霜'},
        {'name': '医用口罩(医疗器械)', 'keyword': '医用口罩'},
    ]
    
    # 先搜索获取drugId
    search_url = 'https://dian.ysbang.cn/wholesale-drug/sales/getRegularSearchPurchaseListForPc/v5430'
    
    for case in test_cases:
        if 'keyword' in case:
            print(f"\n{'='*70}")
            print(f"搜索: {case['name']}")
            print('='*70)
            
            body = {'keyword': case['keyword'], 'page': 1, 'pageSize': 3}
            resp = requests.post(search_url, json=body, headers=headers, cookies=cookies, timeout=15)
            data = resp.json()
            
            items = data.get('data', [])
            if isinstance(items, dict):
                items = items.get('list', [])
            
            for i, item in enumerate(items[:2], 1):
                drug = item.get('drug', item)
                drug_id = drug.get('drugId')
                name = drug.get('drugName')
                drug_type = drug.get('drugType')
                
                print(f"\n商品 {i}: {name}")
                print(f"  drugId: {drug_id}")
                print(f"  drugType: {drug_type}")
                print(f"  规格: {drug.get('specification')}")
                print(f"  厂家: {drug.get('factory')}")
                
                # 尝试获取详情
                if drug_id:
                    print(f"\n  尝试获取详情...")
                    detail_urls = [
                        f'https://dian.ysbang.cn/wholesale-drug/sales/getDrugDetail/v4230',
                        f'https://dian.ysbang.cn/wholesale-drug/sales/getDrugInfo/v4230',
                        f'https://dian.ysbang.cn/wholesale-drug/sales/drugDetail/v4230',
                    ]
                    
                    for detail_url in detail_urls:
                        try:
                            detail_body = {'drugId': drug_id}
                            detail_resp = requests.post(detail_url, json=detail_body, headers=headers, cookies=cookies, timeout=10)
                            detail_data = detail_resp.json()
                            
                            if detail_data.get('code') in ['0', 0]:
                                detail = detail_data.get('data', {})
                                if detail:
                                    print(f"  ✅ {detail_url.split('/')[-2]} 返回数据:")
                                    
                                    # 查找类别相关字段
                                    category_fields = ['category', 'type', 'drugType', 'productType', 
                                                      'approvalNumber', 'licenseNumber', 'certificateNumber',
                                                      '类别', '类型', '批准文号']
                                    
                                    for field in category_fields:
                                        if field in detail:
                                            print(f"    {field}: {detail[field]}")
                                    
                                    # 显示所有字段名
                                    print(f"    所有字段: {', '.join(detail.keys())}")
                                    break
                        except Exception as e:
                            continue

if __name__ == '__main__':
    test_drug_detail()
