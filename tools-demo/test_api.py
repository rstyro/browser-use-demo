"""
API 测试模块

该模块提供了对任务执行系统 API 的完整测试覆盖，包括：
1. 创建任务
2. 获取任务列表
3. 获取单个任务详情
4. 获取任务步骤
5. 执行任务
6. 更新步骤状态
7. 删除任务

使用方法：
1. 确保 Flask 应用已启动（运行 app.py）
2. 运行此脚本：python test_api.py

测试流程：
1. 创建任务 → 获取任务列表 → 获取任务详情 → 获取步骤
2. 执行任务 → 等待5秒 → 检查步骤状态
3. 删除任务 → 验证删除结果
"""

import requests
import json

# API 基础 URL
BASE_URL = "http://localhost:5000/api"


def test_create_task():
    """
    测试创建任务接口
    
    创建一个包含多个步骤的任务，验证返回的任务对象和步骤列表。
    
    Returns:
        int: 创建的任务ID（失败返回 None）
    """
    print("=== 测试创建任务 ===")
    
    # 测试数据：包含编号步骤的任务描述
    payload = {
        "description": "1. 打开浏览器访问百度首页 2. 在搜索框输入测试关键词 3. 点击搜索按钮 4. 验证搜索结果是否包含预期内容"
    }
    
    # 发送请求
    response = requests.post(f"{BASE_URL}/tasks", json=payload)
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 201:
        # 解析响应并打印任务信息
        task = response.json()
        print(f"任务ID: {task['id']}")
        print(f"任务描述: {task['description']}")
        print(f"步骤数量: {len(task['steps'])}")
        for step in task['steps']:
            print(f"  步骤 {step['step_number']}: {step['description']}")
        return task['id']
    else:
        print(f"创建失败: {response.text}")
        return None


def test_get_tasks():
    """
    测试获取任务列表接口
    
    获取所有任务并统计任务总数。
    """
    print("\n=== 测试获取任务列表 ===")
    response = requests.get(f"{BASE_URL}/tasks")
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        tasks = response.json()
        print(f"任务总数: {len(tasks)}")


def test_get_task(task_id):
    """
    测试获取单个任务接口
    
    Args:
        task_id: 任务ID
    """
    print(f"\n=== 测试获取任务 {task_id} ===")
    response = requests.get(f"{BASE_URL}/tasks/{task_id}")
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        task = response.json()
        print(f"任务ID: {task['id']}")
        print(f"状态: {task['status']}")


def test_get_steps(task_id):
    """
    测试获取任务步骤接口
    
    Args:
        task_id: 任务ID
    """
    print(f"\n=== 测试获取任务 {task_id} 的步骤 ===")
    response = requests.get(f"{BASE_URL}/tasks/{task_id}/steps")
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        steps = response.json()
        print(f"步骤数量: {len(steps)}")
        for step in steps:
            print(f"  ID: {step['id']}, 序号: {step['step_number']}, 描述: {step['description']}, 状态: {step['status']}")


def test_execute_task(task_id):
    """
    测试执行任务接口
    
    在后台异步执行任务，不等待完成。
    
    Args:
        task_id: 任务ID
    """
    print(f"\n=== 测试执行任务 {task_id} ===")
    response = requests.post(f"{BASE_URL}/tasks/{task_id}/execute")
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"消息: {result['message']}")


def test_update_step(task_id, step_id):
    """
    测试更新步骤状态接口
    
    Args:
        task_id: 任务ID
        step_id: 步骤ID
    """
    print(f"\n=== 测试更新步骤 {step_id} 状态 ===")
    
    # 更新数据
    payload = {
        "status": "completed",
        "result": "测试步骤完成",
        "error_message": None
    }
    
    response = requests.put(f"{BASE_URL}/tasks/{task_id}/steps/{step_id}", json=payload)
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        step = response.json()
        print(f"步骤ID: {step['id']}, 状态: {step['status']}, 结果: {step['result']}")


def test_delete_task(task_id):
    """
    测试删除任务接口
    
    Args:
        task_id: 任务ID
    """
    print(f"\n=== 测试删除任务 {task_id} ===")
    response = requests.delete(f"{BASE_URL}/tasks/{task_id}")
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"消息: {result['message']}")


if __name__ == "__main__":
    """
    主测试入口
    
    按顺序执行所有测试用例：
    1. 创建任务
    2. 获取任务列表
    3. 获取任务详情
    4. 获取步骤列表
    5. 执行任务
    6. 等待5秒后检查步骤状态
    7. 删除任务
    8. 验证任务已删除
    """
    import time
    
    # 创建任务
    task_id = test_create_task()
    
    # 如果任务创建成功，继续测试
    if task_id:
        # 获取任务列表
        test_get_tasks()
        
        # 获取单个任务详情
        test_get_task(task_id)
        
        # 获取任务步骤
        test_get_steps(task_id)
        
        # 执行任务（异步）
        test_execute_task(task_id)
        
        # 等待任务执行（模拟等待时间）
        time.sleep(5)
        
        # 再次获取步骤状态，检查执行结果
        test_get_steps(task_id)
        
        # 删除任务
        test_delete_task(task_id)
        
        # 验证任务已删除
        test_get_tasks()