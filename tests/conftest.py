"""
pytest配置和fixtures
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base


@pytest.fixture
def engine():
    """创建内存数据库引擎"""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def session(engine):
    """创建数据库会话"""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
