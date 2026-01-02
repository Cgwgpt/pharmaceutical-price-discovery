"""
价格告警服务
实现告警创建、存储、通知和管理
"""
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config import DATABASE_URL
from app.models import Base, init_db

logger = logging.getLogger(__name__)


class PriceAlert(Base):
    """价格告警模型"""
    __tablename__ = 'price_alerts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    drug_id = Column(Integer, nullable=False, index=True)
    drug_name = Column(String(200))
    alert_type = Column(String(50), nullable=False)  # price_change, threshold_reached, etc.
    message = Column(String(500))
    data = Column(Text)  # JSON格式的详细数据
    is_read = Column(Boolean, default=False)
    is_handled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    handled_at = Column(DateTime)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'drug_id': self.drug_id,
            'drug_name': self.drug_name,
            'alert_type': self.alert_type,
            'message': self.message,
            'data': json.loads(self.data) if self.data else None,
            'is_read': self.is_read,
            'is_handled': self.is_handled,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'handled_at': self.handled_at.isoformat() if self.handled_at else None
        }


class AlertService:
    """
    告警服务
    
    功能:
    - 创建告警
    - 查询告警
    - 标记已读/已处理
    - 告警统计
    """
    
    # 告警类型
    ALERT_TYPES = {
        'price_change': '价格变动',
        'price_drop': '价格下降',
        'price_rise': '价格上涨',
        'threshold_reached': '达到目标价',
        'new_lowest': '发现更低价',
        'stock_alert': '库存告警'
    }
    
    def __init__(self):
        self.engine, SessionLocal = init_db(DATABASE_URL)
        # 确保告警表存在
        PriceAlert.__table__.create(self.engine, checkfirst=True)
        self.session = SessionLocal()
    
    def __del__(self):
        if hasattr(self, 'session') and self.session:
            self.session.close()
    
    def create_alert(
        self,
        drug_id: int,
        alert_type: str,
        message: str,
        data: Dict = None,
        drug_name: str = None
    ) -> PriceAlert:
        """
        创建告警
        
        Args:
            drug_id: 药品ID
            alert_type: 告警类型
            message: 告警消息
            data: 详细数据
            drug_name: 药品名称
            
        Returns:
            创建的告警对象
        """
        alert = PriceAlert(
            drug_id=drug_id,
            drug_name=drug_name or data.get('drug_name', ''),
            alert_type=alert_type,
            message=message,
            data=json.dumps(data, ensure_ascii=False) if data else None
        )
        
        self.session.add(alert)
        self.session.commit()
        
        logger.info(f"创建告警: [{alert_type}] {message}")
        
        # 触发通知
        self._send_notification(alert)
        
        return alert
    
    def _send_notification(self, alert: PriceAlert):
        """
        发送告警通知
        
        可扩展为邮件、短信、微信等通知方式
        """
        # 目前仅记录日志，可扩展其他通知方式
        logger.info(f"[告警通知] {alert.alert_type}: {alert.message}")
        
        # TODO: 扩展通知方式
        # - 邮件通知
        # - 微信通知
        # - 钉钉通知
        # - 短信通知
    
    def get_alerts(
        self,
        drug_id: int = None,
        alert_type: str = None,
        is_read: bool = None,
        is_handled: bool = None,
        days: int = 7,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        查询告警
        
        Args:
            drug_id: 药品ID
            alert_type: 告警类型
            is_read: 是否已读
            is_handled: 是否已处理
            days: 查询天数
            limit: 返回数量限制
            
        Returns:
            告警列表
        """
        since = datetime.now() - timedelta(days=days)
        
        query = self.session.query(PriceAlert).filter(
            PriceAlert.created_at >= since
        )
        
        if drug_id:
            query = query.filter(PriceAlert.drug_id == drug_id)
        if alert_type:
            query = query.filter(PriceAlert.alert_type == alert_type)
        if is_read is not None:
            query = query.filter(PriceAlert.is_read == is_read)
        if is_handled is not None:
            query = query.filter(PriceAlert.is_handled == is_handled)
        
        alerts = query.order_by(PriceAlert.created_at.desc()).limit(limit).all()
        
        return [a.to_dict() for a in alerts]
    
    def get_unread_count(self) -> int:
        """获取未读告警数量"""
        return self.session.query(PriceAlert).filter(
            PriceAlert.is_read == False
        ).count()
    
    def mark_as_read(self, alert_id: int) -> bool:
        """标记告警为已读"""
        alert = self.session.query(PriceAlert).filter(
            PriceAlert.id == alert_id
        ).first()
        
        if alert:
            alert.is_read = True
            self.session.commit()
            return True
        return False
    
    def mark_as_handled(self, alert_id: int) -> bool:
        """标记告警为已处理"""
        alert = self.session.query(PriceAlert).filter(
            PriceAlert.id == alert_id
        ).first()
        
        if alert:
            alert.is_handled = True
            alert.handled_at = datetime.utcnow()
            self.session.commit()
            return True
        return False
    
    def mark_all_as_read(self) -> int:
        """标记所有告警为已读"""
        count = self.session.query(PriceAlert).filter(
            PriceAlert.is_read == False
        ).update({'is_read': True})
        self.session.commit()
        return count
    
    def delete_old_alerts(self, days: int = 30) -> int:
        """删除旧告警"""
        cutoff = datetime.now() - timedelta(days=days)
        count = self.session.query(PriceAlert).filter(
            PriceAlert.created_at < cutoff
        ).delete()
        self.session.commit()
        logger.info(f"已删除 {count} 条旧告警")
        return count
    
    def get_alert_statistics(self, days: int = 7) -> Dict[str, Any]:
        """
        获取告警统计
        
        Args:
            days: 统计天数
            
        Returns:
            统计信息
        """
        since = datetime.now() - timedelta(days=days)
        
        total = self.session.query(PriceAlert).filter(
            PriceAlert.created_at >= since
        ).count()
        
        unread = self.session.query(PriceAlert).filter(
            PriceAlert.created_at >= since,
            PriceAlert.is_read == False
        ).count()
        
        unhandled = self.session.query(PriceAlert).filter(
            PriceAlert.created_at >= since,
            PriceAlert.is_handled == False
        ).count()
        
        # 按类型统计
        from sqlalchemy import func
        type_stats = self.session.query(
            PriceAlert.alert_type,
            func.count(PriceAlert.id).label('count')
        ).filter(
            PriceAlert.created_at >= since
        ).group_by(PriceAlert.alert_type).all()
        
        return {
            'period_days': days,
            'total': total,
            'unread': unread,
            'unhandled': unhandled,
            'by_type': {
                t[0]: t[1] for t in type_stats
            }
        }
    
    def create_price_change_alert(
        self,
        drug_id: int,
        drug_name: str,
        old_price: float,
        new_price: float,
        source_name: str
    ):
        """
        创建价格变动告警
        
        Args:
            drug_id: 药品ID
            drug_name: 药品名称
            old_price: 原价
            new_price: 新价
            source_name: 来源
        """
        change = new_price - old_price
        change_percent = (change / old_price) * 100 if old_price > 0 else 0
        
        if change < 0:
            alert_type = 'price_drop'
            message = f"{drug_name} 价格下降 {abs(change_percent):.1f}%，从 ¥{old_price:.2f} 降至 ¥{new_price:.2f}"
        else:
            alert_type = 'price_rise'
            message = f"{drug_name} 价格上涨 {change_percent:.1f}%，从 ¥{old_price:.2f} 涨至 ¥{new_price:.2f}"
        
        self.create_alert(
            drug_id=drug_id,
            alert_type=alert_type,
            message=message,
            drug_name=drug_name,
            data={
                'drug_id': drug_id,
                'drug_name': drug_name,
                'old_price': old_price,
                'new_price': new_price,
                'change': round(change, 2),
                'change_percent': round(change_percent, 2),
                'source_name': source_name
            }
        )
    
    def create_threshold_alert(
        self,
        drug_id: int,
        drug_name: str,
        current_price: float,
        target_price: float,
        source_name: str
    ):
        """
        创建目标价格告警
        
        Args:
            drug_id: 药品ID
            drug_name: 药品名称
            current_price: 当前价格
            target_price: 目标价格
            source_name: 来源
        """
        message = f"{drug_name} 已达到目标价格 ¥{target_price:.2f}，当前价格 ¥{current_price:.2f}"
        
        self.create_alert(
            drug_id=drug_id,
            alert_type='threshold_reached',
            message=message,
            drug_name=drug_name,
            data={
                'drug_id': drug_id,
                'drug_name': drug_name,
                'current_price': current_price,
                'target_price': target_price,
                'source_name': source_name
            }
        )
