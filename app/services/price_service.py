"""
价格查询服务
提供药品价格查询、搜索和比价功能
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from config import DATABASE_URL
from app.models import Drug, PriceRecord, init_db


class PriceService:
    """
    价格查询服务
    
    提供:
    - 最新价格查询
    - 药品搜索
    - 价格历史
    - 多平台比价
    """
    
    def __init__(self):
        self.engine, SessionLocal = init_db(DATABASE_URL)
        self.session = SessionLocal()
    
    def __del__(self):
        if hasattr(self, 'session') and self.session:
            self.session.close()
    
    def get_recent_prices(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取最近爬取的价格记录
        
        Args:
            limit: 返回数量限制
            
        Returns:
            价格记录列表
        """
        records = (
            self.session.query(PriceRecord, Drug)
            .join(Drug, PriceRecord.drug_id == Drug.id)
            .order_by(desc(PriceRecord.crawled_at))
            .limit(limit)
            .all()
        )
        
        return [
            {
                'id': record.id,
                'drug_id': drug.id,
                'drug_name': drug.name,
                'specification': drug.specification,
                'manufacturer': drug.manufacturer,
                'price': float(record.price),
                'source_name': record.source_name,
                'source_url': record.source_url,
                'crawled_at': record.crawled_at.isoformat() if record.crawled_at else None
            }
            for record, drug in records
        ]
    
    def search_drugs(self, keyword: str, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """
        搜索药品
        
        Args:
            keyword: 搜索关键词
            page: 页码
            per_page: 每页数量
            
        Returns:
            搜索结果
        """
        # 模糊搜索
        query = self.session.query(Drug).filter(
            Drug.name.ilike(f'%{keyword}%')
        )
        
        # 统计总数
        total = query.count()
        
        # 分页
        drugs = query.offset((page - 1) * per_page).limit(per_page).all()
        
        # 获取每个药品的最新价格
        result = []
        for drug in drugs:
            latest_price = (
                self.session.query(PriceRecord)
                .filter(PriceRecord.drug_id == drug.id)
                .order_by(desc(PriceRecord.crawled_at))
                .first()
            )
            
            result.append({
                'id': drug.id,
                'name': drug.name,
                'specification': drug.specification,
                'manufacturer': drug.manufacturer,
                'latest_price': float(latest_price.price) if latest_price else None,
                'source_name': latest_price.source_name if latest_price else None,
                'updated_at': latest_price.crawled_at.isoformat() if latest_price else None
            })
        
        return {
            'drugs': result,
            'total': total,
            'pages': (total + per_page - 1) // per_page
        }
    
    def get_drug_by_id(self, drug_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID获取药品信息
        
        Args:
            drug_id: 药品ID
            
        Returns:
            药品信息或None
        """
        drug = self.session.query(Drug).filter(Drug.id == drug_id).first()
        
        if not drug:
            return None
        
        return {
            'id': drug.id,
            'name': drug.name,
            'standard_name': drug.standard_name,
            'specification': drug.specification,
            'dosage_form': drug.dosage_form,
            'manufacturer': drug.manufacturer,
            'created_at': drug.created_at.isoformat() if drug.created_at else None
        }
    
    def get_drug_prices(self, drug_id: int, include_outliers: bool = True) -> List[Dict[str, Any]]:
        """
        获取药品的所有价格记录（按来源分组，取最新）
        
        Args:
            drug_id: 药品ID
            include_outliers: 是否包含异常价格（默认True，但会标注）
            
        Returns:
            价格列表
        """
        # 子查询：每个来源的最新记录
        subquery = (
            self.session.query(
                PriceRecord.source_name,
                func.max(PriceRecord.crawled_at).label('max_time')
            )
            .filter(PriceRecord.drug_id == drug_id)
            .group_by(PriceRecord.source_name)
            .subquery()
        )
        
        # 获取最新价格
        records = (
            self.session.query(PriceRecord)
            .join(
                subquery,
                (PriceRecord.source_name == subquery.c.source_name) &
                (PriceRecord.crawled_at == subquery.c.max_time)
            )
            .filter(PriceRecord.drug_id == drug_id)
            .order_by(PriceRecord.price)
            .all()
        )
        
        prices = [
            {
                'id': r.id,
                'price': float(r.price),
                'source_name': r.source_name,
                'source_url': r.source_url,
                'crawled_at': r.crawled_at.isoformat() if r.crawled_at else None,
                'is_outlier': r.is_outlier if hasattr(r, 'is_outlier') else 0,
                'outlier_reason': r.outlier_reason if hasattr(r, 'outlier_reason') else None
            }
            for r in records
        ]
        
        # 如果不包含异常价格，过滤掉
        if not include_outliers:
            prices = [p for p in prices if p['is_outlier'] == 0]
        
        return prices
    
    def get_price_history(self, drug_id: int, days: int = 30) -> List[Dict[str, Any]]:
        """
        获取药品价格历史
        
        Args:
            drug_id: 药品ID
            days: 天数
            
        Returns:
            历史价格列表
        """
        since = datetime.now() - timedelta(days=days)
        
        records = (
            self.session.query(PriceRecord)
            .filter(
                PriceRecord.drug_id == drug_id,
                PriceRecord.crawled_at >= since
            )
            .order_by(PriceRecord.crawled_at)
            .all()
        )
        
        return [
            {
                'price': float(r.price),
                'source_name': r.source_name,
                'crawled_at': r.crawled_at.isoformat() if r.crawled_at else None
            }
            for r in records
        ]
    
    def compare_prices(self, drug_name: str) -> Optional[Dict[str, Any]]:
        """
        比较同一药品在不同平台的价格
        
        Args:
            drug_name: 药品名称
            
        Returns:
            比价结果
        """
        # 查找匹配的药品
        drugs = (
            self.session.query(Drug)
            .filter(Drug.name.ilike(f'%{drug_name}%'))
            .all()
        )
        
        if not drugs:
            return None
        
        # 收集所有价格
        all_prices = []
        for drug in drugs:
            prices = self.get_drug_prices(drug.id)
            for p in prices:
                p['drug_name'] = drug.name
                p['drug_id'] = drug.id
                p['specification'] = drug.specification
                all_prices.append(p)
        
        if not all_prices:
            return None
        
        # 按价格排序
        all_prices.sort(key=lambda x: x['price'])
        
        # 计算统计信息
        prices_values = [p['price'] for p in all_prices]
        lowest = min(prices_values)
        highest = max(prices_values)
        
        # 价差百分比
        diff_percent = ((highest - lowest) / lowest * 100) if lowest > 0 else 0
        
        return {
            'drug_name': drug_name,
            'prices': all_prices,
            'lowest_price': lowest,
            'highest_price': highest,
            'price_diff_percent': round(diff_percent, 2),
            'potential_savings': round(highest - lowest, 2),
            'source_count': len(all_prices)
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取系统统计信息
        
        Returns:
            统计数据
        """
        drug_count = self.session.query(func.count(Drug.id)).scalar()
        price_count = self.session.query(func.count(PriceRecord.id)).scalar()
        
        # 来源统计
        source_stats = (
            self.session.query(
                PriceRecord.source_name,
                func.count(PriceRecord.id).label('count')
            )
            .group_by(PriceRecord.source_name)
            .all()
        )
        
        # 最近更新时间
        latest = (
            self.session.query(func.max(PriceRecord.crawled_at))
            .scalar()
        )
        
        return {
            'drug_count': drug_count or 0,
            'price_count': price_count or 0,
            'sources': [
                {'name': s[0], 'count': s[1]}
                for s in source_stats
            ],
            'last_updated': latest.isoformat() if latest else None
        }
    
    def get_latest_prices(self, drug_name: str = None) -> List[Dict[str, Any]]:
        """
        获取药品最新价格（兼容设计文档接口）
        
        Args:
            drug_name: 药品名称（可选）
            
        Returns:
            价格列表
        """
        if drug_name:
            result = self.search_drugs(drug_name)
            return result['drugs']
        return self.get_recent_prices()

    
    def get_all_drugs_with_stats(self, page: int = 1, per_page: int = 50, sort_by: str = 'updated', keyword: str = '', category: str = None) -> Dict[str, Any]:
        """
        获取所有已采集的药品列表及统计信息
        
        Args:
            page: 页码
            per_page: 每页数量
            sort_by: 排序方式 (updated=最近更新, name=名称, price_count=价格数量)
            keyword: 搜索关键词（可选）
            category: 商品类别筛选（可选）: drug, cosmetic, medical_device, health_product
            
        Returns:
            药品列表及统计信息
        """
        from sqlalchemy import func, desc, or_
        
        # 构建查询，关联价格记录统计
        query = self.session.query(
            Drug,
            func.count(PriceRecord.id).label('price_count'),
            func.min(PriceRecord.price).label('min_price'),
            func.max(PriceRecord.price).label('max_price'),
            func.max(PriceRecord.crawled_at).label('last_crawled')
        ).outerjoin(
            PriceRecord, Drug.id == PriceRecord.drug_id
        ).group_by(Drug.id)
        
        # 搜索过滤
        if keyword:
            query = query.filter(
                or_(
                    Drug.name.ilike(f'%{keyword}%'),
                    Drug.manufacturer.ilike(f'%{keyword}%'),
                    Drug.specification.ilike(f'%{keyword}%')
                )
            )
        
        # 类别过滤
        if category:
            query = query.filter(Drug.category == category)
        
        # 排序
        if sort_by == 'name':
            query = query.order_by(Drug.name)
        elif sort_by == 'price_count':
            query = query.order_by(desc('price_count'))
        else:  # updated
            query = query.order_by(desc('last_crawled'))
        
        # 统计总数
        total = query.count()
        
        # 分页
        results = query.offset((page - 1) * per_page).limit(per_page).all()
        
        # 格式化结果
        drugs = []
        for drug, price_count, min_price, max_price, last_crawled in results:
            drugs.append({
                'id': drug.id,
                'name': drug.name,
                'specification': drug.specification,
                'manufacturer': drug.manufacturer,
                'category': drug.category if hasattr(drug, 'category') else 'drug',
                'price_count': price_count or 0,
                'min_price': float(min_price) if min_price else None,
                'max_price': float(max_price) if max_price else None,
                'last_crawled': last_crawled.isoformat() if last_crawled else None,
                'created_at': drug.created_at.isoformat() if drug.created_at else None
            })
        
        return {
            'drugs': drugs,
            'total': total,
            'pages': (total + per_page - 1) // per_page
        }
