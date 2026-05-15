"""
API 路由模块

该模块定义了任务执行系统的 RESTful API 接口，提供任务的 CRUD 操作和执行功能。

主要 API 端点：
- POST /api/tasks - 创建任务
- GET /api/tasks - 获取所有任务列表
- GET /api/tasks/<task_id> - 获取单个任务详情
- POST /api/tasks/<task_id>/execute - 执行任务
- GET /api/tasks/<task_id>/steps - 获取任务步骤列表
- GET /api/tasks/<task_id>/steps/<step_id> - 获取单个步骤
- PUT /api/tasks/<task_id>/steps/<step_id> - 更新步骤状态
- DELETE /api/tasks/<task_id> - 删除任务

辅助函数：
- extract_steps_from_description: 从任务描述中提取步骤
- _llm_split_steps: 使用 LLM 将任务描述拆分为步骤
"""

from flask import Blueprint, request, jsonify
import re
import threading

api_bp = Blueprint('api', __name__)


@api_bp.route('/tasks', methods=['POST'])
def create_task():
    """
    创建新任务
    
    接收任务描述，自动提取步骤并创建任务记录。
    
    Request Body:
        {
            "description": "任务描述文本，支持编号步骤格式",
            "case_name": "用例名称（可选，默认为 'Adhoc Task'）"
        }
    
    Response:
        201 Created: 返回创建的任务对象（包含步骤列表）
        400 Bad Request: 缺少任务描述或描述为空
    """
    from db.models import Task, TaskStep
    from db.database import db
    
    data = request.get_json()
    if not data or 'description' not in data:
        return jsonify({'error': 'Missing task description'}), 400

    description = data['description'].strip()
    if not description:
        return jsonify({'error': 'Task description cannot be empty'}), 400

    case_name = data.get('case_name', 'Adhoc Task')
    
    task = Task(description=description, status='pending', case_name=case_name)
    db.session.add(task)
    db.session.commit()

    steps = extract_steps_from_description(description)
    
    for idx, step_desc in enumerate(steps, 1):
        step = TaskStep(
            task_id=task.id,
            step_number=idx,
            description=step_desc,
            status='pending'
        )
        db.session.add(step)
    
    db.session.commit()

    return jsonify(task.to_dict()), 201


@api_bp.route('/tasks', methods=['GET'])
def get_tasks():
    """
    获取所有任务列表
    
    Response:
        200 OK: 返回任务列表
    """
    from db.models import Task
    
    tasks = Task.query.all()
    return jsonify([task.to_dict() for task in tasks])


@api_bp.route('/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    """
    获取单个任务详情
    
    Args:
        task_id: 任务ID
    
    Response:
        200 OK: 返回任务详情（包含步骤列表）
        404 Not Found: 任务不存在
    """
    from db.models import Task
    
    task = Task.query.get(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    return jsonify(task.to_dict())


@api_bp.route('/tasks/<int:task_id>/steps', methods=['GET'])
def get_task_steps(task_id):
    """
    获取任务的所有步骤
    
    Args:
        task_id: 任务ID
    
    Response:
        200 OK: 返回步骤列表（按步骤编号排序）
        404 Not Found: 任务不存在
    """
    from db.models import Task, TaskStep
    
    task = Task.query.get(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    
    steps = TaskStep.query.filter_by(task_id=task_id).order_by(TaskStep.step_number).all()
    return jsonify([step.to_dict() for step in steps])


@api_bp.route('/tasks/<int:task_id>/execute', methods=['POST'])
def execute_task(task_id):
    """
    执行任务
    
    在后台线程中异步执行任务，避免阻塞请求。
    
    Args:
        task_id: 任务ID
    
    Response:
        200 OK: 任务开始执行
        400 Bad Request: 任务正在执行中
        404 Not Found: 任务不存在
    """
    from db.models import Task, TaskStep
    from db.database import db
    from agent import run_task_execution
    
    task = Task.query.get(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    
    if task.status == 'running':
        return jsonify({'error': 'Task is already running'}), 400

    def run_executor():
        from app import app
        with app.app_context():
            steps = TaskStep.query.filter_by(task_id=task_id).order_by(TaskStep.step_number).all()
            steps_data = [step.to_dict() for step in steps]
            run_task_execution(task_id, task.description, steps_data, db.session)

    thread = threading.Thread(target=run_executor, daemon=True)
    thread.start()

    return jsonify({'message': 'Task execution started', 'task_id': task_id}), 200


@api_bp.route('/tasks/<int:task_id>/steps/<int:step_id>', methods=['GET'])
def get_step(task_id, step_id):
    """
    获取单个步骤详情
    
    Args:
        task_id: 任务ID
        step_id: 步骤ID
    
    Response:
        200 OK: 返回步骤详情
        404 Not Found: 步骤不存在
    """
    from db.models import TaskStep
    
    step = TaskStep.query.filter_by(id=step_id, task_id=task_id).first()
    if not step:
        return jsonify({'error': 'Step not found'}), 404
    return jsonify(step.to_dict())


@api_bp.route('/tasks/<int:task_id>/steps/<int:step_id>', methods=['PUT'])
def update_step_status(task_id, step_id):
    """
    更新步骤状态
    
    Args:
        task_id: 任务ID
        step_id: 步骤ID
    
    Request Body:
        {
            "status": "步骤状态（pending/running/completed/failed/skipped）",
            "result": "执行结果（可选）",
            "error_message": "错误信息（可选）"
        }
    
    Response:
        200 OK: 返回更新后的步骤
        400 Bad Request: 缺少状态或状态无效
        404 Not Found: 步骤不存在
    """
    from db.models import TaskStep
    from db.database import db
    
    step = TaskStep.query.filter_by(id=step_id, task_id=task_id).first()
    if not step:
        return jsonify({'error': 'Step not found'}), 404

    data = request.get_json()
    if 'status' not in data:
        return jsonify({'error': 'Missing status'}), 400

    valid_statuses = ['pending', 'running', 'completed', 'failed', 'skipped']
    if data['status'] not in valid_statuses:
        return jsonify({'error': f'Invalid status. Must be one of: {valid_statuses}'}), 400

    step.status = data['status']
    step.result = data.get('result')
    step.error_message = data.get('error_message')
    db.session.commit()

    return jsonify(step.to_dict())


@api_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """
    删除任务
    
    删除任务及其所有关联的步骤（级联删除）。
    
    Args:
        task_id: 任务ID
    
    Response:
        200 OK: 删除成功
        404 Not Found: 任务不存在
    """
    from db.models import Task
    from db.database import db
    
    task = Task.query.get(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    
    db.session.delete(task)
    db.session.commit()
    
    return jsonify({'message': 'Task deleted successfully'}), 200


def extract_steps_from_description(description):
    """
    从任务描述中提取步骤列表
    
    支持多种格式：
    1. 多行编号列表（如 "1. xxx\n2. xxx"）
    2. 单行编号列表（如 "1. xxx 2. xxx"）
    3. 如果无法提取，使用 LLM 进行智能拆分
    
    Args:
        description: 任务描述文本
    
    Returns:
        list: 步骤描述列表
    """
    if not description:
        return []
    
    normalized_text = str(description).replace('\r\n', '\n').replace('\r', '\n').strip()
    
    numbered_line_pattern = re.compile(r'^\s*(\d+(?:\.\d+)*)[\.\s、:：-]+(.*)$')
    extracted_steps = []
    
    lines = normalized_text.split('\n')
    
    if len(lines) > 1:
        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue
            match = numbered_line_pattern.match(line)
            if match:
                desc = match.group(2).strip()
                if desc:
                    extracted_steps.append(desc)
    else:
        pattern = re.compile(r'(\d+)[\.\s、:：-]+([^\d]*?)(?=\s*\d+[\.\s、:：-]|$)')
        matches = pattern.findall(normalized_text)
        for num, desc in matches:
            desc = desc.strip()
            if desc:
                extracted_steps.append(desc)
    
    if not extracted_steps:
        split_inline_text = re.sub(r'\s+(?=\d+(?:\.\d+)*[\.\s、:：-]+)', '\n', normalized_text)
        if split_inline_text != normalized_text:
            return extract_steps_from_description(split_inline_text)
    
    if len(extracted_steps) <= 1:
        llm_steps = _llm_split_steps(normalized_text)
        if llm_steps and len(llm_steps) > 1:
            return llm_steps
    
    return extracted_steps or [description]


def _llm_split_steps(task_description):
    """
    使用 LLM 将任务描述拆分为步骤列表
    
    Args:
        task_description: 任务描述文本
    
    Returns:
        list: 步骤描述列表（失败返回 None）
    """
    try:
        from browser_use.llm.openai.chat import ChatOpenAI
        import os
        import json
        import re
        
        llm = ChatOpenAI(
            model=os.getenv('MODEL_NAME'),
            api_key=os.getenv('AUTH_TOKEN'),
            base_url=os.getenv('BASE_URL'),
            temperature=0.0,
            dont_force_structured_output=True,
            add_schema_to_system_prompt=False,
        )
        
        prompt = f"""请将以下任务拆分成具体的步骤列表。返回一个JSON数组，包含每个步骤的描述。

任务：{task_description}

输出格式：["步骤1描述", "步骤2描述", "步骤3描述"]
"""
        
        import asyncio
        response = asyncio.run(llm.ainvoke(prompt))
        content = response.content.strip()
        
        match = re.search(r'\[.*\]', content, re.DOTALL)
        if match:
            try:
                steps = json.loads(match.group(0))
                if isinstance(steps, list) and len(steps) > 0:
                    cleaned_steps = []
                    for step in steps:
                        s = str(step).strip()
                        s = re.sub(r'^\d+[\.\s、:：-]+', '', s)
                        if s:
                            cleaned_steps.append(s)
                    return cleaned_steps
            except json.JSONDecodeError:
                pass
        
        lines = content.split('\n')
        steps = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith('```'):
                line = re.sub(r'^\d+[\.\s、:：-]+', '', line)
                steps.append(line.strip())
        
        return steps if len(steps) > 1 else None
        
    except Exception as e:
        print(f"LLM split error: {e}")
        return None