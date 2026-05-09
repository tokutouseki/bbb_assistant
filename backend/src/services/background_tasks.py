import threading
import time
import logging
import schedule
from typing import Dict, Any, Callable, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class BackgroundTaskManager:
    """后台任务管理器"""
    
    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.scheduled_tasks: Dict[str, Any] = {}
        self.running = False
        self.thread: Optional[threading.Thread] = None
        logger.info("后台任务管理器初始化完成")
    
    def start(self):
        """启动任务管理器"""
        if self.running:
            logger.warning("后台任务管理器已在运行中")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        logger.info("后台任务管理器已启动")
    
    def stop(self):
        """停止任务管理器"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5.0)
            self.thread = None
        logger.info("后台任务管理器已停止")
    
    def _run_scheduler(self):
        """运行调度器循环"""
        while self.running:
            try:
                schedule.run_pending()
            except Exception as e:
                logger.error(f"调度器执行错误: {e}")
            
            time.sleep(1)
    
    def register_task(self, task_id: str, task_func: Callable, 
                     interval_seconds: Optional[int] = None,
                     cron_expression: Optional[str] = None) -> bool:
        """
        注册后台任务
        
        Args:
            task_id: 任务ID
            task_func: 任务函数
            interval_seconds: 执行间隔（秒）
            cron_expression: Cron表达式
            
        Returns:
            是否成功
        """
        if task_id in self.tasks:
            logger.warning(f"任务已存在: {task_id}")
            return False
        
        task_info = {
            "id": task_id,
            "function": task_func,
            "interval": interval_seconds,
            "cron": cron_expression,
            "last_run": None,
            "run_count": 0,
            "enabled": True
        }
        
        self.tasks[task_id] = task_info
        
        # 调度任务
        if interval_seconds:
            schedule.every(interval_seconds).seconds.do(
                self._execute_task_wrapper, task_id
            ).tag(task_id)
        elif cron_expression:
            # 简化Cron支持
            schedule.every().day.at(cron_expression).do(
                self._execute_task_wrapper, task_id
            ).tag(task_id)
        
        logger.info(f"注册后台任务: {task_id}")
        return True
    
    def _execute_task_wrapper(self, task_id: str):
        """任务执行包装器"""
        if task_id not in self.tasks:
            logger.error(f"任务不存在: {task_id}")
            return
        
        task_info = self.tasks[task_id]
        if not task_info["enabled"]:
            return
        
        try:
            start_time = time.time()
            logger.info(f"开始执行任务: {task_id}")
            
            # 执行任务
            task_info["function"]()
            
            # 更新任务状态
            task_info["last_run"] = datetime.now()
            task_info["run_count"] += 1
            
            elapsed = time.time() - start_time
            logger.info(f"任务完成: {task_id}, 耗时: {elapsed:.2f}s")
            
        except Exception as e:
            logger.error(f"任务执行失败 ({task_id}): {e}")
    
    def unregister_task(self, task_id: str) -> bool:
        """
        取消注册任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功
        """
        if task_id not in self.tasks:
            logger.warning(f"任务不存在: {task_id}")
            return False
        
        # 取消调度
        schedule.clear(task_id)
        
        # 移除任务
        del self.tasks[task_id]
        
        logger.info(f"取消注册任务: {task_id}")
        return True
    
    def enable_task(self, task_id: str) -> bool:
        """启用任务"""
        if task_id in self.tasks:
            self.tasks[task_id]["enabled"] = True
            logger.info(f"启用任务: {task_id}")
            return True
        return False
    
    def disable_task(self, task_id: str) -> bool:
        """禁用任务"""
        if task_id in self.tasks:
            self.tasks[task_id]["enabled"] = False
            logger.info(f"禁用任务: {task_id}")
            return True
        return False
    
    def run_task_now(self, task_id: str) -> bool:
        """
        立即运行任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功
        """
        if task_id not in self.tasks:
            logger.error(f"任务不存在: {task_id}")
            return False
        
        # 在新线程中运行任务，避免阻塞
        thread = threading.Thread(
            target=self._execute_task_wrapper,
            args=(task_id,),
            daemon=True
        )
        thread.start()
        
        logger.info(f"立即运行任务: {task_id}")
        return True
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        if task_id not in self.tasks:
            return None
        
        task_info = self.tasks[task_id]
        return {
            "id": task_id,
            "enabled": task_info["enabled"],
            "last_run": task_info["last_run"],
            "run_count": task_info["run_count"],
            "interval": task_info["interval"],
            "cron": task_info["cron"]
        }
    
    def list_tasks(self) -> Dict[str, Dict[str, Any]]:
        """列出所有任务"""
        return {task_id: self.get_task_status(task_id) 
                for task_id in self.tasks.keys()}
    
    def cleanup_old_data(self):
        """清理旧数据任务"""
        logger.info("开始清理旧数据")
        
        # TODO: 实际清理逻辑
        # 例如：删除旧的日志文件、清理临时文件等
        
        time.sleep(1)  # 模拟清理工作
        logger.info("旧数据清理完成")
    
    def backup_database(self):
        """备份数据库任务"""
        logger.info("开始备份数据库")
        
        # TODO: 实际备份逻辑
        
        time.sleep(2)  # 模拟备份工作
        logger.info("数据库备份完成")
    
    def update_knowledge_base(self):
        """更新知识库任务"""
        logger.info("开始更新知识库")
        
        # TODO: 实际更新逻辑
        
        time.sleep(3)  # 模拟更新工作
        logger.info("知识库更新完成")
    
    def health_check(self):
        """健康检查任务"""
        logger.info("执行健康检查")
        
        # TODO: 实际健康检查逻辑
        
        time.sleep(0.5)
        logger.info("健康检查完成")
    
    def register_default_tasks(self):
        """注册默认任务"""
        # 每小时清理一次旧数据
        self.register_task(
            task_id="cleanup_old_data",
            task_func=self.cleanup_old_data,
            interval_seconds=3600  # 1小时
        )
        
        # 每天凌晨2点备份数据库
        self.register_task(
            task_id="backup_database",
            task_func=self.backup_database,
            cron_expression="02:00"
        )
        
        # 每6小时更新知识库
        self.register_task(
            task_id="update_knowledge_base",
            task_func=self.update_knowledge_base,
            interval_seconds=21600  # 6小时
        )
        
        # 每5分钟健康检查
        self.register_task(
            task_id="health_check",
            task_func=self.health_check,
            interval_seconds=300  # 5分钟
        )
        
        logger.info("默认任务已注册")