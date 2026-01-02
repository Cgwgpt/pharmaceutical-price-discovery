#!/usr/bin/env python3
"""
智能采集 vs 传统采集 - 性能对比演示

展示不同采集方式的性能差异
"""
import time
import logging
from app.services.crawl_service import CrawlService

logging.basicConfig(level=logging.WARNING)  # 减少日志输出

def demo_comparison():
    """对比演示"""
    service = CrawlService()
    keyword = '阿莫西林'  # 使用常见药品测试
    
    print("\n" + "="*70)
    print("🔬 采集方式性能对比演示")
    print("="*70)
    print(f"测试药品: {keyword}")
    print("-"*70)
    
    # 方式1: 纯 API 采集
    print("\n📡 方式1: 纯 API 采集")
    print("-"*70)
    start = time.time()
    api_providers = service._crawl_with_api_only(keyword)
    api_time = time.time() - start
    print(f"✅ 完成")
    print(f"   耗时: {api_time:.2f} 秒")
    print(f"   供应商数: {len(api_providers)}")
    print(f"   速度: ⭐⭐⭐⭐⭐")
    print(f"   完整性: ⭐⭐⭐")
    
    # 方式2: 纯 Playwright 采集（如果安装了）
    print("\n🎭 方式2: 纯 Playwright 采集")
    print("-"*70)
    try:
        start = time.time()
        pw_result = service.crawl_with_playwright(keyword, headless=True, save_to_db=False)
        pw_time = time.time() - start
        pw_count = len(pw_result.get('providers', []))
        print(f"✅ 完成")
        print(f"   耗时: {pw_time:.2f} 秒")
        print(f"   供应商数: {pw_count}")
        print(f"   速度: ⭐")
        print(f"   完整性: ⭐⭐⭐⭐⭐")
    except Exception as e:
        print(f"❌ Playwright 未安装或执行失败")
        pw_time = None
        pw_count = 0
    
    # 方式3: 智能采集
    print("\n🧠 方式3: 智能采集（推荐）")
    print("-"*70)
    start = time.time()
    smart_result = service.crawl_with_smart_strategy(
        keyword=keyword,
        min_providers=5,
        save_to_db=False
    )
    smart_time = time.time() - start
    smart_count = len(smart_result.get('providers', []))
    method = smart_result.get('method', 'unknown')
    
    print(f"✅ 完成")
    print(f"   耗时: {smart_time:.2f} 秒")
    print(f"   供应商数: {smart_count}")
    print(f"   采集方法: {method}")
    print(f"   API: {smart_result.get('api_count', 0)} 个")
    print(f"   Playwright: {smart_result.get('playwright_count', 0)} 个")
    print(f"   速度: ⭐⭐⭐⭐")
    print(f"   完整性: ⭐⭐⭐⭐⭐")
    
    # 总结对比
    print("\n" + "="*70)
    print("📊 性能对比总结")
    print("="*70)
    
    print(f"\n{'方式':<20} {'耗时':<15} {'供应商数':<15} {'推荐度'}")
    print("-"*70)
    print(f"{'API 采集':<20} {f'{api_time:.2f}秒':<15} {len(api_providers):<15} {'⭐⭐⭐'}")
    if pw_time:
        print(f"{'Playwright 采集':<20} {f'{pw_time:.2f}秒':<15} {pw_count:<15} {'⭐⭐'}")
    print(f"{'智能采集（推荐）':<20} {f'{smart_time:.2f}秒':<15} {smart_count:<15} {'⭐⭐⭐⭐⭐'}")
    
    # 结论
    print("\n" + "="*70)
    print("💡 结论")
    print("="*70)
    
    if method == 'api':
        print("✅ API 数据充足，智能采集直接使用 API，速度最快！")
    elif method == 'hybrid':
        print("✅ 智能采集自动补充数据，平衡了速度和完整性！")
    elif method == 'playwright':
        print("✅ 智能采集使用 Playwright，确保数据完整性！")
    
    print("\n推荐使用智能采集，它能自动选择最优方案：")
    print("  • 数据充足时 → 使用快速的 API")
    print("  • 数据不足时 → 自动用 Playwright 补充")
    print("  • 性能最优，数据最全")
    
    print("\n" + "="*70)

if __name__ == '__main__':
    demo_comparison()
