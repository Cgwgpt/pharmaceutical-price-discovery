#!/usr/bin/env python3
"""
测试智能采集功能

演示 API 优先、Playwright 备选的策略
"""
import logging
from app.services.crawl_service import CrawlService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_smart_crawl():
    """测试智能采集"""
    service = CrawlService()
    
    # 测试药品
    test_cases = [
        {
            'keyword': '阿莫西林',
            'description': '常见药品，API 应该能找到足够数据'
        },
        {
            'keyword': '天麻蜜环菌片',
            'description': '可能需要 Playwright 补充'
        }
    ]
    
    print("\n" + "="*60)
    print("🧠 智能采集测试")
    print("="*60)
    
    for i, test in enumerate(test_cases, 1):
        keyword = test['keyword']
        description = test['description']
        
        print(f"\n测试 {i}: {keyword}")
        print(f"说明: {description}")
        print("-" * 60)
        
        # 执行智能采集
        result = service.crawl_with_smart_strategy(
            keyword=keyword,
            min_providers=5,  # 少于5个供应商时使用 Playwright 补充
            save_to_db=False  # 测试时不保存
        )
        
        # 显示结果
        print(f"\n结果:")
        print(f"  成功: {'✅' if result['success'] else '❌'}")
        print(f"  方法: {result['method']}")
        print(f"  API 采集: {result['api_count']} 个供应商")
        print(f"  Playwright 补充: {result['playwright_count']} 个供应商")
        print(f"  总计: {len(result['providers'])} 个供应商")
        
        if result.get('error'):
            print(f"  错误: {result['error']}")
        
        # 显示前5个供应商价格
        if result['providers']:
            print(f"\n  前5个供应商价格:")
            for j, p in enumerate(result['providers'][:5], 1):
                source = p.get('source', 'unknown')
                print(f"    {j}. {p['provider_name']}: ¥{p['price']:.2f} [{source}]")
        
        print("\n" + "="*60)

if __name__ == '__main__':
    test_smart_crawl()
