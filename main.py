from browser_use import Agent
from browser_use.llm.openai.chat import ChatOpenAI
from browser_use import Browser, BrowserProfile
from dotenv import load_dotenv
import asyncio
import os
import platform

# interpolate=True 添加环境变量中的变量引用
load_dotenv(interpolate=True)

# 设置更长的浏览器启动超时时间
os.environ["TIMEOUT_BrowserStartEvent"] = "120"
os.environ["TIMEOUT_BrowserLaunchEvent"] = "120"
# 60秒导航超时
os.environ["TIMEOUT_NavigateToUrlEvent"] = "60"


async def main():
    llm = ChatOpenAI(
        model=os.getenv("ARK_MODEL_NAME"),
        api_key=os.getenv("ARK_API_KEY"),
        base_url=os.getenv("ARK_BASE_URL"),
        temperature=0,
        dont_force_structured_output=True,  # 不强制使用结构化输出，避免 json_schema 错误，有些模型不支持结构化输出
        add_schema_to_system_prompt=True,  # 将 schema 添加到系统提示中
    )

    task = "打开 https://www.zhihu.com/ 并提取页面标题"

    # 创建浏览器配置 - 禁用默认扩展以加快启动
    browser_profile = BrowserProfile(
        headless=False,
        enable_default_extensions=False,  # 禁用默认扩展，避免下载超时，Google浏览器扩展插件需要翻墙
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
        headless=(system == 'Linux'),  # Linux 使用无头模式，其他系统使用显示模式,
    )

    result = await agent.run()
    
    print("\n" + "="*60)
    print(f"原始结果：{result}")
    print("任务完成！")
    print("="*60)
    
    # 显示最终结果
    if hasattr(result, 'final_result') and result.final_result:
        print(f"\n最终结果：\n{result.final_result}\n")
    elif hasattr(result, 'all_results'):
        for action_result in result.all_results:
            if action_result.extracted_content:
                print(f"\n提取内容：{action_result.extracted_content}")
    
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())