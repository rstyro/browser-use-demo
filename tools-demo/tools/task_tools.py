"""
任务工具模块

该模块定义了 Agent 可用的工具函数，包括状态更新、标签页操作等。

核心工具：
- mark_task_complete: 标记步骤完成
- mark_task_failed: 标记步骤失败
- mark_task_skipped: 标记步骤跳过
- update_task_status: 更新步骤状态
- close_tab: 关闭标签页
- check_stop: 检查是否需要停止
- Done: 任务完成
"""

import logging
import asyncio

logger = logging.getLogger(__name__)


class TaskTools:
    """
    任务工具类
    负责注册和管理 Agent 可用的工具函数。
    """
    
    def __init__(self, status_manager, placeholder_checker, emit_callback):
        """
        初始化任务工具
        
        Args:
            status_manager: 状态管理器实例
            placeholder_checker: 占位符 URL 检查函数
            emit_callback: 回调函数
        """
        self.status_manager = status_manager
        self.placeholder_checker = placeholder_checker
        self.emit_callback = emit_callback
    
    def register_tools(self, tools):
        """
        注册所有工具到工具注册表
        
        Args:
            tools: Tools 实例
        """
        @tools.action('Done')
        async def done(success: bool = True, text: str = ""):
            return f"任务完成: {text}"
        
        @tools.action('check_stop')
        async def check_stop(should_stop: bool = False):
            if should_stop:
                logger.info("🛑 Agent 请求停止执行")
            return f"stop_checked: {should_stop}"
        
        @tools.action('close_tab')
        async def close_tab(browser_session=None):
            return await self._close_tab(browser_session)
        
        @tools.action('mark_task_complete')
        async def mark_task_complete(task_id: int, result: str = None):
            return await self._mark_task_complete(task_id, result)
        
        @tools.action('mark_task_failed')
        async def mark_task_failed(task_id: int, error_message: str = None):
            return await self._mark_task_failed(task_id, error_message)
        
        @tools.action('mark_task_skipped')
        async def mark_task_skipped(task_id: int):
            return await self._mark_task_skipped(task_id)
        
        @tools.action('update_task_status')
        async def update_task_status(task_id: int, status: str, result: str = None, error_message: str = None):
            return await self._update_task_status(task_id, status, result, error_message)
    
    async def _close_tab(self, browser_session):
        """
        关闭当前标签页
        
        Args:
            browser_session: 浏览器会话
        
        Returns:
            str: 操作结果
        """
        from browser_use.browser.events import CloseTabEvent, SwitchTabEvent
        
        if browser_session is None or browser_session.agent_focus_target_id is None:
            raise ValueError("没有活跃的标签页可关闭")
        
        target_id = browser_session.agent_focus_target_id
        
        async def find_preferred_fallback_tab(browser_session, exclude_target_id=None):
            tabs = await browser_session.get_tabs()
            candidate_tabs = [tab for tab in tabs if tab.target_id != exclude_target_id]
            if not candidate_tabs:
                return None
            non_placeholder_tabs = [tab for tab in candidate_tabs if not self.placeholder_checker(getattr(tab, 'url', ''))]
            return (non_placeholder_tabs or candidate_tabs)[-1]
        
        fallback_tab = None
        try:
            fallback_tab = await find_preferred_fallback_tab(browser_session, exclude_target_id=target_id)
        except Exception as e:
            logger.warning(f"确定备选标签页失败: {e}")
        
        event = browser_session.event_bus.dispatch(CloseTabEvent(target_id=target_id))
        await event
        
        if fallback_tab is not None:
            try:
                await asyncio.sleep(0.15)
                if browser_session.agent_focus_target_id != fallback_tab.target_id:
                    await browser_session.event_bus.dispatch(
                        SwitchTabEvent(target_id=fallback_tab.target_id)
                    )
            except Exception as e:
                logger.warning(f"切换到备选标签页失败: {e}")
        
        return f"已关闭标签页 {target_id[-4:]}"
    
    async def _mark_task_complete(self, task_id, result=None):
        """
        标记步骤完成
        
        Args:
            task_id: 步骤编号
            result: 执行结果
        
        Returns:
            str: 操作结果
        """
        logger.info(f"✅ 标记步骤 step_id={task_id} 完成")
        await self.emit_callback({'task_id': task_id, 'status': 'completed', 'result': result})
        return f"步骤 {task_id} 已标记完成"
    
    async def _mark_task_failed(self, task_id, error_message=None):
        """
        标记步骤失败
        
        Args:
            task_id: 步骤编号
            error_message: 错误信息
        
        Returns:
            str: 操作结果
        """
        logger.info(f"❌ 标记步骤 step_id={task_id} 失败")
        await self.emit_callback({'task_id': task_id, 'status': 'failed', 'error_message': error_message})
        return f"步骤 {task_id} 已标记失败"
    
    async def _mark_task_skipped(self, task_id):
        """
        标记步骤跳过
        
        Args:
            task_id: 步骤编号
        
        Returns:
            str: 操作结果
        """
        logger.info(f"⏭️ 标记步骤 step_id={task_id} 跳过")
        await self.emit_callback({'task_id': task_id, 'status': 'skipped'})
        return f"步骤 {task_id} 已标记跳过"
    
    async def _update_task_status(self, task_id, status, result=None, error_message=None):
        """
        更新步骤状态
        
        Args:
            task_id: 步骤编号
            status: 状态值
            result: 执行结果
            error_message: 错误信息
        
        Returns:
            str: 操作结果
        """
        normalized_status = str(status).strip().lower()
        if normalized_status not in {'completed', 'failed', 'skipped', 'in_progress'}:
            raise ValueError(f"不支持的状态: {status}")
        
        logger.info(f"🔄 更新步骤 step_id={task_id} 状态为 {normalized_status}")
        await self.emit_callback({
            'task_id': task_id,
            'status': normalized_status,
            'result': result,
            'error_message': error_message
        })
        return f"步骤 {task_id} 已更新为 {normalized_status}"