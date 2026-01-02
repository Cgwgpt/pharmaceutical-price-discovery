"""
数据库迁移脚本：添加价格异常标注字段

为 price_records 表添加:
- is_outlier: 价格异常标注 (0=正常, 1=异常高, -1=异常低, 2=占位价格)
- outlier_reason: 异常原因说明
"""
import sqlite3

def migrate():
    conn = sqlite3.connect('pharma_prices.db')
    cursor = conn.cursor()
    
    try:
        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(price_records)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # 添加 is_outlier 字段
        if 'is_outlier' not in columns:
            print("添加 is_outlier 字段...")
            cursor.execute("""
                ALTER TABLE price_records 
                ADD COLUMN is_outlier INTEGER DEFAULT 0
            """)
            print("✓ is_outlier 字段已添加")
        else:
            print("is_outlier 字段已存在")
        
        # 添加 outlier_reason 字段
        if 'outlier_reason' not in columns:
            print("添加 outlier_reason 字段...")
            cursor.execute("""
                ALTER TABLE price_records 
                ADD COLUMN outlier_reason VARCHAR(200)
            """)
            print("✓ outlier_reason 字段已添加")
        else:
            print("outlier_reason 字段已存在")
        
        # 检查 drugs 表的 category 字段
        cursor.execute("PRAGMA table_info(drugs)")
        drug_columns = [col[1] for col in cursor.fetchall()]
        
        if 'category' not in drug_columns:
            print("添加 category 字段到 drugs 表...")
            cursor.execute("""
                ALTER TABLE drugs 
                ADD COLUMN category VARCHAR(20) DEFAULT 'drug'
            """)
            print("✓ category 字段已添加")
        else:
            print("category 字段已存在")
        
        conn.commit()
        print("\n✅ 数据库迁移完成！")
        
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
