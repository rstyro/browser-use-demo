# Task Executor Service

基于 Flask + browser-use 的任务执行服务，支持任务描述拆分、LLM分析、真实浏览器操作执行和步骤状态回调。

## 功能特性

- **任务创建**: 接收任务描述片段，自动拆分为多个步骤并存入 MySQL
- **步骤查询**: 通过 API 接口返回步骤明细
- **任务执行**: 使用 browser-use 执行真实浏览器操作
- **状态回调**: 执行过程中通过回调机制实时更新步骤完成状态到数据库

## 技术栈

- Python 3.8+
- Flask 2.3.3
- Flask-SQLAlchemy 3.1.1
- browser-use 0.2.26
- langchain-openai 0.1.6
- MySQL 5.7+

## 安装依赖

```bash
cd d:\demo_code_repo\testhub_platform\demo
pip install -r requirements.txt
```

## 配置环境

修改 `.env` 文件：

```env
# MySQL Configuration
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=task_executor_db

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=5000

# LLM Configuration
AUTH_TOKEN=your-api-key
BASE_URL=https://api.example.com/v1
MODEL_NAME=gpt-4o-mini
PROVIDER=openai
TEMPERATURE=0.0
```

## 创建数据库

```sql
CREATE DATABASE task_executor_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

## 启动服务

```bash
python app.py
```

服务将在 `http://localhost:5000` 启动。

## API 接口

### 1. 创建任务

**POST** `/api/tasks`

请求体：
```json
{
    "description": "1. 打开浏览器访问百度首页 2. 在搜索框输入测试关键词 3. 点击搜索按钮 4. 验证搜索结果",
    "case_name": "百度搜索测试"
}
```

响应：
```json
{
    "id": 1,
    "description": "1. 打开浏览器访问百度首页 2. 在搜索框输入测试关键词...",
    "status": "pending",
    "case_name": "百度搜索测试",
    "steps": [
        {"id": 1, "step_number": 1, "description": "打开浏览器访问百度首页", "status": "pending"},
        {"id": 2, "step_number": 2, "description": "在搜索框输入测试关键词", "status": "pending"},
        ...
    ]
}
```

### 2. 获取所有任务

**GET** `/api/tasks`

### 3. 获取单个任务

**GET** `/api/tasks/{task_id}`

### 4. 获取任务步骤

**GET** `/api/tasks/{task_id}/steps`

### 5. 执行任务

**POST** `/api/tasks/{task_id}/execute`

响应：
```json
{
    "message": "Task execution started",
    "task_id": 1
}
```

### 6. 获取单个步骤

**GET** `/api/tasks/{task_id}/steps/{step_id}`

### 7. 更新步骤状态

**PUT** `/api/tasks/{task_id}/steps/{step_id}`

请求体：
```json
{
    "status": "completed",
    "result": "步骤执行成功",
    "error_message": null
}
```

### 8. 删除任务

**DELETE** `/api/tasks/{task_id}`

## 步骤状态说明

| 状态 | 说明 |
|------|------|
| `pending` | 待执行 |
| `running` | 执行中 |
| `completed` | 已完成 |
| `failed` | 失败 |
| `skipped` | 跳过 |

## 项目结构

```
demo/
├── app.py              # Flask 应用入口
├── models.py           # 数据库模型 (Task, TaskStep)
├── routes.py           # API 路由
├── ai_agent.py         # AI 代理（集成 browser-use 和 LLM）
├── .env                # 环境配置
├── requirements.txt    # 依赖列表
├── README.md           # 项目说明
└── test_api.py         # API 测试脚本
```

## 工作流程

```
┌─────────────────────────────────────────────────────────────────┐
│  1. 创建任务                                                   │
│     POST /api/tasks → 提取步骤 → 存入 MySQL                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. 获取步骤                                                   │
│     GET /api/tasks/{id}/steps → 返回步骤明细                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. 执行任务                                                   │
│     POST /api/tasks/{id}/execute                               │
│         │                                                      │
│         ▼                                                      │
│     ┌─────────────────────────────────────────────────────┐    │
│     │ TaskExecutionAgent                                  │    │
│     │ ├─ 初始化 LLM                                      │    │
│     │ ├─ 创建 browser-use Agent                          │    │
│     │ ├─ 注册回调函数 (mark_task_complete等)              │    │
│     │ ├─ 执行浏览器操作                                   │    │
│     │ └─ 通过回调更新数据库步骤状态                        │    │
│     └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## 核心实现

`ai_agent.py` 中的关键组件：

1. **LLM 初始化**: 使用 langchain-openai 连接大语言模型
2. **浏览器配置**: 自动检测系统并配置 Chrome 浏览器参数
3. **Controller**: 注册自定义动作（mark_task_complete, mark_task_failed 等）
4. **回调机制**: 通过 emit_callback 更新数据库中的步骤状态
5. **on_step_end**: 监控每步执行，解析动作并触发回调

## 测试示例

```bash
# 创建任务
curl -X POST http://localhost:5000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"description": "1. 访问百度首页 2. 搜索关键词 3. 验证结果"}'

# 获取步骤明细
curl http://localhost:5000/api/tasks/1/steps

# 执行任务（会打开真实浏览器执行）
curl -X POST http://localhost:5000/api/tasks/1/execute

# 查看任务状态（包含执行日志）
curl http://localhost:5000/api/tasks/1
```

## browser-use 集成说明

服务使用 browser-use 库执行真实浏览器操作：

- **Agent**: 核心执行引擎，接收任务描述和 LLM
- **Controller**: 注册自定义动作供 LLM 调用
- **BrowserProfile**: 浏览器配置（无头模式/显示模式）
- **事件系统**: 处理标签页关闭、切换等事件

执行过程中，LLM 通过调用 `mark_task_complete(task_id=N)` 等动作通知服务更新步骤状态，服务通过回调将状态写入数据库。
