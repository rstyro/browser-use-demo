from browser_use import Agent
from browser_use.llm.openai.chat import ChatOpenAI
from browser_use import Browser, BrowserProfile
from dotenv import load_dotenv
import asyncio
import os
import platform
from typing import List, Dict, Any

# interpolate=True 添加环境变量中的变量引用
load_dotenv(interpolate=True)

# 设置更长的浏览器启动超时时间
os.environ["TIMEOUT_BrowserStartEvent"] = "120"
os.environ["TIMEOUT_BrowserLaunchEvent"] = "120"
# 60秒导航超时
os.environ["TIMEOUT_NavigateToUrlEvent"] = "60"


def format_steps(history_list) -> List[Dict[str, Any]]:
    """
    将任务历史拆分为可读的步骤列表，并包含每个步骤的状态信息
    
    Returns:
        包含步骤详情的字典列表
    """
    steps = []
    
    for idx, history_item in enumerate(history_list.history):
        step_info = {
            "step_number": idx + 1,
            "url": history_item.state.url if history_item.state else None,
            "success": True,
            "error": None,
            "extracted_content": None,
            "actions": [],
            "next_goal": None,
            "thinking": None,
            "evaluation": None
        }
        
        # 添加模型输出信息
        if history_item.model_output:
            step_info["thinking"] = history_item.model_output.thinking
            step_info["next_goal"] = history_item.model_output.next_goal
            step_info["evaluation"] = history_item.model_output.evaluation_previous_goal
            
            # 解析每个动作
            for action in history_item.model_output.action:
                action_dict = action.model_dump(exclude_none=True, mode='json')
                step_info["actions"].append(action_dict)
        
        # 添加结果信息
        for result in history_item.result:
            if result.error:
                step_info["error"] = result.error
                step_info["success"] = False
            if result.extracted_content:
                step_info["extracted_content"] = result.extracted_content
        
        steps.append(step_info)
    
    return steps


def print_steps_summary(steps: List[Dict[str, Any]]):
    """打印步骤的详细摘要"""
    print("\n" + "="*80)
    print("任务步骤摘要")
    print("="*80)
    
    for step in steps:
        status = "✅ 成功" if step["success"] else "❌ 失败"
        print(f"\n步骤 {step['step_number']}: {status}")
        print(f"  URL: {step['url']}")
        
        if step["thinking"]:
            print(f"  思考: {step['thinking']}")
        if step["next_goal"]:
            print(f"  下一步目标: {step['next_goal']}")
        if step["evaluation"]:
            print(f"  上一步评估: {step['evaluation']}")
        
        if step["actions"]:
            print("  执行的动作:")
            for action in step["actions"]:
                action_name = list(action.keys())[0]
                action_params = action[action_name]
                print(f"    - {action_name}: {action_params}")
        
        if step["extracted_content"]:
            print(f"  提取内容: {step['extracted_content']}")
        if step["error"]:
            print(f"  错误: {step['error']}")


async def run_task_with_tracking(task: str):
    """
    运行任务并显示详细的步骤追踪信息
    
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
    
    # 创建智能体
    agent = Agent(
        task=task,
        llm=llm,
        browser=browser,
        use_vision=True,
        headless=(system == 'Linux'),
    )

    result = await agent.run()
    
    print("\n" + "="*80)
    print("任务执行完成")
    print("="*80)
    
    # 拆分任务步骤并显示状态
    steps = format_steps(result)
    print_steps_summary(steps)
    
    # 总体统计
    print("\n" + "="*80)
    print("总体统计")
    print("="*80)
    total_steps = len(steps)
    successful_steps = sum(1 for s in steps if s["success"])
    print(f"总步骤数: {total_steps}")
    print(f"成功步骤: {successful_steps}")
    print(f"失败步骤: {total_steps - successful_steps}")
    print(f"最终状态: {'成功' if result.is_successful() else '失败'}")
    
    # 显示最终结果
    if result.final_result():
        print(f"\n最终结果：\n{result.final_result()}\n")
    
    print("="*80 + "\n")
    
    return steps, result


if __name__ == "__main__":
    task = "打开 https://www.zhihu.com/ 并提取页面标题"
    asyncio.run(run_task_with_tracking(task))
