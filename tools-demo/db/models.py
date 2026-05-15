"""
数据库模型模块

该模块定义了任务执行系统的核心数据库模型：
- Task: 任务模型，存储任务的基本信息和执行状态
- TaskStep: 任务步骤模型，存储任务的各个子步骤

模型关系：
- Task 与 TaskStep 是一对多关系（一个任务包含多个步骤）
- 步骤级联删除：删除任务时自动删除关联的步骤
"""

from datetime import datetime
from .database import db


class Task(db.Model):
    """
    任务模型
    
    表示一个自动化任务，包含任务描述、执行状态、执行时间等信息。
    
    Attributes:
        id: 任务唯一标识（主键）
        description: 任务描述文本
        status: 任务状态（pending/running/completed/failed）
        case_name: 用例名称，默认为 'Adhoc Task'
        execution_mode: 执行模式，默认为 'text'
        start_time: 任务开始时间
        end_time: 任务结束时间
        duration: 执行时长（秒）
        logs: 执行日志
        created_at: 创建时间
        updated_at: 更新时间
        steps: 关联的步骤列表（一对多关系）
    """
    
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')
    case_name = db.Column(db.String(200), default='Adhoc Task')
    execution_mode = db.Column(db.String(20), default='text')
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    duration = db.Column(db.Float)
    logs = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    steps = db.relationship('TaskStep', backref='task', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        """
        将任务对象转换为字典格式，便于 JSON 序列化
        
        Returns:
            dict: 包含任务所有字段的字典，包括关联的步骤列表
        """
        return {
            'id': self.id,
            'description': self.description,
            'status': self.status,
            'case_name': self.case_name,
            'execution_mode': self.execution_mode,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration': self.duration,
            'logs': self.logs,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'steps': [step.to_dict() for step in self.steps]
        }


class TaskStep(db.Model):
    """
    任务步骤模型
    
    表示任务的一个子步骤，记录步骤编号、描述、执行状态和结果。
    
    Attributes:
        id: 步骤唯一标识（主键）
        task_id: 关联的任务ID（外键）
        step_number: 步骤编号（从1开始）
        description: 步骤描述文本
        status: 步骤状态（pending/running/completed/failed/skipped）
        result: 执行结果
        error_message: 错误信息（如果失败）
        created_at: 创建时间
        updated_at: 更新时间
    """
    
    __tablename__ = 'task_steps'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    step_number = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')
    result = db.Column(db.Text)
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """
        将步骤对象转换为字典格式，便于 JSON 序列化
        
        Returns:
            dict: 包含步骤所有字段的字典
        """
        return {
            'id': self.id,
            'task_id': self.task_id,
            'step_number': self.step_number,
            'description': self.description,
            'status': self.status,
            'result': self.result,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }