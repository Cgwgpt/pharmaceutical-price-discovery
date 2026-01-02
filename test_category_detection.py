"""
测试改进后的商品类别识别
"""
from app.services.crawl_service import CrawlService

def test_category_detection():
    """测试各种商品的类别识别"""
    
    service = CrawlService()
    
    # 测试用例
    test_cases = [
        # (商品名称, 厂家, 预期类别)
        ('立普妥 阿托伐他汀钙片 20mg*7片(薄膜衣)', '', 'drug'),
        ('阿乐 阿托伐他汀钙片 10mg*7片', '', 'drug'),
        ('维福佳 维生素C片 0.1g*100片', '', 'drug'),
        ('达因 伊可新 维生素AD滴剂 30粒(0-1岁)', '', 'drug'),
        ('片仔癀 3g*1粒(RX)', '漳州片仔癀药业股份有限公司', 'drug'),
        ('皇后 片仔癀 珍珠霜 25g', '福建片仔癀化妆品有限公司', 'cosmetic'),
        ('皇后牌 片仔癀 珍珠膏 20g', '福建片仔癀化妆品有限公司', 'cosmetic'),
        ('朝伊康 医用外科口罩 50片(独立包装 无菌)', '', 'medical_device'),
        ('亿智 小猪佩奇 益生菌软糖 95g(草莓味)灭活型', '', 'health_product'),
        ('阿莫西林胶囊 0.25g*24粒', '', 'drug'),
        ('999 感冒灵颗粒 10g*9袋', '', 'drug'),
        ('云南白药创可贴 100片', '', 'medical_device'),
        ('汤臣倍健 蛋白粉 450g', '', 'health_product'),
    ]
    
    print("=" * 80)
    print("商品类别识别测试")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for name, manufacturer, expected in test_cases:
        result = service._detect_product_category(name, manufacturer)
        actual = result['category']
        confidence = result['confidence']
        reason = result['reason']
        
        status = "✅" if actual == expected else "❌"
        if actual == expected:
            passed += 1
        else:
            failed += 1
        
        print(f"\n{status} {name}")
        print(f"   预期: {expected}")
        print(f"   实际: {actual} (置信度={confidence:.2f})")
        print(f"   原因: {reason}")
        if manufacturer:
            print(f"   厂家: {manufacturer}")
    
    print("\n" + "=" * 80)
    print(f"测试结果: {passed}通过 / {failed}失败 / {len(test_cases)}总计")
    print(f"准确率: {passed/len(test_cases)*100:.1f}%")
    print("=" * 80)

if __name__ == '__main__':
    test_category_detection()
