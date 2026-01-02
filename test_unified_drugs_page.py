#!/usr/bin/env python3
"""
测试统一的药品库页面功能
"""
import requests

BASE_URL = "http://127.0.0.1:5001"

def test_unified_drugs_page():
    """测试统一的药品库页面"""
    print("=" * 60)
    print("测试统一的药品库页面")
    print("=" * 60)
    
    # 测试1: 访问药品库（默认表格视图）
    print("\n1. 测试访问药品库（表格视图）...")
    response = requests.get(f"{BASE_URL}/drugs")
    assert response.status_code == 200, "页面访问失败"
    assert "药品库" in response.text, "页面标题不正确"
    print("✅ 表格视图访问成功")
    
    # 测试2: 访问药品库（卡片视图）
    print("\n2. 测试访问药品库（卡片视图）...")
    response = requests.get(f"{BASE_URL}/drugs?view=card")
    assert response.status_code == 200, "卡片视图访问失败"
    assert "card-hover" in response.text, "卡片视图未正确渲染"
    print("✅ 卡片视图访问成功")
    
    # 测试3: 搜索功能（表格视图）
    print("\n3. 测试搜索功能（表格视图）...")
    response = requests.get(f"{BASE_URL}/drugs?q=天麻&view=table")
    assert response.status_code == 200, "搜索失败"
    assert "搜索结果" in response.text, "搜索结果提示未显示"
    print("✅ 搜索功能正常（表格视图）")
    
    # 测试4: 搜索功能（卡片视图）
    print("\n4. 测试搜索功能（卡片视图）...")
    response = requests.get(f"{BASE_URL}/drugs?q=天麻&view=card")
    assert response.status_code == 200, "搜索失败"
    assert "搜索结果" in response.text, "搜索结果提示未显示"
    print("✅ 搜索功能正常（卡片视图）")
    
    # 测试5: 旧搜索页面重定向
    print("\n5. 测试旧搜索页面重定向...")
    response = requests.get(f"{BASE_URL}/search?q=test", allow_redirects=False)
    assert response.status_code == 302, "未正确重定向"
    assert "/drugs" in response.headers.get('Location', ''), "重定向目标不正确"
    print("✅ 旧搜索页面正确重定向到药品库")
    
    # 测试6: 视图切换
    print("\n6. 测试视图切换...")
    response = requests.get(f"{BASE_URL}/drugs?view=table")
    assert "表格" in response.text, "表格视图按钮未找到"
    assert "卡片" in response.text, "卡片视图按钮未找到"
    print("✅ 视图切换按钮正常")
    
    # 测试7: 排序功能（卡片视图）
    print("\n7. 测试排序功能（卡片视图）...")
    for sort_by in ['updated', 'name', 'price_count']:
        response = requests.get(f"{BASE_URL}/drugs?sort={sort_by}&view=card")
        assert response.status_code == 200, f"排序 {sort_by} 失败"
    print("✅ 排序功能正常（卡片视图）")
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)
    print("\n📝 功能说明：")
    print("- 药品库页面现在是统一的药品浏览和搜索入口")
    print("- 支持两种视图：表格视图（默认）和卡片视图")
    print("- 旧的搜索页面(/search)会自动重定向到药品库")
    print("- 导航栏已移除独立的'搜索'链接，统一使用'药品库'")

if __name__ == "__main__":
    try:
        test_unified_drugs_page()
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
