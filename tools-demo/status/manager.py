"""
状态管理模块

该模块负责管理任务和步骤的状态更新，提供与数据库交互的封装。

核心功能：
- 更新步骤状态（包括结果和错误信息）
- 更新任务状态
- 记录执行日志
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class StatusManager:
    """
    状态管理器类
    负责更新任务和步骤的状态到数据库。
    """
    
    def __init__(self, task_id, steps, db_session):
        """
        初始化状态管理器
        
        Args:
            task_id: 任务ID
            steps: 步骤列表
            db_session: 数据库会话
        """
        self.task_id = task_id
        self.steps = steps
        self.db_session = db_session
        self.execution_log = []
    
    def log(self, message):
        """
        记录执行日志
        
        Args:
            message: 日志消息
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        self.execution_log.append(log_entry)
        logger.info(log_entry)
    
    def update_step_status(self, step_number, status, result=None, error_message=None):
        """
        更新步骤状态到数据库
        
        Args:
            step_number: 步骤编号
            status: 步骤状态 (pending/running/completed/failed/skipped)
            result: 执行结果
            error_message: 错误信息
        """
        from db.models import TaskStep
        
        try:
            step = self.db_session.query(TaskStep).filter(
                TaskStep.task_id == self.task_id,
                TaskStep.step_number == step_number
            ).first()
            
            if step:
                if step.status == 'completed':
                    self.log(f"步骤 {step_number} 状态已是 'completed'，取消这次更新status={status}")
                    return
                step.status = status
                step.result = result
                step.error_message = error_message
                self.db_session.commit()
                self.log(f"步骤 {step_number} 状态更新为 '{status}'")
        except Exception as e:
            self.log(f"更新步骤 {step_number} 状态失败: {str(e)}")
    
    def update_task_status(self, status, end_time=None, duration=None):
        """
        更新任务状态到数据库
        
        Args:
            status: 任务状态 (pending/running/completed/failed)
            end_time: 结束时间
            duration: 执行时长（秒）
        """
        from db.models import Task
        
        try:
            task = self.db_session.query(Task).filter(Task.id == self.task_id).first()
            if task:
                task.status = status
                if end_time:
                    task.end_time = end_time
                if duration:
                    task.duration = duration
                task.logs = '\n'.join(self.execution_log)
                self.db_session.commit()
                self.log(f"任务 {self.task_id} 状态更新为 '{status}'")
        except Exception as e:
            self.log(f"更新任务状态失败: {str(e)}")
    
    def get_execution_logs(self):
        """
        获取执行日志
        
        Returns:
            list: 执行日志列表
        """
        return self.execution_log