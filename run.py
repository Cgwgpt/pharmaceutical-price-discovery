"""
应用启动入口
"""
from app import create_app

app = create_app()

if __name__ == '__main__':
    print("=" * 50)
    print("医药价格发现系统")
    print("访问地址: http://127.0.0.1:5001")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5001)
