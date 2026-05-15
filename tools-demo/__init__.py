"""
任务执行系统包初始化

该包提供任务执行引擎的核心功能，包括：
- 任务执行代理
- 浏览器自动化操作
- 状态管理
- 工具注册
"""

from .agent import TaskExecutionAgent, run_task_execution

__all__ = ['TaskExecutionAgent', 'run_task_execution']
__version__ = '1.0.0'