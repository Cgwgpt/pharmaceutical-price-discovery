"""
应用启动入口
"""
import os
from app import create_app

app = create_app()

if __name__ == '__main__':
    # Cloud Run使用PORT环境变量
    port = int(os.environ.get('PORT', 5001))
    print("=" * 50)
    print("医药价格发现系统")
    print(f"访问地址: http://0.0.0.0:{port}")
    print("=" * 50)
    app.run(debug=False, host='0.0.0.0', port=port)
