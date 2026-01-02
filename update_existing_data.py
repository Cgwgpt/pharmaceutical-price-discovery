"""
更新现有数据：
1. 检测并标注商品类别
2. 标注异常价格
"""
import sqlite3
from app.services.crawl_service import CrawlService

def detect_category(name: str) -> str:
    """检测商品类别"""
    name_lower = name.lower()
    
    # 化妆品
    cosmetic_keywords = ['珍珠霜', '珍珠膏', '面霜', '乳液', '精华', '化妆', '护肤', '洗面', '面膜', '眼霜', '皇后牌']
    for kw in cosmetic_keywords:
        if kw in name_lower:
            return 'cosmetic'
    
    # 医疗器械
    device_keywords = ['血糖仪', '血压计', '体温计', '雾化器', '轮椅', '拐杖', '口罩', '手套', '纱布', '绷带']
    for kw in device_keywords:
        if kw in name_lower:
            return 'medical_device'
    
    # 保健品
    health_keywords = ['维生素', '钙片', '鱼油', '蛋白粉', '益生菌', '保健', '营养']
    for kw in health_keywords:
        if kw in name_lower:
            return 'health_product'
    
    return 'drug'

def update_categories():
    """更新商品类别"""
    conn = sqlite3.connect('pharma_prices.db')
    cursor = conn.cursor()
    
    print("正在更新商品类别...")
    
    # 获取所有药品
    cursor.execute("SELECT id, name FROM drugs")
    drugs = cursor.fetchall()
    
    updated = 0
    for drug_id, name in drugs:
        category = detect_category(name)
        cursor.execute("UPDATE drugs SET category = ? WHERE id = ?", (category, drug_id))
        if category != 'drug':
            print(f"  [{category}] {name}")
            updated += 1
    
    conn.commit()
    conn.close()
    
    print(f"✓ 更新了 {updated} 个非药品商品的类别")

def mark_outliers():
    """标注异常价格"""
    print("\n正在标注异常价格...")
    
    service = CrawlService()
    
    # 使用服务的标注方法
    from config import DATABASE_URL
    from app.models import init_db
    
    _, SessionLocal = init_db(DATABASE_URL)
    session = SessionLocal()
    
    try:
        marked = service._mark_price_outliers(session)
        print(f"✓ 标注了 {marked} 条异常价格")
    finally:
        session.close()

if __name__ == '__main__':
    print("=" * 50)
    print("更新现有数据")
    print("=" * 50)
    
    update_categories()
    mark_outliers()
    
    print("\n✅ 数据更新完成！")
