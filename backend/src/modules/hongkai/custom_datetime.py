import datetime
import time
import requests
import json
import os
import sys

# 添加父目录到sys.path以导入config模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# 星期几中文映射
translation_map = {
    'Monday': '星期一',
    'Tuesday': '星期二',
    'Wednesday': '星期三',
    'Thursday': '星期四',
    'Friday': '星期五',
    'Saturday': '星期六',
    'Sunday': '星期日'
}


def get_offline_datetime():
    """
    获取离线状态下的本地日期和时间
    :return: 包含年、月、日、时、分、秒、星期几的字典
    """
    now = datetime.datetime.now()
    weekday_en = now.strftime('%A')
    return {
        'year': now.year,
        'month': now.month,
        'day': now.day,
        'hour': now.hour,
        'minute': now.minute,
        'second': now.second,
        'weekday': weekday_en,  # 星期几的英文名称
        'weekday_cn': translation_map.get(weekday_en, weekday_en),  # 星期几的中文名称
        'datetime': now.strftime('%Y-%m-%d %H:%M:%S'),
        'date': now.strftime('%Y-%m-%d'),
        'time': now.strftime('%H:%M:%S'),
        'status': 'offline'
    }


def get_online_datetime():
    """
    获取在线状态下的准确日期和时间，固定使用中国时间
    :return: 包含年、月、日、时、分、秒、星期几等信息的字典
    """
    try:
        # 使用百度搜索的时间API获取当前时间（中国境内服务）
        url = 'https://www.baidu.com'
        response = requests.get(url, timeout=5)
        response.raise_for_status()  # 检查请求是否成功
        
        # 从响应头中获取时间
        if 'Date' in response.headers:
            date_str = response.headers['Date']
            # 解析HTTP日期格式
            local_datetime = datetime.datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S GMT')
            # 转换为北京时间（UTC+8）
            local_datetime = local_datetime + datetime.timedelta(hours=8)
        else:
            raise Exception("百度响应头中没有Date字段")
        
        weekday_en = local_datetime.strftime('%A')
        
        return {
            'year': local_datetime.year,
            'month': local_datetime.month,
            'day': local_datetime.day,
            'hour': local_datetime.hour,
            'minute': local_datetime.minute,
            'second': local_datetime.second,
            'weekday': weekday_en,
            'weekday_cn': translation_map.get(weekday_en, weekday_en),
            'datetime': local_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            'date': local_datetime.strftime('%Y-%m-%d'),
            'time': local_datetime.strftime('%H:%M:%S'),
            'status': 'online'
        }
    except requests.exceptions.RequestException as e:
        # 网络请求相关错误
        print(f"网络请求失败: {e}")
        return get_offline_datetime()
    except json.JSONDecodeError as e:
        # JSON解析错误
        print(f"时间数据解析失败: {e}")
        return get_offline_datetime()
    except Exception as e:
        # 其他未知错误
        print(f"在线获取时间失败: {e}")
        return get_offline_datetime()


def get_datetime(prefer_online=True):
    """
    获取日期和时间，可选择优先使用在线或离线模式
    :param prefer_online: 是否优先使用在线模式
    :return: 包含日期和时间信息的字典
    """
    if prefer_online:
        return get_online_datetime()
    else:
        return get_offline_datetime()


def save_datetime_data(file_path=None):
    """
    保存日期和时间数据到文件，优先使用在线时间
    同时检测星期并与上一次的日期进行比对，根据比对结果更新config.json中的相应字段
    :param file_path: 保存文件路径，默认保存在time_date文件夹中
    :return: 保存的文件路径
    """
    if file_path is None:
        # 默认保存路径
        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "current_datetime.json")
    
    # 优先获取在线时间
    datetime_data = get_datetime(prefer_online=True)
    
    # 读取上一次的日期数据
    previous_datetime = None
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                previous_datetime = json.load(f)
        except Exception as e:
            print(f"读取上一次日期数据失败: {e}")
    
    # 比较日期并更新config.json
    current_date = datetime_data.get('date')
    current_weekday = datetime_data.get('weekday_cn')
    current_weekday_en = datetime_data.get('weekday')
    
    # 获取当前周数（使用ISO周数）
    current_date_obj = datetime.datetime.strptime(current_date, '%Y-%m-%d')
    current_year, current_week, _ = current_date_obj.isocalendar()
    
    # 检查是否是新的一天
    if previous_datetime:
        previous_date = previous_datetime.get('date')
        previous_weekday = previous_datetime.get('weekday_cn')
        previous_weekday_en = previous_datetime.get('weekday')
        
        # 获取上一次的周数
        previous_date_obj = datetime.datetime.strptime(previous_date, '%Y-%m-%d')
        previous_year, previous_week, _ = previous_date_obj.isocalendar()
        
        # 如果日期不同，设置shenzhijian_done为false
        if current_date != previous_date:
            print(f"检测到新的一天: {current_date}，重置shenzhijian_done为false")
            config.update_config("shenzhijian_done", False)
        
        # 如果是星期一且周数不同，设置letu_level_done为false
        if (current_weekday == "星期一" or current_weekday_en == "Monday") and (current_week != previous_week or current_year != previous_year):
            print(f"检测到新的一周: 第{current_week}周，重置letu_level_done为false")
            config.update_config("letu_level_done", False)
    else:
        # 首次运行，初始化配置
        print("首次运行，初始化配置")
        config.update_config("shenzhijian_done", False)
        if current_weekday == "星期一" or current_weekday_en == "Monday":
            print("当前是星期一，重置letu_level_done为false")
            config.update_config("letu_level_done", False)
    
    # 保存到文件
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(datetime_data, f, ensure_ascii=False, indent=2)
    
    return file_path


if __name__ == "__main__":
    # 示例用法
    print("=== 优先在线模式获取时间(固定中国时间) ===")
    online_time = get_datetime(prefer_online=True)
    print(json.dumps(online_time, ensure_ascii=False, indent=2))
    
    print("\n=== 离线模式获取时间 ===")
    offline_time = get_datetime(prefer_online=False)
    print(json.dumps(offline_time, ensure_ascii=False, indent=2))
    
    # 保存时间数据到文件
    print("\n=== 保存时间数据到文件 ===")
    saved_file = save_datetime_data()
    print(f"时间数据已保存到: {saved_file}")
