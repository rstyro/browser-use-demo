# Browser Use Demo 项目文档

## 项目概述

这是一个基于 `browser-use` 库的浏览器自动化DEMO项目，集成了火山引擎（Volc Engine）的豆包 AI 模型。


## 快速开始

```bash
# 下载项目代码
git clone https://github.com/rstyro/browser-use-demo.git 
# 进入项目目录
cd browser-use-demo

# 如果uv未安装，先安装uv 包管理器, 安装命令为：
npm install uv

# 安装依赖
uv sync
# 运行项目
python main.py
```

## 项目创建与使用

### 第一步：环境准备

#### 1.1 安装 Python

确保你的系统安装了 Python 3.12 或更高版本：

```bash
python --version
```

#### 1.2 安装 uv 包管理器

本项目使用 `uv` 作为包管理器（快速的 Python 包管理工具）：

**Windows (PowerShell):**
```powershell
npm install uv
```

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 第二步：项目创建

#### 2.1 创建项目目录

```bash
mkdir browser-use-demo
cd browser-use-demo
```

#### 2.2 初始化项目

使用 uv 初始化项目：

```bash
uv init

# 添加依赖
# browser-use: 浏览器自动化库
# langchain-openai: OpenAI 模型
# python-dotenv: 环境变量加载库
uv add browser-use langchain-openai python-dotenv

# 安装依赖
uv sync
```

这会创建虚拟环境并安装所有依赖。

### 第三步：配置环境变量

#### 3.1 创建 .env 文件

在项目根目录创建 `.env` 文件：

```env
# 使用的是火山引擎
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/coding/v3
ARK_API_KEY=${ARK_API_KEY}
ARK_MODEL_NAME=doubao-seed-2.0-pro
```

#### 3.2 获取火山引擎 API Key

1. 访问 [火山引擎控制台](https://console.volcengine.com/ark)
2. 注册并登录账号
3. 创建 API Key（ARK_API_KEY）
4. 在系统环境变量中设置 `ARK_API_KEY`，或者直接在 `.env` 中填入你的 API Key

### 第四步：编写主程序

创建 `main.py` 文件，内容如下：

```python
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
        model=os.getenv("VOLC_MODEL_ENDPOINT"),
        api_key=os.getenv("VOLC_API_KEY"),
        base_url=os.getenv("VOLC_BASE_URL"),
        temperature=0,
        dont_force_structured_output=True,
        add_schema_to_system_prompt=True,
    )

    # 任务描述
    task = "打开 https://www.zhihu.com/ 并提取页面标题"

    # 创建浏览器配置
    browser_profile = BrowserProfile(
        headless=False,
        # 禁用默认扩展，因为安装扩展访问 Google 扩展商店需要翻墙
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
        headless=(system == 'Linux'), # Linux 默认启用无头模式
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
```

### 第五步：运行项目

#### 5.1 激活虚拟环境

**Windows (PowerShell):**
```powershell
.venv\Scripts\Activate.ps1
```

**Windows (CMD):**
```cmd
.venv\Scripts\activate.bat
```

**macOS/Linux:**
```bash
source .venv/bin/activate
```

#### 5.2 运行程序

```bash
python main.py
```

或者使用 uv 直接运行：

```bash
uv run python main.py
```


