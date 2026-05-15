"""
Flask 应用入口

该模块创建并配置 Flask 应用，初始化数据库，注册 API 路由。

主要功能：
1. 加载环境变量配置
2. 初始化 Flask 应用和数据库连接
3. 注册 API 蓝图
4. 创建数据库表（如果不存在）
5. 启动开发服务器

运行方式：
- 在 demo 目录下: python app.py
- 在父目录下: python -m demo.app
"""

import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from flask import Flask
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

from db import init_db, db
init_db(app)

from api import api_bp
app.register_blueprint(api_bp, url_prefix='/api')

with app.app_context():
    from db.models import Task, TaskStep
    db.create_all()
    print("Database tables created successfully")

if __name__ == '__main__':
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    
    app.run(host=host, port=port, debug=debug)