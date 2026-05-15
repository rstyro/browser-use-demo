"""
浏览器配置模块

该模块负责创建和配置浏览器实例，支持 Windows 和 Linux 操作系统。
每个任务使用独立的用户数据目录，确保任务隔离。

核心功能：
- 根据操作系统自动查找 Chrome 浏览器路径
- 配置浏览器启动参数
- 创建任务专属的浏览器配置文件
"""

import os
import platform
import logging

logger = logging.getLogger(__name__)


class BrowserProfileFactory:
    """
    浏览器配置工厂类
    负责创建任务专属的浏览器配置。
    """
    
    def __init__(self, task_id, execution_id):
        """
        初始化浏览器配置工厂
        
        Args:
            task_id: 任务ID
            execution_id: 执行ID
        """
        self.task_id = task_id
        self.execution_id = execution_id
        self.user_data_dir = self._create_user_data_dir()
    
    def _create_user_data_dir(self):
        """
        创建任务专属的用户数据目录
        
        Returns:
            str: 用户数据目录路径
        """
        user_data_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            '.browser_data',
            f'task_{self.task_id}_{self.execution_id}'
        )
        os.makedirs(user_data_dir, exist_ok=True)
        return user_data_dir
    
    def _find_chrome_path(self):
        """
        根据操作系统查找 Chrome 浏览器路径
        
        Returns:
            str: Chrome 浏览器可执行文件路径（如果找到）
        """
        system = platform.system()
        
        if system == 'Windows':
            paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
            ]
        elif system == 'Linux':
            paths = [
                '/usr/bin/chromium-browser',
                '/usr/bin/chromium',
                '/usr/bin/google-chrome',
                '/usr/bin/google-chrome-stable',
                '/opt/google/chrome/chrome',
                '/snap/bin/chromium',
            ]
        else:
            logger.warning(f"不支持的操作系统: {system}")
            return None
        
        for path in paths:
            if os.path.exists(path) and (system == 'Windows' or os.access(path, os.X_OK)):
                return path
        
        logger.warning("未找到 Chrome 浏览器路径")
        return None
    
    def _get_base_args(self):
        """
        获取基础浏览器启动参数
        
        Returns:
            list: 浏览器启动参数列表
        """
        return [
            '--disable-blink-features=AutomationControlled',
            '--disable-infobars',
            '--disable-notifications',
            '--disable-background-networking',
            '--disable-background-timer-throttling',
            '--disable-renderer-backgrounding',
            '--disable-backgrounding-occluded-windows',
            '--disable-extensions',
            '--disable-web-security',
            f'--user-data-dir={self.user_data_dir}',
            '--no-first-run',
            '--no-default-browser-check',
            '--disable-component-update',
        ]
    
    def _get_system_specific_args(self):
        """
        获取特定操作系统的浏览器参数
        
        Returns:
            list: 操作系统特定参数列表
        """
        system = platform.system()
        
        if system == 'Linux':
            return [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--headless=new',
                '--disable-software-rasterizer',
                '--remote-debugging-port=0',
                '--no-zygote',
                '--single-process',
            ]
        else:
            return [
                '--no-sandbox',
                '--disable-gpu',
                '--remote-debugging-port=0',
            ]
    
    def create(self):
        """
        创建浏览器配置对象
        
        Returns:
            BrowserProfile: 浏览器配置对象
        """
        from browser_use import BrowserProfile
        
        chrome_path = self._find_chrome_path()
        args = self._get_base_args() + self._get_system_specific_args()
        
        profile = BrowserProfile(
            headless=(platform.system() == 'Linux'),
            disable_security=True,
            executable_path=chrome_path,
            args=args,
            wait_for_network_idle_page_load_time=0.2,
            minimum_wait_page_load_time=0.05,
            wait_between_actions=0.1,
            enable_default_extensions=False,
            user_data_dir=self.user_data_dir,
        )
        
        logger.info(f"🔧 任务 {self.task_id} 浏览器配置创建完成，用户数据目录: {self.user_data_dir}")
        return profile
    
    def cleanup(self):
        """
        清理任务执行后的浏览器数据目录
        """
        try:
            import shutil
            if os.path.exists(self.user_data_dir):
                shutil.rmtree(self.user_data_dir)
                logger.info(f"🗑️ 任务 {self.task_id} 临时数据目录已清理: {self.user_data_dir}")
        except Exception as e:
            logger.warning(f"清理任务 {self.task_id} 浏览器数据时出错: {e}")
    
    def is_placeholder_url(self, url: str) -> bool:
        """
        判断是否为占位符 URL
        
        Args:
            url: URL 字符串
        
        Returns:
            bool: 是否为占位符 URL
        """
        normalized = (url or '').strip().lower()
        return (
            not normalized
            or normalized == 'about:blank'
            or normalized.startswith('chrome://newtab')
            or normalized.startswith('edge://newtab')
        )