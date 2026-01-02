#!/usr/bin/env python3
"""
测试药品列表页面功能
"""
import requests
from bs4 import BeautifulSoup

BASE_URL = "http://127.0.0.1:5001"

def test_drugs_list_page():
    """测试药品列表页面基本功能"""
    print("=" * 60)
    print("测试药品列表页面")
    print("=" * 60)
    
    # 测试1: 访问药品列表页面
    print("\n1. 测试访问药品列表页面...")
    response = requests.get(f"{BASE_URL}/drugs")
    assert response.status_code == 200, "页面访问失败"
    print("✅ 页面访问成功")
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 测试2: 检查页面标题
    print("\n2. 检查页面标题...")
    title = soup.find('title').text
    assert "已采集药品列表" in title, "页面标题不正确"
    print(f"✅ 页面标题: {title}")
    
    # 测试3: 检查统计信息
    print("\n3. 检查统计信息...")
    stats_cards = soup.find_all('div', class_='card-body text-center')
    if len(stats_cards) >= 4:
        total_drugs = stats_cards[0].find('h3').text
        total_prices = stats_cards[1].find('h3').text
        current_page = stats_cards[2].find('h3').text
        total_pages = stats_cards[3].find('h3').text
        print(f"✅ 药品总数: {total_drugs}")
        print(f"✅ 价格记录总数: {total_prices}")
        print(f"✅ 当前页: {current_page}")
        print(f"✅ 总页数: {total_pages}")
    
    # 测试4: 检查药品表格
    print("\n4. 检查药品表格...")
    table = soup.find('table', class_='table')
    assert table is not None, "未找到药品表格"
    rows = table.find('tbody').find_all('tr')
    print(f"✅ 找到 {len(rows)} 条药品记录")
    
    if rows:
        first_row = rows[0]
        cells = first_row.find_all('td')
        if len(cells) >= 7:
            drug_id = cells[0].text.strip()
            drug_name = cells[1].find('strong').text.strip()
            print(f"✅ 第一条记录: ID={drug_id}, 名称={drug_name}")
    
    # 测试5: 测试排序功能
    print("\n5. 测试排序功能...")
    for sort_by in ['updated', 'name', 'price_count']:
        response = requests.get(f"{BASE_URL}/drugs?sort={sort_by}")
        assert response.status_code == 200, f"排序 {sort_by} 失败"
        print(f"✅ 排序方式 '{sort_by}' 正常")
    
    # 测试6: 测试分页功能
    print("\n6. 测试分页功能...")
    for page in [1, 2]:
        response = requests.get(f"{BASE_URL}/drugs?page={page}")
        assert response.status_code == 200, f"第 {page} 页访问失败"
        soup = BeautifulSoup(response.text, 'html.parser')
        page_indicator = soup.find_all('div', class_='card-body text-center')
        if len(page_indicator) >= 3:
            current = page_indicator[2].find('h3').text.strip()
            assert current == str(page), f"页码不匹配: 期望 {page}, 实际 {current}"
        print(f"✅ 第 {page} 页正常")
    
    # 测试7: 测试查看按钮链接
    print("\n7. 测试查看按钮链接...")
    response = requests.get(f"{BASE_URL}/drugs")
    soup = BeautifulSoup(response.text, 'html.parser')
    view_links = soup.find_all('a', class_='btn-outline-primary')
    if view_links:
        first_link = view_links[0]['href']
        print(f"✅ 找到查看链接: {first_link}")
        
        # 访问药品详情页
        response = requests.get(f"{BASE_URL}{first_link}")
        assert response.status_code == 200, "药品详情页访问失败"
        print(f"✅ 药品详情页访问成功")
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_drugs_list_page()
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
