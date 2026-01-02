"""
修复数据库中的商品类别误判
"""
import sqlite3
from app.services.crawl_service import CrawlService

def fix_categories():
    """修复已知的误判"""
    
    conn = sqlite3.connect('pharma_prices.db')
    cursor = conn.cursor()
    
    print("=" * 70)
    print("修复商品类别误判")
    print("=" * 70)
    
    # 1. 修复阿托伐他汀钙片（降脂药，应为药品）
    print("\n1. 修复阿托伐他汀钙片...")
    cursor.execute("""
        UPDATE drugs 
        SET category = 'drug' 
        WHERE name LIKE '%阿托伐他汀钙片%'
    """)
    affected = cursor.rowcount
    print(f"   ✓ 修复了 {affected} 条记录")
    
    # 2. 修复维生素类药品（含剂型的应为药品）
    print("\n2. 修复维生素类药品...")
    cursor.execute("""
        UPDATE drugs 
        SET category = 'drug' 
        WHERE (name LIKE '%维生素%片%' 
           OR name LIKE '%维生素%滴剂%'
           OR name LIKE '%维生素%胶囊%'
           OR name LIKE '%维生素%口服液%')
          AND category != 'drug'
    """)
    affected = cursor.rowcount
    print(f"   ✓ 修复了 {affected} 条记录")
    
    conn.commit()
    
    # 3. 重新检测所有商品的类别
    print("\n3. 重新检测所有商品类别...")
    
    service = CrawlService()
    
    cursor.execute("SELECT id, name, manufacturer FROM drugs")
    drugs = cursor.fetchall()
    
    updated = 0
    for drug_id, name, manufacturer in drugs:
        result = service._detect_product_category(name, manufacturer or '')
        new_category = result['category']
        confidence = result['confidence']
        
        # 获取当前类别
        cursor.execute("SELECT category FROM drugs WHERE id = ?", (drug_id,))
        current_category = cursor.fetchone()[0]
        
        # 如果类别不同且新类别置信度高，则更新
        if current_category != new_category and confidence >= 0.8:
            cursor.execute("""
                UPDATE drugs 
                SET category = ? 
                WHERE id = ?
            """, (new_category, drug_id))
            updated += 1
            print(f"   更新: {name}")
            print(f"     {current_category} → {new_category} (置信度={confidence:.2f})")
    
    conn.commit()
    print(f"\n   ✓ 更新了 {updated} 条记录")
    
    # 4. 显示最终统计
    print("\n4. 最终统计:")
    cursor.execute("""
        SELECT category, COUNT(*) as count 
        FROM drugs 
        GROUP BY category 
        ORDER BY count DESC
    """)
    
    for category, count in cursor.fetchall():
        category_names = {
            'drug': '药品',
            'cosmetic': '化妆品',
            'medical_device': '医疗器械',
            'health_product': '保健品'
        }
        name = category_names.get(category, category)
        print(f"   {name}: {count}个")
    
    # 5. 显示非药品商品
    print("\n5. 非药品商品列表:")
    cursor.execute("""
        SELECT name, category 
        FROM drugs 
        WHERE category != 'drug' 
        ORDER BY category, name
    """)
    
    for name, category in cursor.fetchall():
        category_names = {
            'cosmetic': '化妆品',
            'medical_device': '医疗器械',
            'health_product': '保健品'
        }
        cat_name = category_names.get(category, category)
        print(f"   [{cat_name}] {name}")
    
    conn.close()
    
    print("\n" + "=" * 70)
    print("修复完成")
    print("=" * 70)

if __name__ == '__main__':
    fix_categories()
