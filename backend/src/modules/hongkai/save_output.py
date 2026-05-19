#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动输出记录工具
功能：在导入模块后自动记录所有print语句的输出到控制台和日志文件
使用方法：import all_log.save_output 或 from all_log.save_output import save_log
"""

import os
import sys
import time
import traceback


# 全局变量存储日志文件路径
_log_file_path = None

# 原始的print函数
_original_print = print

def _get_caller_info():
    """
    获取调用文件的信息
    
    :return: 调用文件名（不含扩展名）
    """
    caller_file = None
    # 遍历调用栈找到第一个非save_output.py的文件
    for frame_info in traceback.extract_stack():
        file_path = frame_info[0]
        if os.path.basename(file_path) != 'save_output.py':
            caller_file = file_path
            break
    
    if caller_file:
        caller_filename = os.path.basename(caller_file)
        return os.path.splitext(caller_filename)[0]
    return 'unknown'

def clean_old_logs():
    """
    清理超过30天的日志文件
    """
    # 日志目录
    log_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 当前时间
    current_time = time.time()
    
    # 30天的秒数
    thirty_days = 30 * 24 * 60 * 60
    
    # 遍历日志目录
    for filename in os.listdir(log_dir):
        if filename.endswith('.log'):
            file_path = os.path.join(log_dir, filename)
            
            # 获取文件的修改时间
            mod_time = os.path.getmtime(file_path)
            
            # 计算文件的年龄
            file_age = current_time - mod_time
            
            # 如果文件超过30天，则删除
            if file_age > thirty_days:
                try:
                    os.remove(file_path)
                    _original_print(f"[日志清理] 删除过期日志文件: {filename}")
                except Exception as e:
                    _original_print(f"[日志清理] 删除文件失败 {filename}: {e}")

def save_log(message):
    """
    将日志信息保存到文件并在控制台显示
    
    :param message: 日志消息内容
    :return: 无
    """
    global _log_file_path
    
    # 日志目录（固定为save_output.py所在的目录）
    log_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 清理过期日志
    if _log_file_path is None:
        clean_old_logs()
    
    # 如果日志文件路径尚未设置，则创建日志文件
    if _log_file_path is None:
        # 获取调用文件的信息
        caller_name = _get_caller_info()
        
        # 日志文件名（格式：调用文件名_YYYYMMDD_HHMMSS.log）
        timestamp = time.strftime('%Y%m%d_%H%M%S', time.localtime())
        log_filename = f'{caller_name}_{timestamp}.log'
        _log_file_path = os.path.join(log_dir, log_filename)
    
    # 日志格式：[YYYY-MM-DD HH:MM:SS] 消息内容
    log_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    log_entry = f"[{log_time}] {message}"
    
    try:
        # 输出到控制台
        _original_print(log_entry)
        
        # 写入到日志文件
        with open(_log_file_path, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')
    except UnicodeEncodeError:
        # 处理编码错误
        try:
            # 尝试使用utf-8编码输出
            log_entry_encoded = log_entry.encode('utf-8', 'replace').decode('utf-8')
            _original_print(log_entry_encoded)
            with open(_log_file_path, 'a', encoding='utf-8') as f:
                f.write(log_entry_encoded + '\n')
        except Exception as e:
            pass

def _custom_print(*args, **kwargs):
    """
    自定义的print函数，会将输出同时记录到日志文件
    
    :param args: print函数的位置参数
    :param kwargs: print函数的关键字参数
    :return: 无
    """
    try:
        # 将print的参数转换为字符串
        output_str = ' '.join(map(str, args))
        
        # 调用save_log函数记录日志
        save_log(output_str)
    except Exception as e:
        # 处理异常，确保程序不会因为日志记录失败而崩溃
        try:
            _original_print(f"[日志错误] 记录日志失败: {e}")
        except:
            pass

# 替换内置的print函数
def _override_print():
    """
    替换内置的print函数为自定义的print函数
    """
    import builtins
    builtins.print = _custom_print

# 模块导入时自动替换print函数
_override_print()


# 示例用法
if __name__ == "__main__":
    # 测试自动记录print输出
    print("程序开始执行")
    print("处理数据中...")
    print("注意：资源不足")
    print("错误：操作失败")
    print("调试信息：变量x=10")
    
    # 测试手动调用save_log
    save_log("这是手动调用save_log的日志")
    
    print("\n日志记录完成！")
    print("日志文件格式示例：调用文件名_YYYYMMDD_HHMMSS.log")
    print("使用方法1：import all_log.save_output")
    print("使用方法2：from all_log.save_output import save_log")
    print("示例：print('这是一条自动记录的输出')")
    print("示例：save_log('这是一条手动记录的日志')")
    
    # 测试清理过期日志
    print("\n测试清理过期日志...")
    clean_old_logs()
    print("日志清理完成！")
