"""
价格监控服务
实现价格历史记录、变动检测和阈值告警
"""
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy import func, desc, and_
from sqlalchemy.orm import Session

from config import DATABASE_URL
from app.models import Drug, PriceRecord, init_db


class MonitorService:
    """
    价格监控服务
    
    功能:
    - 价格历史记录查询
    - 价格变动检测
    - 阈值告警判断
    - 价格趋势分析
    """
    
    # 默认价格变动阈值（百分比）
    DEFAULT_THRESHOLD = 5.0
    
    def __init__(self):
        self.engine, SessionLocal = init_db(DATABASE_URL)
        self.session = SessionLocal()
    
    def __del__(self):
        if hasattr(self, 'session') and self.session:
            self.session.close()
    
    def get_price_history(
        self, 
        drug_id: int, 
        days: int = 30,
        source_name: str = None
    ) -> List[Dict[str, Any]]:
        """
        获取药品价格历史
        
        Args:
            drug_id: 药品ID
            days: 查询天数
            source_name: 来源名称（可选）
            
        Returns:
            历史价格列表
        """
        since = datetime.now() - timedelta(days=days)
        
        query = self.session.query(PriceRecord).filter(
            PriceRecord.drug_id == drug_id,
            PriceRecord.crawled_at >= since
        )
        
        if source_name:
            query = query.filter(PriceRecord.source_name == source_name)
        
        records = query.order_by(PriceRecord.crawled_at).all()
        
        return [
            {
                'id': r.id,
                'price': float(r.price),
                'source_name': r.source_name,
                'crawled_at': r.crawled_at.isoformat() if r.crawled_at else None,
                'date': r.crawled_at.strftime('%Y-%m-%d') if r.crawled_at else None
            }
            for r in records
        ]
    
    def get_price_trend(self, drug_id: int, days: int = 30) -> Dict[str, Any]:
        """
        获取价格趋势分析
        
        Args:
            drug_id: 药品ID
            days: 分析天数
            
        Returns:
            趋势分析结果
        """
        history = self.get_price_history(drug_id, days)
        
        if not history:
            return {
                'drug_id': drug_id,
                'trend': 'unknown',
                'data_points': 0
            }
        
        prices = [h['price'] for h in history]
        
        # 计算统计数据
        min_price = min(prices)
        max_price = max(prices)
        avg_price = sum(prices) / len(prices)
        
        # 计算趋势（简单线性回归斜率）
        if len(prices) >= 2:
            n = len(prices)
            x_sum = sum(range(n))
            y_sum = sum(prices)
            xy_sum = sum(i * p for i, p in enumerate(prices))
            x2_sum = sum(i * i for i in range(n))
            
            slope = (n * xy_sum - x_sum * y_sum) / (n * x2_sum - x_sum * x_sum) if (n * x2_sum - x_sum * x_sum) != 0 else 0
            
            if slope > 0.01:
                trend = 'rising'
            elif slope < -0.01:
                trend = 'falling'
            else:
                trend = 'stable'
        else:
            trend = 'insufficient_data'
            slope = 0
        
        # 计算波动率
        if len(prices) >= 2:
            variance = sum((p - avg_price) ** 2 for p in prices) / len(prices)
            volatility = (variance ** 0.5) / avg_price * 100
        else:
            volatility = 0
        
        return {
            'drug_id': drug_id,
            'trend': trend,
            'slope': round(slope, 4),
            'min_price': round(min_price, 2),
            'max_price': round(max_price, 2),
            'avg_price': round(avg_price, 2),
            'volatility': round(volatility, 2),
            'data_points': len(prices),
            'period_days': days,
            'history': history
        }
    
    def detect_price_change(
        self, 
        drug_id: int, 
        threshold: float = None
    ) -> Optional[Dict[str, Any]]:
        """
        检测价格变动
        
        Args:
            drug_id: 药品ID
            threshold: 变动阈值百分比
            
        Returns:
            变动信息或None
        """
        threshold = threshold or self.DEFAULT_THRESHOLD
        
        # 获取最近两次价格记录
        records = (
            self.session.query(PriceRecord)
            .filter(PriceRecord.drug_id == drug_id)
            .order_by(desc(PriceRecord.crawled_at))
            .limit(2)
            .all()
        )
        
        if len(records) < 2:
            return None
        
        current = records[0]
        previous = records[1]
        
        current_price = float(current.price)
        previous_price = float(previous.price)
        
        if previous_price == 0:
            return None
        
        # 计算变动
        change = current_price - previous_price
        change_percent = (change / previous_price) * 100
        
        # 判断是否超过阈值
        exceeded = abs(change_percent) >= threshold
        
        return {
            'drug_id': drug_id,
            'current_price': round(current_price, 2),
            'previous_price': round(previous_price, 2),
            'change': round(change, 2),
            'change_percent': round(change_percent, 2),
            'direction': 'up' if change > 0 else ('down' if change < 0 else 'unchanged'),
            'threshold': threshold,
            'exceeded': exceeded,
            'current_time': current.crawled_at.isoformat() if current.crawled_at else None,
            'previous_time': previous.crawled_at.isoformat() if previous.crawled_at else None,
            'source_name': current.source_name
        }
    
    def get_price_alerts(
        self, 
        threshold: float = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取价格变动告警列表
        
        Args:
            threshold: 变动阈值百分比
            limit: 返回数量限制
            
        Returns:
            告警列表
        """
        threshold = threshold or self.DEFAULT_THRESHOLD
        
        # 获取所有药品
        drugs = self.session.query(Drug).all()
        
        alerts = []
        for drug in drugs:
            change = self.detect_price_change(drug.id, threshold)
            if change and change['exceeded']:
                change['drug_name'] = drug.name
                change['specification'] = drug.specification
                alerts.append(change)
        
        # 按变动幅度排序
        alerts.sort(key=lambda x: abs(x['change_percent']), reverse=True)
        
        return alerts[:limit]
    
    def get_daily_summary(self, date: datetime = None) -> Dict[str, Any]:
        """
        获取每日价格汇总
        
        Args:
            date: 日期（默认今天）
            
        Returns:
            汇总信息
        """
        if date is None:
            date = datetime.now()
        
        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        
        # 当日爬取数量
        crawled_count = (
            self.session.query(func.count(PriceRecord.id))
            .filter(
                PriceRecord.crawled_at >= start,
                PriceRecord.crawled_at < end
            )
            .scalar()
        )
        
        # 当日价格变动
        alerts = self.get_price_alerts()
        
        # 按来源统计
        source_stats = (
            self.session.query(
                PriceRecord.source_name,
                func.count(PriceRecord.id).label('count')
            )
            .filter(
                PriceRecord.crawled_at >= start,
                PriceRecord.crawled_at < end
            )
            .group_by(PriceRecord.source_name)
            .all()
        )
        
        return {
            'date': date.strftime('%Y-%m-%d'),
            'crawled_count': crawled_count or 0,
            'alert_count': len(alerts),
            'price_up_count': len([a for a in alerts if a['direction'] == 'up']),
            'price_down_count': len([a for a in alerts if a['direction'] == 'down']),
            'sources': [
                {'name': s[0], 'count': s[1]}
                for s in source_stats
            ],
            'top_alerts': alerts[:10]
        }
    
    def check_threshold(
        self, 
        drug_id: int, 
        target_price: float,
        alert_type: str = 'below'
    ) -> bool:
        """
        检查价格是否达到目标阈值
        
        Args:
            drug_id: 药品ID
            target_price: 目标价格
            alert_type: 告警类型 ('below' 或 'above')
            
        Returns:
            是否达到阈值
        """
        # 获取最新价格
        latest = (
            self.session.query(PriceRecord)
            .filter(PriceRecord.drug_id == drug_id)
            .order_by(desc(PriceRecord.crawled_at))
            .first()
        )
        
        if not latest:
            return False
        
        current_price = float(latest.price)
        
        if alert_type == 'below':
            return current_price <= target_price
        elif alert_type == 'above':
            return current_price >= target_price
        
        return False
    
    def get_price_statistics(self, drug_id: int, days: int = 30) -> Dict[str, Any]:
        """
        获取价格统计信息
        
        Args:
            drug_id: 药品ID
            days: 统计天数
            
        Returns:
            统计信息
        """
        since = datetime.now() - timedelta(days=days)
        
        stats = (
            self.session.query(
                func.min(PriceRecord.price).label('min_price'),
                func.max(PriceRecord.price).label('max_price'),
                func.avg(PriceRecord.price).label('avg_price'),
                func.count(PriceRecord.id).label('record_count')
            )
            .filter(
                PriceRecord.drug_id == drug_id,
                PriceRecord.crawled_at >= since
            )
            .first()
        )
        
        if not stats or not stats.record_count:
            return {
                'drug_id': drug_id,
                'period_days': days,
                'record_count': 0
            }
        
        return {
            'drug_id': drug_id,
            'period_days': days,
            'min_price': float(stats.min_price) if stats.min_price else 0,
            'max_price': float(stats.max_price) if stats.max_price else 0,
            'avg_price': round(float(stats.avg_price), 2) if stats.avg_price else 0,
            'record_count': stats.record_count,
            'price_range': round(float(stats.max_price - stats.min_price), 2) if stats.max_price and stats.min_price else 0
        }
