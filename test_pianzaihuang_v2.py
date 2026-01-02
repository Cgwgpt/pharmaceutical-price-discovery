"""
测试片仔癀 - 通过搜索进入详情页
"""
import json
import asyncio
from playwright.async_api import async_playwright

async def test_with_search():
    """通过搜索进入详情页"""
    
    # 读取token
    try:
        with open('.token_cache.json', 'r') as f:
            token = json.load(f)['token']
        print("✓ Token已加载")
    except:
        print("❌ 无法读取token")
        return
    
    print("\n" + "=" * 70)
    print("测试：通过搜索进入片仔癀详情页")
    print("=" * 70)
    
    captured_apis = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # 非无头模式观察
        context = await browser.new_context()
        
        # 设置token
        await context.add_cookies([{
            'name': 'Token',
            'value': token,
            'domain': 'dian.ysbang.cn',
            'path': '/'
        }])
        
        page = await context.new_page()
        
        # 拦截API
        async def handle_response(response):
            url = response.url
            if 'dian.ysbang.cn' in url and '/wholesale-drug/' in url:
                try:
                    if response.status == 200:
                        data = await response.json()
                        captured_apis.append({
                            'url': url,
                            'data': data
                        })
                        print(f"  拦截API: {url.split('dian.ysbang.cn')[-1]}")
                except:
                    pass
        
        page.on('response', handle_response)
        
        # 1. 访问首页
        print("\n步骤1：访问首页")
        await page.goto('https://dian.ysbang.cn/', wait_until='networkidle')
        await asyncio.sleep(2)
        
        # 2. 搜索片仔癀
        print("\n步骤2：搜索'片仔癀'")
        try:
            # 查找搜索框
            search_input = await page.query_selector('input[placeholder*="搜索"]')
            if search_input:
                await search_input.fill('片仔癀')
                await asyncio.sleep(1)
                
                # 按回车或点击搜索按钮
                await search_input.press('Enter')
                await asyncio.sleep(3)
                
                print("  ✓ 搜索完成")
            else:
                print("  ❌ 未找到搜索框")
        except Exception as e:
            print(f"  ❌ 搜索失败: {e}")
        
        # 3. 点击第一个结果
        print("\n步骤3：点击第一个搜索结果")
        try:
            # 等待搜索结果加载
            await asyncio.sleep(2)
            
            # 查找第一个商品链接（根据实际页面结构调整选择器）
            first_item = await page.query_selector('.drug-item, .goods-item, [class*="drug"], [class*="goods"]')
            if first_item:
                await first_item.click()
                await asyncio.sleep(5)  # 等待详情页加载
                print("  ✓ 已进入详情页")
            else:
                print("  ❌ 未找到商品项")
        except Exception as e:
            print(f"  ❌ 点击失败: {e}")
        
        # 4. 分析拦截到的API
        print(f"\n步骤4：分析拦截到的 {len(captured_apis)} 个API")
        
        # 保存到文件
        with open('debug_api_search.json', 'w', encoding='utf-8') as f:
            json.dump(captured_apis, f, ensure_ascii=False, indent=2)
        print(f"  ✓ API数据已保存到 debug_api_search.json")
        
        # 查找批准文号
        import re
        approval_patterns = [
            r'国药准字[HZSJB]\d{8}',
            r'国械注准\d+',
            r'卫妆准字\d+',
        ]
        
        found_approval = False
        for api in captured_apis:
            api_str = json.dumps(api['data'], ensure_ascii=False)
            for pattern in approval_patterns:
                matches = re.findall(pattern, api_str)
                if matches:
                    print(f"\n  ✅ 找到批准文号: {matches[0]}")
                    print(f"     来源API: {api['url'].split('dian.ysbang.cn')[-1]}")
                    found_approval = True
                    break
            if found_approval:
                break
        
        if not found_approval:
            print("\n  ⚠️  未在API中找到批准文号")
            print("  可能需要查看页面HTML内容")
        
        print("\n按Enter键关闭浏览器...")
        input()
        
        await browser.close()
    
    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)

if __name__ == '__main__':
    asyncio.run(test_with_search())
