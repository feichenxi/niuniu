import core.config
from core.comm import *
import subprocess
import time
import re
import win32gui, win32ui, win32process, win32api
import win32con
from pywinauto import Application
import pyautogui
import pygetwindow as gw
from screeninfo import get_monitors
from ctypes import wintypes
import ctypes
import threading
import tkinter as tk
from PIL import Image, ImageTk
import random


# 全局参数

# 获取窗口句柄
def Get_Window_Handle(Partial_Title, Process_Name):
    def Callback(hwnd, hwnds):
        if win32gui.IsWindowVisible(hwnd) and Partial_Title.lower() in win32gui.GetWindowText(hwnd).lower():
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                h_process = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ, False,
                                                 pid)
                exe_name = win32process.GetModuleFileNameEx(h_process, 0).lower()
                if Process_Name.lower() in exe_name:
                    placement = win32gui.GetWindowPlacement(hwnd)
                    if placement[1] != win32con.SW_SHOWMINIMIZED:
                        hwnds.append(hwnd)
            except Exception as e:
                BoxText(f"错误：Get_Window_Handle错误.Error checking window {hwnd}: {e}")
        return True

    hwnds = []
    win32gui.EnumWindows(Callback, hwnds)
    return hwnds[0] if hwnds else None


# 获取窗口句柄

# 通用点击 ~ 相关
# def Window_Rect(hwnd):
#     try:
#         rect = win32gui.GetWindowRect(hwnd)
#         x, y, w, h = rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1]
#         return x, y, w, h
#     except Exception as e:
#         BoxText(f"日志：Window_Rect.An error occurred: {e}")
#         return None


# def Window_Scale(orig_shape, window_rect, xy):
#     orig_h, orig_w = orig_shape[:2]  # 注意这里假设 orig_shape 是 (height, width)
#     win_x, win_y, win_w, win_h = window_rect
#     scaled_x = int(win_x + (xy[0] / orig_w) * win_w)
#     scaled_y = int(win_y + (xy[1] / orig_h) * win_h)
#     return scaled_x, scaled_y


def Win_Click_Xy(results, class_name, win):
    coordinates = []
    if core.config.Win_Dot_Status:
        name_to_id = {v: k for k, v in results.names.items()}
        class_id = name_to_id.get(class_name)
        if class_id is None or results.boxes is None:
            return []

        for box in results.boxes:
            if box.cls.item() == class_id:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                coordinates.append((center_x, center_y))
                # Win_Click_Pyautogui(win=win, xy=(center_x, center_y))
                Win_Click_Win32api(win=win, xy=(center_x, center_y))
                BoxText(fr"重要：窗口{win}，按钮{class_name}，Win_Click_Xy，----------------窗口点击")
    else:
        # BoxText(fr"错误：窗口{win}，按钮{class_name}，Win_Click_Xy，未点击开始执行....")
        pass

    return coordinates

# 通用点击 ~ 相关


# 通用点击 ~ 鼠标
# 全局变量用于存储最近一次点击的时间戳
last_click_time = {}
click_lock = threading.Lock()
interval = 0.3  # 点击间隔时间

def Win_Click_Win32api(win, xy):
    def click_thread():
        global last_click_time
        current_time = time.time()

        # 获取当前窗口最后点击的时间，如果没有则初始化为0
        with click_lock:
            last_click = last_click_time.get(win, 0)

            # 检查是否已经过了冷却时间
            if current_time - last_click >= interval:
                try:
                    hwnd = win32gui.FindWindow(None, win)
                    if hwnd:
                        if not win32gui.IsIconic(hwnd):
                            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                            win32gui.SetForegroundWindow(hwnd)
                            win32gui.BringWindowToTop(hwnd)

                        window_rect = win32gui.GetWindowRect(hwnd)
                        if window_rect:
                            x_offset, y_offset = window_rect[0], window_rect[1]
                            screen_x = xy[0] + x_offset
                            screen_y = xy[1] + y_offset
                            win32api.SetCursorPos((screen_x, screen_y))
                            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                            BoxText(fr"重要：===============Win_Click_Win32api，正常，{win}，xy={xy}")
                            # 更新最后点击的时间戳
                            last_click_time[win] = current_time
                        else:
                            BoxText(fr"错误：===============Win_Click_Win32api，窗口，{win}，获取窗口矩形失败")
                    else:
                        BoxText(fr"错误：===============Win_Click_Win32api，窗口，{win}，hwnd错误")
                except Exception as e:
                    BoxText(fr"错误：===============Win_Click_Win32api，异常，{e}")
            else:
                BoxText(fr"信息：===============Win_Click_Win32api，窗口，{win}，冷却中")

        time.sleep(interval)  # 线程休眠以避免频繁创建线程

    threading.Thread(target=click_thread).start()

def Win_Click_Pyautogui(win, xy):
    try:
        x, y = xy
        app = Application().connect(path="dnplayer.exe")
        main_window = app.window(title_re=f".*{win}.*")  # 根据实际标题正则表达式调整
        rect = main_window.rectangle()
        absolute_x = rect.left + x
        absolute_y = rect.top + y
        pyautogui.click(x=absolute_x, y=absolute_y)
    except Exception as e:
        pass
        # print(f"发生错误: {e}")


def Win_Click_See(hwnd, x_offset, y_offset):
    icon_path = fr"model\dot.png"
    duration = 0.25
    rect = win32gui.GetWindowRect(hwnd)
    x, y = rect[0] + x_offset, rect[1] + y_offset
    root = tk.Toplevel()
    root.overrideredirect(True)
    root.attributes('-topmost', True)
    root.attributes('-transparentcolor', 'white')
    root.configure(bg='white')
    root.geometry(f'+{x}+{y}')
    img = Image.open(icon_path)
    img_tk = ImageTk.PhotoImage(img)
    label = tk.Label(root, image=img_tk, bg='white', highlightthickness=0, borderwidth=0)
    label.image = img_tk
    label.pack()
    root.update_idletasks()
    root.update()
    time.sleep(duration)
    root.destroy()


def Win_Click_Adb(window_name, coordinates, max_retries=3):
    adb_path = fr'model\adb\adb.exe'

    class Win_Adb_Internal:
        def __init__(self, adb_path):
            self.adb_path = adb_path

        def start_adb_server(self):
            """启动 ADB 服务器"""
            try:
                result = subprocess.run(
                    [self.adb_path, 'start-server'],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                return True
            except Exception as e:
                BoxText(fr"日志：日志：启动 ADB 服务器时发生错误：{e}")
                return False

        def get_device_list(self):
            """获取连接的 ADB 设备列表"""
            try:
                result = subprocess.run(
                    [self.adb_path, 'devices'],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                device_lines = result.stdout.strip().split('\n')[1:]
                devices = {}
                for line in device_lines:
                    if not line.strip():
                        continue
                    match = re.match(r'(\S+)\s+device', line)
                    if match:
                        devices[match.group(1)] = 'device'
                return devices
            except Exception as e:
                BoxText(fr"日志：获取设备列表时发生错误：{e}")
                return {}

        def enumerate_windows(self, callback):
            """枚举所有顶级窗口并调用回调函数"""

            def safe_callback(hwnd, lparam):
                try:
                    if win32gui.IsWindowVisible(hwnd):  # 只处理可见的窗口
                        callback(hwnd, lparam)
                except Exception as e:
                    BoxText(fr"日志：控制点击时发生错误，窗口可能已最小化，枚举窗口时发生错误：{e}")
                    try:
                        # 尝试恢复窗口状态
                        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)  # 恢复窗口
                        win32gui.SetForegroundWindow(hwnd)  # 将窗口置为前台
                    except Exception as restore_e:
                        BoxText(fr"日志：恢复窗口状态时发生错误：{restore_e}")

            try:
                win32gui.EnumWindows(safe_callback, None)
            except Exception as e:
                BoxText(fr"日志：枚举窗口时发生错误：{e}")

        def find_emulator_by_window_title(self, window_title):
            """根据窗口标题查找对应的模拟器设备"""
            devices = self.get_device_list()
            emulator_serial = None

            def enum_windows_callback(hwnd, _):
                nonlocal emulator_serial
                if emulator_serial:
                    return True

                if not win32gui.IsWindowVisible(hwnd):  # 确保窗口是可见的
                    return True

                title = win32gui.GetWindowText(hwnd)
                if window_title.lower() in title.lower():
                    pid = win32process.GetWindowThreadProcessId(hwnd)[1]
                    process_name = next(
                        (p.info['name'] for p in psutil.process_iter(['pid', 'name']) if p.info['pid'] == pid), None)

                    if process_name and "dnplayer.exe" in process_name.lower():
                        match = re.search(r'(\d+)', window_title.lower())
                        if match:
                            number = int(match.group(1))
                            port = 5554 + (number - 1) * 2
                            expected_serial = f'emulator-{port}'
                            if expected_serial in devices:
                                emulator_serial = expected_serial
                                return False  # 停止枚举

            self.enumerate_windows(enum_windows_callback)
            return emulator_serial

        def send_adb_touch_event(self, emulator_serial, x, y):
            """向指定序列号的模拟器发送触摸事件"""
            try:
                subprocess.run(
                    [self.adb_path, '-s', emulator_serial, 'shell', 'input', 'tap', str(x), str(y)],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                return True
            except Exception as e:
                BoxText(fr"日志：日志：发生错误：{e}")
                return False

        def click_on_window(self, window_title, x, y, retries=0):
            """根据窗口标题发送点击指令"""
            if retries >= max_retries:
                print("达到最大重试次数")
                return False

            if not self.start_adb_server():
                BoxText(fr"日志：日志：无法启动 ADB 服务器，请检查 ADB 安装和路径设置。")
                return self.click_on_window(window_title, x, y, retries + 1)

            # 这里有问题.........
            emulator_serial = self.find_emulator_by_window_title(window_title)
            if not emulator_serial:
                BoxText(fr"日志：日志：未找到与窗口 '{window_title}' 对应的模拟器设备。")
                return self.click_on_window(window_title, x, y, retries + 1)

            # 获取目标窗口句柄，显示小点
            hwnd = None

            def enum_windows_callback(hwnd_local, _):
                nonlocal hwnd
                if win32gui.IsWindowVisible(hwnd_local) and window_title.lower() in win32gui.GetWindowText(
                        hwnd_local).lower():
                    hwnd = hwnd_local
                    return False  # 停止枚举

            self.enumerate_windows(enum_windows_callback)

            # if hwnd is not None:
            #     if core.config.Win_Dot_Status:
            #         Win_Click_See(hwnd, x, y)  # 传递队列
            #     else:
            #         BoxText(fr"错误：core.config.Win_Dot_Status={core.config.Win_Dot_Status}")
            # 获取目标窗口句柄，显示小点

            return self.send_adb_touch_event(emulator_serial, x, y)

    # 创建内部工具类实例，并执行点击操作
    win_adb_tool = Win_Adb_Internal(adb_path)
    success = win_adb_tool.click_on_window(window_name, *coordinates)
    return success


# 通用点击 ~ Adb方式

# 窗口平均布局


def Win_Arrange():
    DWMWA_EXTENDED_FRAME_BOUNDS = 9
    MONITOR_DEFAULTTOPRIMARY = 1
    MDT_EFFECTIVE_DPI = 0
    main_monitor = get_monitors()[0]
    screen_width = main_monitor.width
    screen_height = main_monitor.height
    user32 = ctypes.windll.user32
    shcore = ctypes.windll.shcore

    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    monitor_handle = user32.MonitorFromWindow(0, MONITOR_DEFAULTTOPRIMARY)
    dpiX = wintypes.UINT()
    dpiY = wintypes.UINT()
    shcore.GetDpiForMonitor(
        monitor_handle,
        MDT_EFFECTIVE_DPI,
        ctypes.byref(dpiX),
        ctypes.byref(dpiY)
    )
    original_width = 1920
    original_height = 1080
    scale_x = screen_width / original_width
    scale_y = screen_height / original_height
    inter_window_margin = screen_width * 0.01  # 窗口间的水平边距，保持不变
    vertical_inter_window_margin = screen_height * 0.13  # 上下窗口间的垂直边距，设置为5%
    top_margin = screen_height * 0.00  # 第一行窗口的顶部边距，这里设为0%
    right_margin = screen_width * 0.01  # 右侧边距
    usable_height = screen_height - top_margin - vertical_inter_window_margin
    window_height = (usable_height) / 2
    fixed_window_width = int(original_width * 0.35)  # 假设窗口宽度为原始宽度的47%
    fixed_window_height = int(original_height * 0.35)  # 同样假设窗口高度为原始高度的47%
    scaled_window_width = int(fixed_window_width * scale_x)
    scaled_window_height = int(fixed_window_height * scale_y)
    window_titles = ["w1", "w2", "w3", "w4"]
    for i, title in enumerate(window_titles):
        windows = gw.getWindowsWithTitle(title)
        if not windows:
            continue
        window = windows[0]
        row = i // 2
        col = i % 2
        rect = wintypes.RECT()
        DwmGetWindowAttribute = ctypes.windll.dwmapi.DwmGetWindowAttribute
        DwmGetWindowAttribute(
            window._hWnd,
            DWMWA_EXTENDED_FRAME_BOUNDS,
            ctypes.byref(rect),
            ctypes.sizeof(rect)
        )
        frame_width = rect.right - rect.left - window.width
        frame_height = rect.bottom - rect.top - window.height
        adjusted_width = scaled_window_width + frame_width
        adjusted_height = scaled_window_height + frame_height
        if col == 0:
            second_col_x = screen_width - adjusted_width - right_margin
            x = second_col_x - adjusted_width - inter_window_margin
        else:
            x = screen_width - adjusted_width - right_margin
        if row == 0:
            y = top_margin
        else:
            y = top_margin + adjusted_height + vertical_inter_window_margin  # 第二行窗口的Y坐标
        try:
            window.resizeTo(int(adjusted_width), int(adjusted_height))
            window.moveTo(int(x), int(y))
        except Exception as e:
            pass

# 窗口平均布局
