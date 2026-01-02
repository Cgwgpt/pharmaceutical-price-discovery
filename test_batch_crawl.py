#!/usr/bin/env python3
"""
测试批量采集功能
"""
import sys
sys.path.insert(0, '.')

from app.services.crawl_service import CrawlService
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_batch_crawl():
    """测试批量采集搜索结果"""
    
    keyword = '天麻蜜环菌片'
    max_drugs = 5  # 测试时只采集5个药品
    
    print("=" * 60)
    print(f"📦 批量采集测试")
    print("=" * 60)
    print(f"搜索关键词: {keyword}")
    print(f"最多采集: {max_drugs} 个药品")
    print(f"预计耗时: {max_drugs * 15} 秒")
    print("=" * 60)
    print()
    
    service = CrawlService()
    
    result = service.crawl_all_search_results(
        keyword=keyword,
        max_drugs=max_drugs,
        max_providers_per_drug=50,
        save_to_db=True
    )
    
    print()
    print("=" * 60)
    print("📊 采集结果")
    print("=" * 60)
    
    if result['success']:
        print(f"✅ 采集成功！")
        print(f"📊 采集了 {result['total_drugs']} 个药品")
        print(f"📊 找到 {result['total_providers']} 个供应商")
        print(f"💾 保存了 {result['total_saved']} 条新价格记录")
        print()
        
        if result['drugs']:
            print("📋 药品详情：")
            for idx, drug in enumerate(result['drugs'], 1):
                if drug.get('success'):
                    print(f"  {idx}. {drug['name']}")
                    print(f"     └─ {drug['providers_count']} 个供应商，保存 {drug['saved_count']} 条记录")
                else:
                    print(f"  {idx}. {drug['name']} ❌ {drug.get('error', '采集失败')}")
    else:
        print(f"❌ 采集失败: {result.get('error')}")
    
    print("=" * 60)

if __name__ == '__main__':
    test_batch_crawl()
