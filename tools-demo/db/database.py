"""
数据库配置模块

该模块负责数据库连接的初始化和管理，支持 MySQL 数据库。

主要功能：
1. 自动创建数据库（如果不存在）
2. 配置 SQLAlchemy 连接
3. 初始化 Flask 应用的数据库连接

配置来源：.env 文件中的数据库相关环境变量
"""

import os
import mysql.connector
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()


def _create_database_if_not_exists():
    """
    检查并创建数据库（如果不存在）
    
    使用 mysql.connector 直接连接 MySQL 服务器，创建指定的数据库。
    如果数据库已存在，则不执行任何操作。
    """
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = int(os.getenv('DB_PORT', 3306))
    db_user = os.getenv('DB_USER', 'root')
    db_password = os.getenv('DB_PASSWORD', '')
    db_name = os.getenv('DB_NAME', 'task_executor_db')
    
    try:
        connection = mysql.connector.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password
        )
        
        cursor = connection.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        
        cursor.close()
        connection.close()
        print(f"Database '{db_name}' is ready")
    
    except Exception as e:
        print(f"Warning: Could not create database automatically: {e}")
        print("   Please create the database manually: CREATE DATABASE task_executor_db")


def init_db(app):
    """
    初始化 Flask 应用的数据库连接
    
    Args:
        app: Flask 应用实例
    """
    _create_database_if_not_exists()
    
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = int(os.getenv('DB_PORT', 3306))
    db_user = os.getenv('DB_USER', 'root')
    db_password = os.getenv('DB_PASSWORD', '')
    db_name = os.getenv('DB_NAME', 'task_executor_db')
    
    app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)