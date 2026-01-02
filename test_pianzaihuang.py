"""
测试片仔癀的商品类别提取
"""
import json
import sys

def test_pianzaihuang():
    """测试片仔癀"""
    
    # 读取token
    try:
        with open('.token_cache.json', 'r') as f:
            token = json.load(f)['token']
        print(f"✓ Token已加载")
    except:
        print("❌ 无法读取token，请先登录")
        return
    
    print("\n" + "=" * 70)
    print("测试：片仔癀商品类别提取")
    print("=" * 70)
    
    # 片仔癀的drugId
    drug_id = 138595
    
    print(f"\n步骤1：使用Playwright提取类别")
    print(f"  drugId: {drug_id}")
    print(f"  正在访问详情页并拦截API...")
    
    try:
        from scraper.utils.category_extractor import extract_category_sync
        
        result = extract_category_sync(
            drug_id=drug_id,
            token=token,
            headless=True  # 无头模式
        )
        
        print(f"\n结果:")
        print(f"  成功: {result['success']}")
        
        # 显示拦截到的API
        if 'captured_api_urls' in result:
            print(f"\n  拦截到 {len(result['captured_api_urls'])} 个API请求:")
            for i, url in enumerate(result['captured_api_urls'][:5], 1):
                # 只显示路径部分
                path = url.split('dian.ysbang.cn')[-1] if 'dian.ysbang.cn' in url else url
                print(f"    {i}. {path}")
            if len(result['captured_api_urls']) > 5:
                print(f"    ... 还有 {len(result['captured_api_urls']) - 5} 个")
        
        if result['success']:
            print(f"  ✅ 商品类别: {result['category']}")
            print(f"  ✅ 批准文号: {result['approval_number']}")
            
            # 显示类别说明
            category_names = {
                'drug': '药品',
                'cosmetic': '化妆品',
                'medical_device': '医疗器械',
                'health_product': '保健品'
            }
            category_cn = category_names.get(result['category'], '未知')
            print(f"  📦 类别说明: {category_cn}")
            
            if result['api_data']:
                print(f"\n  拦截到的API数据:")
                print(f"    API URL: {result.get('api_url', 'N/A')}")
                if 'data' in result['api_data']:
                    data = result['api_data']['data']
                    if isinstance(data, dict):
                        print(f"    数据字段: {', '.join(list(data.keys())[:10])}")
            
            if result['detail']:
                print(f"\n  详情页信息:")
                for key, value in result['detail'].items():
                    print(f"    {key}: {value}")
        else:
            print(f"  ❌ 提取失败")
            if result['error']:
                print(f"  错误: {result['error']}")
        
    except ImportError as e:
        print(f"\n❌ 导入错误: {e}")
        print(f"\n请确保已安装Playwright:")
        print(f"  pip install playwright")
        print(f"  playwright install chromium")
        return
    except Exception as e:
        print(f"\n❌ 执行错误: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)

if __name__ == '__main__':
    test_pianzaihuang()
