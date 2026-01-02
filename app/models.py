"""
数据模型定义
使用SQLAlchemy ORM定义Drug和PriceRecord模型
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey,
    Numeric, Index, create_engine
)
from sqlalchemy.orm import declarative_base, relationship, Session

Base = declarative_base()


class Drug(Base):
    """药品基础信息模型"""
    __tablename__ = 'drugs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, index=True)
    standard_name = Column(String(200), index=True)
    generic_name = Column(String(200), index=True)  # 通用名
    brand_name = Column(String(100))  # 品牌名
    specification = Column(String(100))
    dosage_form = Column(String(50))
    manufacturer = Column(String(200))
    approval_number = Column(String(50), index=True)  # 批准文号（国药准字等）
    category = Column(String(20), default='drug')  # 产品类别: drug, medical_device, cosmetic, other
    drug_hash = Column(String(16), index=True)  # 唯一标识（含厂家）
    simple_hash = Column(String(12), index=True)  # 简化标识（不含厂家）
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联价格记录
    price_records = relationship('PriceRecord', back_populates='drug', lazy='dynamic')
    # 关联别名
    aliases = relationship('DrugAlias', back_populates='drug', lazy='dynamic')

    def __repr__(self):
        return f'<Drug {self.name}>'


class PriceRecord(Base):
    """价格记录模型"""
    __tablename__ = 'price_records'

    id = Column(Integer, primary_key=True, autoincrement=True)
    drug_id = Column(Integer, ForeignKey('drugs.id'), nullable=False, index=True)
    price = Column(Numeric(10, 2), nullable=False)
    source_url = Column(String(500), nullable=False)
    source_name = Column(String(100), nullable=False)
    crawled_at = Column(DateTime, default=datetime.utcnow, index=True)
    is_outlier = Column(Integer, default=0)  # 价格异常标注: 0=正常, 1=异常高, -1=异常低, 2=占位价格
    outlier_reason = Column(String(200))  # 异常原因说明

    # 关联药品
    drug = relationship('Drug', back_populates='price_records')

    def __repr__(self):
        return f'<PriceRecord {self.drug_id}: {self.price}>'


class DrugAlias(Base):
    """药品名称别名模型（用于标准化）"""
    __tablename__ = 'drug_aliases'

    id = Column(Integer, primary_key=True, autoincrement=True)
    drug_id = Column(Integer, ForeignKey('drugs.id'), nullable=False)
    alias_name = Column(String(200), nullable=False, index=True)

    # 关联药品
    drug = relationship('Drug', back_populates='aliases')

    def __repr__(self):
        return f'<DrugAlias {self.alias_name}>'


def init_db(database_url: str) -> tuple:
    """
    初始化数据库，创建所有表结构
    
    Args:
        database_url: 数据库连接URL
        
    Returns:
        tuple: (engine, Session类)
    """
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=engine)
    return engine, SessionLocal


def get_session(database_url: str) -> Session:
    """
    获取数据库会话
    
    Args:
        database_url: 数据库连接URL
        
    Returns:
        Session: 数据库会话实例
    """
    _, SessionLocal = init_db(database_url)
    return SessionLocal()
