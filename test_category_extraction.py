"""
测试商品类别提取功能
"""
import json
from scraper.utils.category_extractor import extract_category_sync

def test_extract_categories():
    """测试提取不同类型商品的类别"""
    
    # 读取token
    try:
        with open('.token_cache.json', 'r') as f:
            token = json.load(f)['token']
    except:
        print("❌ 无法读取token")
        return
    
    # 测试不同类型的商品
    test_cases = [
        {'name': '片仔癀(药品)', 'drug_id': 138595},
        # 可以添加更多测试用例
        # {'name': '片仔癀珍珠霜(化妆品)', 'drug_id': xxx},
        # {'name': '医用口罩(医疗器械)', 'drug_id': xxx},
    ]
    
    print("=" * 70)
    print("商品类别提取测试")
    print("=" * 70)
    
    for case in test_cases:
        print(f"\n测试: {case['name']} (drugId={case['drug_id']})")
        print("-" * 70)
        
        result = extract_category_sync(
            drug_id=case['drug_id'],
            token=token,
            headless=True  # 使用无头模式
        )
        
        print(f"  成功: {result['success']}")
        print(f"  类别: {result['category']}")
        print(f"  批准文号: {result['approval_number']}")
        
        if result['api_data']:
            print(f"  拦截到API数据: 是")
            # 显示API数据的关键字段
            if 'data' in result['api_data']:
                data = result['api_data']['data']
                if isinstance(data, dict):
                    print(f"  API字段: {', '.join(data.keys())}")
        
        if result['error']:
            print(f"  错误: {result['error']}")
        
        print()
    
    print("=" * 70)
    print("测试完成")
    print("=" * 70)

if __name__ == '__main__':
    test_extract_categories()
