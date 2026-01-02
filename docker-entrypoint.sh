#!/bin/bash
set -e

# 等待数据库准备就绪（如果使用外部数据库）
if [ "$DATABASE_URL" != "sqlite:///data/pharma_prices.db" ]; then
    echo "等待数据库连接..."
    python -c "
import time
import sys
from sqlalchemy import create_engine
from config import DATABASE_URL

max_tries = 30
for i in range(max_tries):
    try:
        engine = create_engine(DATABASE_URL)
        engine.connect()
        print('数据库连接成功!')
        break
    except Exception as e:
        if i == max_tries - 1:
            print(f'数据库连接失败: {e}')
            sys.exit(1)
        print(f'等待数据库... ({i+1}/{max_tries})')
        time.sleep(2)
"
fi

# 初始化数据库
echo "初始化数据库..."
python -c "
from app.models import init_db
from config import DATABASE_URL

try:
    engine, SessionLocal = init_db(DATABASE_URL)
    print('数据库表创建完成!')
except Exception as e:
    print(f'数据库初始化失败: {e}')
    import traceback
    traceback.print_exc()
"

# 启动应用
echo "启动医药价格发现系统..."
exec "$@"