from browser_use import Agent
from browser_use.llm.openai.chat import ChatOpenAI
from browser_use import Browser, BrowserProfile
from browser_use.agent.views import AgentOutput, AgentHistory
from browser_use.browser.views import BrowserStateSummary
from dotenv import load_dotenv
import asyncio
import os
import platform
from typing import List, Dict, Any
from datetime import datetime

# interpolate=True 添加环境变量中的变量引用
load_dotenv(interpolate=True)

# 设置更长的浏览器启动超时时间
os.environ["TIMEOUT_BrowserStartEvent"] = "120"
os.environ["TIMEOUT_BrowserLaunchEvent"] = "120"
# 60秒导航超时
os.environ["TIMEOUT_NavigateToUrlEvent"] = "60"


class RealtimeStepTracker:
    """实时步骤追踪器"""
    
    def __init__(self):
        self.steps: List[Dict[str, Any]] = []
        self.current_step: int = 0
        self.start_time = datetime.now()
    
    def on_new_step(self, browser_state: BrowserStateSummary, agent_output: AgentOutput, step_number: int):
        """
        当新步骤完成时的回调函数
        
        Args:
            browser_state: 当前浏览器状态
            agent_output: 智能体输出
            step_number: 步骤编号
        """
        self.current_step = step_number
        
        step_info = {
            "step_number": step_number,
            "timestamp": datetime.now().isoformat(),
            "url": browser_state.url,
            "thinking": agent_output.thinking,
            "next_goal": agent_output.next_goal,
            "evaluation": agent_output.evaluation_previous_goal,
            "actions": [],
            "success": True,
            "error": None,
            "extracted_content": None
        }
        
        # 解析动作
        for action in agent_output.action:
            action_dict = action.model_dump(exclude_none=True, mode='json')
            step_info["actions"].append(action_dict)
        
        self.steps.append(step_info)
        self._print_step(step_info)
    
    def _print_step(self, step_info: Dict[str, Any]):
        """打印单个步骤的信息"""
        print("\n" + "="*80)
        print(f"[步骤 {step_info['step_number']}] 实时更新")
        print("="*80)
        print(f"时间: {step_info['timestamp']}")
        print(f"URL: {step_info['url']}")
        
        if step_info["thinking"]:
            print(f"\n思考:")
            print(f"   {step_info['thinking']}")
        
        if step_info["evaluation"]:
            print(f"\n上一步评估:")
            print(f"   {step_info['evaluation']}")
        
        if step_info["next_goal"]:
            print(f"\n下一步目标:")
            print(f"   {step_info['next_goal']}")
        
        if step_info["actions"]:
            print(f"\n执行的动作:")
            for action in step_info["actions"]:
                action_name = list(action.keys())[0]
                action_params = action[action_name]
                print(f"   - {action_name}: {action_params}")
        
        print("="*80)
    
    def print_final_summary(self, final_result):
        """打印最终总结"""
        print("\n" + "="*80)
        print("任务完成 - 最终总结")
        print("="*80)
        
        # 总体统计
        total_steps = len(self.steps)
        elapsed_time = (datetime.now() - self.start_time).total_seconds()
        
        print(f"统计:")
        print(f"   总步骤数: {total_steps}")
        print(f"   耗时: {elapsed_time:.2f} 秒")
        print(f"   最终状态: {'成功' if final_result.is_successful() else '失败'}")
        
        if final_result.final_result():
            print(f"\n最终结果:")
            print(f"   {final_result.final_result()}")
        
        print("\n" + "="*80)
        print("步骤概览:")
        print("="*80)
        for step in self.steps:
            status_text = "[OK]" if step["success"] else "[FAIL]"
            print(f"   {status_text} 步骤 {step['step_number']}: {step['url']}")
        print("="*80 + "\n")


async def run_task_realtime(task: str):
    """
    运行任务并实时显示步骤信息
    
    Args:
        task: 任务描述
    """
    llm = ChatOpenAI(
        model=os.getenv("ARK_MODEL_NAME"),
        api_key=os.getenv("ARK_API_KEY"),
        base_url=os.getenv("ARK_BASE_URL"),
        temperature=0,
        dont_force_structured_output=True,
        add_schema_to_system_prompt=True,
    )

    # 创建浏览器配置
    browser_profile = BrowserProfile(
        headless=False,
        enable_default_extensions=False,
        window_size={"width": 1280, "height": 800},
    )
    browser = Browser(browser_profile=browser_profile)

    system = platform.system()
    print(f"当前系统：{system}")
    
    # 创建追踪器
    tracker = RealtimeStepTracker()
    
    print("\n" + "="*80)
    print(f"开始执行任务: {task}")
    print("="*80 + "\n")
    
    # 创建智能体，注册实时回调
    agent = Agent(
        task=task,
        llm=llm,
        browser=browser,
        use_vision=True,
        headless=(system == 'Linux'),
        register_new_step_callback=tracker.on_new_step,
    )

    result = await agent.run()
    
    # 打印最终总结
    tracker.print_final_summary(result)
    
    return tracker.steps, result


if __name__ == "__main__":
    task = "打开 https://www.zhihu.com/ 并提取页面标题"
    asyncio.run(run_task_realtime(task))
