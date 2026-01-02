#!/usr/bin/env python3
"""
测试药品详情页面数据完整性
"""
import sqlite3
import requests
import re

def test_drug_detail_data():
    """测试药品详情页面数据完整性"""
    drug_id = 204  # 皇后牌 片仔癀 珍珠膏 20g
    
    print("=" * 60)
    print(f"测试药品详情页面数据完整性 (Drug ID: {drug_id})")
    print("=" * 60)
    
    # 1. 查询数据库中的数据
    print("\n1. 查询数据库...")
    conn = sqlite3.connect('pharma_prices.db')
    cursor = conn.cursor()
    
    # 获取药品信息
    cursor.execute("SELECT name, specification, manufacturer FROM drugs WHERE id = ?", (drug_id,))
    drug_info = cursor.fetchone()
    print(f"   药品名称: {drug_info[0]}")
    print(f"   规格: {drug_info[1] or '无'}")
    print(f"   厂家: {drug_info[2] or '无'}")
    
    # 获取价格记录统计
    cursor.execute("""
        SELECT 
            COUNT(*) as total_records,
            COUNT(DISTINCT source_name) as unique_sources,
            MIN(price) as min_price,
            MAX(price) as max_price,
            AVG(price) as avg_price
        FROM price_records 
        WHERE drug_id = ?
    """, (drug_id,))
    stats = cursor.fetchone()
    total_records, unique_sources, min_price, max_price, avg_price = stats
    
    print(f"\n   💾 数据库统计:")
    print(f"   - 总记录数: {total_records}")
    print(f"   - 不同供应商数: {unique_sources}")
    print(f"   - 最低价: ¥{min_price:.2f}")
    print(f"   - 最高价: ¥{max_price:.2f}")
    print(f"   - 平均价: ¥{avg_price:.2f}")
    
    # 获取所有供应商列表
    cursor.execute("""
        SELECT DISTINCT source_name, price 
        FROM price_records 
        WHERE drug_id = ? 
        ORDER BY price
    """, (drug_id,))
    db_sources = cursor.fetchall()
    conn.close()
    
    # 2. 访问详情页面
    print("\n2. 访问详情页面...")
    url = f"http://127.0.0.1:5001/drug/{drug_id}"
    response = requests.get(url)
    
    if response.status_code != 200:
        print(f"   ❌ 页面访问失败: {response.status_code}")
        return
    
    print(f"   ✅ 页面访问成功")
    
    # 3. 解析页面内容
    print("\n3. 解析页面内容...")
    html = response.text
    
    # 提取所有供应商名称
    page_sources = re.findall(r'药师帮-([^<]+)', html)
    # 去重（因为顶部会显示一次最低价供应商）
    unique_page_sources = list(set(page_sources))
    
    print(f"   📊 页面显示的供应商数: {len(unique_page_sources)}")
    
    # 提取所有价格
    prices = re.findall(r'¥(\d+\.\d+)', html)
    print(f"   💰 页面显示的价格数: {len(prices)}")
    
    # 4. 对比验证
    print("\n4. 数据完整性验证...")
    
    # 验证供应商数量
    if len(unique_page_sources) == unique_sources:
        print(f"   ✅ 供应商数量匹配: {len(unique_page_sources)} = {unique_sources}")
    else:
        print(f"   ⚠️  供应商数量不匹配: 页面 {len(unique_page_sources)} vs 数据库 {unique_sources}")
    
    # 验证价格范围
    page_prices = [float(p) for p in prices]
    if page_prices:
        page_min = min(page_prices)
        page_max = max(page_prices)
        
        if abs(page_min - min_price) < 0.01:
            print(f"   ✅ 最低价匹配: ¥{page_min:.2f}")
        else:
            print(f"   ⚠️  最低价不匹配: 页面 ¥{page_min:.2f} vs 数据库 ¥{min_price:.2f}")
        
        if abs(page_max - max_price) < 0.01:
            print(f"   ✅ 最高价匹配: ¥{page_max:.2f}")
        else:
            print(f"   ⚠️  最高价不匹配: 页面 ¥{page_max:.2f} vs 数据库 ¥{max_price:.2f}")
    
    # 5. 显示供应商列表对比
    print("\n5. 供应商列表（前10个）:")
    print(f"   {'数据库':<30} {'页面':<30}")
    print(f"   {'-'*30} {'-'*30}")
    
    db_source_names = [s[0].replace('药师帮-', '') for s in db_sources[:10]]
    page_source_names = sorted(unique_page_sources)[:10]
    
    max_len = max(len(db_source_names), len(page_source_names))
    for i in range(max_len):
        db_name = db_source_names[i] if i < len(db_source_names) else ''
        page_name = page_source_names[i] if i < len(page_source_names) else ''
        print(f"   {db_name:<30} {page_name:<30}")
    
    # 6. 总结
    print("\n" + "=" * 60)
    if len(unique_page_sources) == unique_sources:
        print("✅ 数据完整性验证通过！")
        print(f"   - 所有 {unique_sources} 个供应商都正确显示")
        print(f"   - 价格范围: ¥{min_price:.2f} - ¥{max_price:.2f}")
    else:
        print("⚠️  数据可能不完整")
        print(f"   - 数据库: {unique_sources} 个供应商")
        print(f"   - 页面: {len(unique_page_sources)} 个供应商")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_drug_detail_data()
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
