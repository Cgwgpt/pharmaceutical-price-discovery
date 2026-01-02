"""
使用Playwright测试采集药品详情页
目标：获取批准文号、商品类别等详细信息
"""
import asyncio
import json
from playwright.async_api import async_playwright

async def test_drug_detail_page():
    """测试药品详情页采集"""
    
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
        {'name': '片仔癀珍珠霜(化妆品)', 'drug_id': None},  # 需要搜索
        {'name': '医用口罩(医疗器械)', 'drug_id': None},
    ]
    
    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(headless=False)  # 先用非无头模式观察
        context = await browser.new_context()
        
        # 设置token
        await context.add_cookies([{
            'name': 'Token',
            'value': token,
            'domain': 'dian.ysbang.cn',
            'path': '/'
        }])
        
        page = await context.new_page()
        
        for case in test_cases:
            drug_id = case['drug_id']
            if not drug_id:
                continue
            
            print(f"\n{'='*70}")
            print(f"测试: {case['name']} (drugId={drug_id})")
            print('='*70)
            
            # 访问详情页
            url = f'https://dian.ysbang.cn/#/drug/{drug_id}'
            print(f"访问: {url}")
            
            try:
                await page.goto(url, wait_until='networkidle', timeout=30000)
                await asyncio.sleep(3)  # 等待页面加载
                
                # 尝试提取批准文号
                print("\n查找批准文号...")
                
                # 方法1：通过文本查找
                approval_selectors = [
                    'text=批准文号',
                    'text=国药准字',
                    'text=国械注准',
                    'text=卫妆准字',
                    'text=注册证号',
                    'text=许可证号',
                ]
                
                for selector in approval_selectors:
                    try:
                        element = await page.query_selector(selector)
                        if element:
                            # 获取父元素或兄弟元素的文本
                            parent = await element.evaluate('el => el.parentElement.textContent')
                            print(f"  找到: {parent}")
                    except:
                        pass
                
                # 方法2：获取整个页面内容，搜索批准文号
                content = await page.content()
                
                import re
                # 搜索批准文号模式
                patterns = [
                    r'国药准字[HZSJB]\d{8}',
                    r'国械注准\d+',
                    r'国械注进\d+',
                    r'卫妆准字\d+',
                    r'国妆特字\d+',
                    r'国食健字G\d+',
                ]
                
                print("\n正则搜索批准文号:")
                for pattern in patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        print(f"  ✅ {pattern}: {matches[0]}")
                        
                        # 判断类别
                        approval = matches[0]
                        if '国药准字' in approval:
                            print(f"  📦 类别: 药品")
                        elif '国械注' in approval:
                            print(f"  📦 类别: 医疗器械")
                        elif '妆' in approval:
                            print(f"  📦 类别: 化妆品")
                        elif '国食健字' in approval:
                            print(f"  📦 类别: 保健品")
                
                # 方法3：拦截API请求
                print("\n等待API请求...")
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"❌ 错误: {e}")
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(test_drug_detail_page())
