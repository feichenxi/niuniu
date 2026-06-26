import os
import sys
import datetime
import colorama
from colorama import Fore, Back, Style, init

colorama.init()
init(autoreset=True)

# 环境配置 - 从 .env 文件或环境变量读取，避免硬编码敏感信息
os.environ.setdefault('CURL_CA_BUNDLE', '')
os.environ.setdefault('HF_ENDPOINT', os.getenv('HF_ENDPOINT', 'https://hf-mirror.com'))

global_BoxText_count = 0
only_domain = os.getenv('POKER_SERVER_DOMAIN', 'localhost')
global_domain = f'http://{only_domain}'

color_map = {
    'green': Fore.GREEN,
    'red': Fore.RED,
    'white': Fore.WHITE,
    'blue': Fore.BLUE,
    'black': Fore.BLACK,
    'yellow': Fore.YELLOW,
    'magenta': Fore.MAGENTA,
    'cyan': Fore.CYAN
}

# 输出文字模块
import inspect


def BoxText(text):
    global global_BoxText_count
    current_time = datetime.datetime.now().strftime('%H:%M:%S')  # 获取当前时间并格式化

    # 根据文本内容设定颜色
    if text.startswith('日志：'):
        color = 'WHITE'
    elif text.startswith('成功：'):
        color = 'GREEN'
    elif text.startswith('错误：'):
        color = 'RED'
    elif text.startswith('警告：'):
        color = 'RED'
    elif text.startswith('重要：'):
        color = 'YELLOW'
    elif text.startswith('消息：'):
        color = 'CYAN'
    elif text.startswith('通知：'):
        color = 'MAGENTA'
    elif text.startswith('输出：'):
        color = 'LIGHTBLACK_EX'
    else:
        color = 'WHITE'

    # 获取当前调用栈的信息
    # caller_frame = inspect.currentframe().f_back
    # (filename, line_number, function_name, lines, index) = inspect.getframeinfo(caller_frame)
    # log_message = f"日志：{filename}:{line_number} - {function_name}. {text}"

    color_code = color_map.get(color.lower(), Fore.WHITE)
    global_BoxText_count += 1
    print(f"{color_code} {global_BoxText_count} [{current_time}] {text}")


# 输出文字模块


# 连接mysql
import mysql.connector
from mysql.connector import Error


def Mysql_Link():
    """建立与MySQL数据库的连接"""
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', only_domain),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'poker'),
            charset='utf8mb4'
        )
        if connection.is_connected():
            # BoxText(f"日志：core.comm.Mysql_Link.成功")
            return connection
    except Error as e:
        BoxText(f"错误：core.comm.Mysql_Link.错误.{e}")
        return None


def Mysql_Row(sql):
    connection = Mysql_Link()
    if not connection:
        BoxText(f"日志：core.comm.Mysql_Link.No database connection established.")
        return

    try:
        cursor = connection.cursor()
        query = sql
        cursor.execute(query)

        # 判断是SELECT、UPDATE还是INSERT
        if sql.strip().upper().startswith("SELECT"):
            # 处理SELECT语句
            column_names = [desc[0] for desc in cursor.description]
            records = cursor.fetchall()
            result = [dict(zip(column_names, row)) for row in records]
        elif sql.strip().upper().startswith("UPDATE") or sql.strip().upper().startswith("INSERT"):
            # 处理UPDATE和INSERT语句
            connection.commit()  # 提交事务
            # 检查是否为插入操作，并返回最后插入的ID
            if sql.strip().upper().startswith("INSERT"):
                result = cursor.lastrowid  # 返回最后插入的ID
            else:
                result = cursor.rowcount  # 返回受影响的行数

        else:
            # 其他类型的SQL语句
            connection.commit()  # 提交事务
            result = cursor.rowcount  # 返回受影响的行数

        return result

    except Error as e:
        BoxText(f"错误：core.comm.Mysql_Link.Error while executing SQL. {e}")
        # BoxText(f"消息：core.comm.Mysql_Link.SQL={sql}")
        return None

    finally:
        cursor.close()
        connection.close()


# 连接mysql


# 当前文件路径
def Abs_Path():
    abs_path = os.path.dirname(os.path.abspath(__file__))
    abs_path = os.path.dirname(abs_path) + "/"
    return abs_path


# 当前文件路径

# 输出详细错误
import sys
import traceback


def Error_Detail(e):
    exc_type, exc_value, exc_traceback = sys.exc_info()
    file_name = exc_traceback.tb_frame.f_code.co_filename
    line_number = exc_traceback.tb_lineno
    BoxText(f"错误：产生错误{e}，错误发生在文件 {file_name} 的第 {line_number} 行。")
    traceback.print_exc()


# 输出详细错误


# 输出硬件信息
import torch
import psutil
import platform


def Device_Info():
    if torch.cuda.is_available():
        # 获取并打印GPU信息
        device = torch.device("cuda")
        gpu_info = []
        for i in range(torch.cuda.device_count()):
            gpu_info.append({
                'Device': torch.cuda.get_device_name(i),
                'Memory Usage': f"{torch.cuda.memory_allocated(i) / 1024 ** 2:.2f} MB / {torch.cuda.get_device_properties(i).total_memory / 1024 ** 2:.2f} MB"
            })

        for info in gpu_info:
            BoxText(f"重要：使用GPU，Using GPU: {info['Device']}，Memory Usage: {info['Memory Usage']}")
    else:
        device = torch.device("cpu")

        # 获取并打印CPU信息
        cpu_info = {
            'Physical cores': psutil.cpu_count(logical=False),
            'Total cores': psutil.cpu_count(logical=True),
            'Max Frequency': f"{psutil.cpu_freq().max:.2f}Mhz",
            'Min Frequency': f"{psutil.cpu_freq().min:.2f}Mhz",
            'Current Frequency': f"{psutil.cpu_freq().current:.2f}Mhz",
            'CPU Usage (%)': f"{psutil.cpu_percent()}%",
            'CPU Info': platform.processor()
        }

        BoxText(f"重要：使用CPU， {cpu_info['CPU Info']}，线程：{cpu_info['Total cores']}")
        # BoxText(f"Physical cores: {cpu_info['Physical cores']}")
        # BoxText(f"Total cores: {cpu_info['Total cores']}")
        # BoxText(f"Max Frequency: {cpu_info['Max Frequency']}")
        # BoxText(f"Min Frequency: {cpu_info['Min Frequency']}")
        # BoxText(f"Current Frequency: {cpu_info['Current Frequency']}")
        # BoxText(f"CPU Usage: {cpu_info['CPU Usage (%)']}")

    return device


# 输出硬件信息


# 唯一标识
from functools import lru_cache
import uuid
import hashlib

@lru_cache(maxsize=1)  # 只缓存最新的结果
def Uuid():
    mac_num = hex(uuid.getnode()).replace('0x', '').upper()
    mac = ':'.join(mac_num[i:i + 2] for i in range(0, 12, 2))
    sha_signature = hashlib.sha256(mac.encode()).hexdigest()
    return sha_signature
# 唯一标识
