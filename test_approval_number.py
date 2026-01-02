"""
测试药师帮API是否返回批准文号
批准文号是判断商品类别的最可靠依据
"""
import requests
import json
import re

def determine_category_by_approval(approval_number: str, name: str = '') -> str:
    """
    根据批准文号判断商品类别（最可靠的方法）
    
    批准文号格式：
    - 国药准字H/Z/S/J/B + 8位数字 = 药品
    - 国械注准/进 = 医疗器械  
    - 卫妆准字/国妆特字 = 化妆品
    """
    approval = (approval_number or '').upper()
    
    # 药品：国药准字
    if re.match(r'国药准字[HZSJB]\d{8}', approval):
        return 'drug'
    
    # 医疗器械：国械注准、国械注进
    if re.match(r'国械注[准进]', approval):
        return 'medical_device'
    
    # 化妆品：卫妆准字、国妆特字
    if '妆' in approval or '化妆' in approval:
        return 'cosmetic'
    
    # 保健品：国食健字
    if '国食健字' in approval or '卫食健字' in approval:
        return 'health_product'
    
    return 'unknown'

def test_api():
    """测试API返回的批准文号"""
    
    # 读取token
    try:
        with open('.token_cache.json', 'r') as f:
            token = json.load(f)['token']
    except:
        print("❌ 无法读取token，请先登录")
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
    
    # 测试不同类型的商品
    test_keywords = [
        '片仔癀',           # 药品
        '片仔癀珍珠霜',     # 化妆品
        '医用口罩',         # 医疗器械
        '维生素C',          # 保健品/药品
    ]
    
    url = 'https://dian.ysbang.cn/wholesale-drug/sales/getRegularSearchPurchaseListForPc/v5430'
    
    for keyword in test_keywords:
        print("\n" + "=" * 70)
        print(f"搜索: {keyword}")
        print("=" * 70)
        
        body = {'keyword': keyword, 'page': 1, 'pageSize': 5}
        
        try:
            resp = requests.post(url, json=body, headers=headers, cookies=cookies, timeout=15)
            data = resp.json()
            
            if data.get('code') not in ['0', 0, '40001']:
                # code=40001 表示没有数据，但不是错误
                if data.get('code') != '40001':
                    print(f"⚠️  API返回: code={data.get('code')}, message={data.get('message')}")
                    # 继续尝试解析数据
            
            items = data.get('data', [])
            if isinstance(items, dict):
                items = items.get('list', [])
            
            if not items:
                print("未找到商品")
                continue
            
            print(f"\n找到 {len(items)} 个商品\n")
            
            for i, item in enumerate(items[:3], 1):
                drug = item.get('drug', item)
                name = drug.get('drugName', '')
                
                print(f"\n商品 {i}: {name}")
                print(f"  规格: {drug.get('specification', '')}")
                print(f"  厂家: {drug.get('factory', '')}")
                print(f"  💊 drugType: {drug.get('drugType', 'N/A')}")  # 重点关注这个字段
                
                # 查找批准文号相关字段
                approval_fields = [
                    'approvalNumber', 'approval_number', 'approvalNo',
                    'licenseNumber', 'license_number', 'licenseNo',
                    'registrationNumber', 'registration_number',
                    'certificateNumber', 'certificate_number',
                    '批准文号', '注册证号', '许可证号'
                ]
                
                found_approval = False
                for field in approval_fields:
                    if field in drug:
                        approval = drug.get(field)
                        if approval:
                            category = determine_category_by_approval(approval, name)
                            print(f"  ✅ {field}: {approval}")
                            print(f"  📦 类别: {category}")
                            found_approval = True
                            break
                
                if not found_approval:
                    print(f"  ⚠️  未找到批准文号字段")
                    print(f"  可用字段: {', '.join(drug.keys())}")
                
        except Exception as e:
            print(f"❌ 请求失败: {e}")

if __name__ == '__main__':
    test_api()
