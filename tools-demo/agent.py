"""
任务执行代理模块

该模块实现了基于 browser-use 的任务执行引擎，支持：
1. 任务描述解析和步骤拆分
2. 浏览器自动化操作（每个任务独立实例）
3. 步骤状态回调更新（任务级隔离）
4. 执行日志记录

核心特性：
- 任务隔离：每个任务使用独立的浏览器实例
- 状态隔离：步骤状态更新基于 task_id + step_number 唯一标识
- 并发安全：支持多个任务同时执行而不互相干扰

核心组件：
- TaskExecutionAgent: 任务执行代理主类
- run_task_execution: 执行任务同步入口函数
"""

import logging
import asyncio
import os
import re
import uuid
import inspect
from datetime import datetime
from dotenv import load_dotenv
from collections import OrderedDict

from browser.profile import BrowserProfileFactory
from status.manager import StatusManager
from tools.task_tools import TaskTools

logger = logging.getLogger(__name__)
os.environ['ANONYMIZED_TELEMETRY'] = 'false'
os.environ["TIMEOUT_BrowserStartEvent"] = "120"
os.environ["TIMEOUT_BrowserLaunchEvent"] = "120"
os.environ["TIMEOUT_NavigateToUrlEvent"] = "60"
load_dotenv(interpolate=True)

running_tasks = OrderedDict()
task_lock = asyncio.Lock()


class TaskExecutionAgent:
    """
    任务执行代理类
    负责执行自动化任务，管理浏览器操作和步骤状态更新。
    
    Args:
        task_id: 任务ID（来自数据库）
        task_description: 任务描述
        steps: 预拆分的步骤列表
        db_session: 数据库会话
    """
    
    def __init__(self, task_id, task_description, steps, db_session):
        self.task_id = task_id
        self.task_description = task_description
        self.steps = steps
        self.db_session = db_session
        self.execution_id = str(uuid.uuid4())[:8]
        
        self.browser_profile_factory = BrowserProfileFactory(task_id, self.execution_id)
        self.status_manager = StatusManager(task_id, steps, db_session)
        self.browser = None
        
        logger.info(f"任务 {task_id} 初始化完成，执行ID: {self.execution_id}")
    
    def _format_action(self, action):
        """
        格式化动作描述，用于日志输出
        
        Args:
            action: 动作对象
        
        Returns:
            str: 格式化后的动作描述
        """
        try:
            action_dict = {}
            if hasattr(action, 'model_dump'):
                action_dict = action.model_dump()
            elif hasattr(action, '_action_dict'):
                action_dict = action._action_dict
            elif hasattr(action, '_dict'):
                action_dict = action._dict
            elif isinstance(action, dict):
                action_dict = action
            else:
                return str(action)
            
            if not action_dict:
                return "待机"
            
            descriptions = []
            for name, params in action_dict.items():
                if not params and name not in ['scroll_down', 'scroll_up', 'done']:
                    continue
                
                if name in ['go_to_url', 'navigate']:
                    url = params.get('url') if isinstance(params, dict) else params
                    descriptions.append(f"访问: {url}")
                elif name in ['click_element', 'click']:
                    index = params.get('index') if isinstance(params, dict) else params
                    descriptions.append(f"点击[{index}]")
                elif name in ['input_text', 'input']:
                    text = params.get('text') if isinstance(params, dict) else None
                    descriptions.append(f"输入: '{text}'")
                elif name == 'switch_tab':
                    index = params.get('index', params)
                    descriptions.append(f"切换标签 {index}")
                elif name == 'open_new_tab':
                    url = params.get('url', params)
                    descriptions.append(f"新标签打开: {url}")
                elif name == 'close_tab':
                    descriptions.append("关闭当前标签页")
                elif name == 'done':
                    descriptions.append("任务完成")
                else:
                    descriptions.append(f"{name}")
            return " | ".join(descriptions)
        except:
            return "执行操作"
    
    def _build_task_prompt(self):
        """
        构建最终任务提示词
        
        Returns:
            str: 完整的任务提示词
        """
        final_task = self.task_description
        
        if self.steps:
            final_task += "\n\n重要指令：\n"
            final_task += "你有一个子任务列表，请严格按顺序执行。\n"
            final_task += "关键：在确定每个子任务结果后，必须立即调用 'mark_task_complete(task_id=N)'、'mark_task_failed(task_id=N)'、'mark_task_skipped(task_id=N)' 或 'update_task_status(task_id=N, status=\"...\")'。\n"
            final_task += "子任务（按顺序执行）：\n"
            
            cleaned_tasks = []
            for t in self.steps:
                desc = t.get('description', '')
                while True:
                    match = re.match(r'^\s*\d+[\.\s、:]+(.*)', desc)
                    if not match:
                        break
                    desc = match.group(1).strip()
                cleaned_tasks.append(f"{t['step_number']}. {desc}")
            
            final_task += "\n".join(cleaned_tasks)
        
        final_task += f"\n\n当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        final_task += "\n关键规则：\n"
        final_task += "1. 完成后标记：仅在成功完成任务 N 后调用 'mark_task_complete(task_id=N)'。\n"
        final_task += "2. 标记当前任务：始终标记刚刚完成的任务。\n"
        final_task += "3. 不要跳过：每个子任务必须以明确的状态更新结束。\n"
        final_task += "4. 示例：[{click: {...}}, {mark_task_complete: {task_id: 1}}]\n"
        final_task += "5. 全部完成后：当所有子任务都完成时，立即调用 {Done: {success: true, text: '任务已完成'}} 结束任务。\n"
        final_task += "6. 任务结束：调用 Done 动作后，Agent 将停止执行。\n"
        
        return final_task
    
    async def execute(self):
        """
        执行任务主入口
        
        Returns:
            dict: 执行结果 {'task_id', 'status', 'duration', 'error'}
        """
        from browser_use import Agent, Browser, Tools
        from browser_use.llm.openai.chat import ChatOpenAI
        
        async with task_lock:
            if self.task_id in running_tasks:
                logger.warning(f"任务 {self.task_id} 已在执行中，跳过")
                return {'task_id': self.task_id, 'status': 'failed', 'error': 'Task already running'}
            running_tasks[self.task_id] = {
                'execution_id': self.execution_id,
                'status': 'running',
                'start_time': datetime.now()
            }
        
        self.status_manager.log(f"开始执行任务: {self.task_description} (执行ID: {self.execution_id})")
        self.status_manager.update_task_status('running')
        
        start_time = datetime.now()
        result = None
        
        try:
            llm = ChatOpenAI(
                model=os.getenv('MODEL_NAME'),
                api_key=os.getenv('AUTH_TOKEN'),
                base_url=os.getenv('BASE_URL'),
                temperature=float(os.getenv('TEMPERATURE', '0.0')),
                dont_force_structured_output=True,
                add_schema_to_system_prompt=True,
            )
            
            tools = Tools()
            
            async def emit_callback(payload):
                if payload.get('task_id'):
                    step_number = payload['task_id']
                    status = payload.get('status', 'completed')
                    result = payload.get('result')
                    error_message = payload.get('error_message')
                    self.status_manager.update_step_status(step_number, status, result, error_message)
                    if self.steps:
                        for step in self.steps:
                            if step.get('step_number') == step_number:
                                step['status'] = status
                                if result:
                                    step['result'] = result
                                if error_message:
                                    step['error_message'] = error_message
                                break
                elif payload.get('type') == 'log' and payload.get('content'):
                    self.status_manager.log(f"步骤日志: {payload['content'][:100]}...")
            
            task_tools = TaskTools(
                self.status_manager,
                self.browser_profile_factory.is_placeholder_url,
                emit_callback
            )
            task_tools.register_tools(tools)
            
            browser_profile = self.browser_profile_factory.create()
            self.browser = Browser(browser_profile=browser_profile)
            
            agent = Agent(
                task=self._build_task_prompt(),
                llm=llm,
                browser=self.browser,
                tools=tools,
                use_vision=False,
                headless=os.name == 'posix',
                max_actions_per_step=10,
                max_retries=1,
                max_failures=2,
                llm_timeout=60,
                step_timeout=90,
                generate_gif=False,
            )
            
            current_step_index = 0
            last_processed_history_len = 0
            task_completed = False
            done_action_detected = False
            stop_execution = False
            done_exception = None
            
            async def on_step_end(agent_instance):
                nonlocal current_step_index, last_processed_history_len, task_completed, done_action_detected, stop_execution, done_exception
                
                if stop_execution:
                    return
                
                history = getattr(agent_instance, 'history', [])
                if hasattr(history, 'history'):
                    history = history.history
                
                new_actions = []
                if len(history) > last_processed_history_len:
                    for i in range(last_processed_history_len, len(history)):
                        step = history[i]
                        try:
                            if hasattr(step, 'model_output') and hasattr(step.model_output, 'action'):
                                raw = step.model_output.action
                                actions = raw if isinstance(raw, list) else [raw]
                                new_actions.extend(actions)
                                
                                action_str = " | ".join([self._format_action(a) for a in actions])
                                log_content = f"\n[步骤 {i + 1}]\n执行: {action_str}\n"
                                self.status_manager.log(log_content)
                        except Exception as e:
                            logger.warning(f"步骤结束处理错误: {e}")
                    last_processed_history_len = len(history)
                
                for action in new_actions:
                    action_dict = action.model_dump() if hasattr(action, 'model_dump') else getattr(action, '_action_dict', {})
                    
                    # 打印action_dict
                    self.status_manager.log(f"action==: {action}")

                    if 'Done' in action_dict or 'done' in action_dict:
                        done_action_detected = True
                        stop_execution = True
                        self.status_manager.log("检测到 Done 动作，任务即将结束")
                        done_exception = Exception("Done action detected - stopping execution")
                        raise done_exception
                    
                    if 'mark_task_complete' in action_dict:
                        task_id = action_dict['mark_task_complete'].get('task_id')
                        result_data = action_dict['mark_task_complete'].get('result')
                        if task_id:
                            await emit_callback({'task_id': int(task_id), 'status': 'completed', 'result': result_data})
                            if self.steps:
                                completed_count = sum(1 for s in self.steps if s.get('status') == 'completed')
                                if completed_count >= len(self.steps):
                                    task_completed = True
                                    self.status_manager.log("所有步骤已完成，任务即将结束")
                    elif 'mark_task_failed' in action_dict:
                        task_id = action_dict['mark_task_failed'].get('task_id')
                        error_message = action_dict['mark_task_failed'].get('error_message')
                        if task_id:
                            await emit_callback({'task_id': int(task_id), 'status': 'failed', 'error_message': error_message})
                    elif 'mark_task_skipped' in action_dict:
                        task_id = action_dict['mark_task_skipped'].get('task_id')
                        if task_id:
                            await emit_callback({'task_id': int(task_id), 'status': 'skipped'})
                    elif 'update_task_status' in action_dict:
                        payload = action_dict['update_task_status']
                        task_id = payload.get('task_id')
                        status = payload.get('status', 'completed')
                        result_data = payload.get('result')
                        error_message = payload.get('error_message')
                        if task_id:
                            await emit_callback({
                                'task_id': int(task_id),
                                'status': status,
                                'result': result_data,
                                'error_message': error_message
                            })
                    else:
                        action_name = list(action_dict.keys())[0] if action_dict else str(action)
                        if action_name in ['go_to_url', 'navigate', 'click_element', 'click', 'input_text', 'input']:
                            if current_step_index < len(self.steps):
                                step_num = self.steps[current_step_index].get('step_number', current_step_index + 1)
                                self.status_manager.update_step_status(step_num, 'in_progress')
                                
                                if action_name in ['go_to_url', 'navigate']:
                                    current_step_index += 1
                                    if current_step_index <= len(self.steps):
                                        prev_step_num = self.steps[current_step_index - 1].get('step_number', current_step_index)
                                        self.status_manager.update_step_status(prev_step_num, 'completed')
                                        if current_step_index >= len(self.steps):
                                            task_completed = True
                                            self.status_manager.log("所有步骤已完成，任务即将结束")
            
            try:
                sig = inspect.signature(agent.run)
                max_execution_steps = len(self.steps) * 2 + 3
                self.status_manager.log(f"最大执行步骤数: {max_execution_steps}")
                
                if 'on_step_end' in sig.parameters:
                    self.status_manager.log("设置回调函数: on_step_end")
                    result = await agent.run(
                        max_steps=max_execution_steps,
                        on_step_end=on_step_end
                    )
                else:
                    result = await agent.run(max_steps=max_execution_steps)
            except KeyboardInterrupt:
                result = None
            except Exception as e:
                if done_action_detected and "Done action detected" in str(e):
                    self.status_manager.log("Done 动作异常中断，被捕获")
                    result = None
                else:
                    logger.error(f"代理执行错误: {e}")
                    raise
            
            if task_completed or done_action_detected:
                self.status_manager.log("任务提前完成，跳过后续检查")
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                self.status_manager.update_task_status('completed', end_time, duration)
                return {'task_id': self.task_id, 'status': 'completed', 'duration': duration}
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            all_completed = all(step.get('status') == 'completed' for step in self.steps) if self.steps else True
            
            if all_completed:
                self.status_manager.update_task_status('completed', end_time, duration)
                self.status_manager.log(f"任务执行成功，耗时 {duration:.2f} 秒")
                result = {'task_id': self.task_id, 'status': 'completed', 'duration': duration}
            else:
                self.status_manager.update_task_status('failed', end_time, duration)
                self.status_manager.log("任务执行失败")
                result = {'task_id': self.task_id, 'status': 'failed', 'duration': duration}
                
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            self.status_manager.update_task_status('failed', end_time, duration)
            error_msg = f"任务执行错误: {str(e)}"
            self.status_manager.log(error_msg)
            result = {'task_id': self.task_id, 'status': 'failed', 'error': error_msg}
        
        finally:
            async with task_lock:
                if self.task_id in running_tasks:
                    del running_tasks[self.task_id]
            
            if self.browser:
                try:
                    self.browser.close()
                    logger.info(f"任务 {self.task_id} 浏览器实例已关闭")
                except:
                    pass
            
            self.browser_profile_factory.cleanup()
            self.status_manager.log(f"任务 {self.task_id} 执行完成，资源已清理")
        
        return result


def run_task_execution(task_id, task_description, steps, db_session):
    """
    运行任务执行的同步入口函数
    
    Args:
        task_id: 任务ID
        task_description: 任务描述
        steps: 步骤列表
        db_session: 数据库会话
    
    Returns:
        dict: 执行结果
    """
    agent = TaskExecutionAgent(task_id, task_description, steps, db_session)
    return asyncio.run(agent.execute())