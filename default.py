import os
import queue
task_queue = queue.Queue()
import core.config
from core.comm import *
from core.click import *
from core.decision import local_decide
import core.click
import cv2
import numpy as np
import win32gui, win32ui, win32process, win32api
import ctypes
import time
from threading import Thread, Lock
from ultralytics import YOLO
from PIL import Image, ImageDraw, ImageFont
import requests
import torch
import win32con
import json
import threading
import traceback
from datetime import datetime
import keyboard

# 全局参数
running = True
confidence_min = 0.20

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

# Load YOLO model
model_card = YOLO(r"model\card.pt")
model_button = YOLO(r"model\button.pt")
if torch.cuda.is_available():
    model_card.to('cuda')
    model_button.to('cuda')
else:
    model_card.to('cpu')
    model_button.to('cpu')


def Model_Ally(image_path, type):
    model_card.conf = model_button.conf = confidence_min
    model_button.iou = model_button.iou = confidence_min
    if type == 'card':
        result = model_card.predict(source=image_path, verbose=False)
    elif type == 'button':
        result = model_button.predict(source=image_path, verbose=False)

    return result


def Capture_Client_Area(Hwnd, max_retries=3):
    for attempt in range(max_retries + 1):
        try:
            rect = win32gui.GetClientRect(Hwnd)
            left, top, right, bot = rect
            w = right - left
            h = bot - top
            hwndDC = win32gui.GetWindowDC(Hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()

            # 创建兼容位图前先检查 DC 是否有效
            if not saveDC:
                raise RuntimeError("Failed to create compatible DC.")

            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)

            saveDC.SelectObject(saveBitMap)
            result = ctypes.windll.user32.PrintWindow(Hwnd, saveDC.GetSafeHdc(), 1)

            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            im = Image.frombuffer('RGB', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), bmpstr, 'raw', 'BGRX', 0, 1)

            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(Hwnd, hwndDC)

            if result:
                return np.array(im)
            else:
                BoxText("日志：PrintWindow failed.")
                raise RuntimeError("Failed to capture client area.")

        except Exception as e:
            if attempt < max_retries:
                BoxText(
                    f"错误：Capture_Client_Area encountered an error on attempt {attempt + 1}/{max_retries}: {e}. Retrying...")
                time.sleep(1)  # 等待1秒后重试
            else:
                BoxText(f"错误：Capture_Client_Area failed after {max_retries} attempts.")
                raise  # 如果所有重试都失败，则抛出异常


def Window_Card(win_name, process_name, win='off'):
    frame_interval = 1 / 2

    global running
    while running:
        Hwnd = Get_Window_Handle(win_name, process_name)
        if not Hwnd:
            # BoxText(f"错误：未找到包含'{win_name}'的窗口，请确认窗口存在且未最小化。")
            time.sleep(0.1)  # 等待一段时间后重试
            continue

        start_time = time.time()

        try:
            img = Capture_Client_Area(Hwnd)
            rect = win32gui.GetClientRect(Hwnd)  # 获取客户区矩形
            client_rect = win32gui.ClientToScreen(Hwnd, (rect[0], rect[1]))
            client_rect_end = win32gui.ClientToScreen(Hwnd, (rect[2], rect[3]))
            original_window_width = client_rect_end[0] - client_rect[0]
            original_window_height = client_rect_end[1] - client_rect[1]

            crop_bottom_height = int(original_window_height * 0.25)
            crop_left = int((original_window_width - original_window_width * 0.6) / 2)
            crop_right = crop_left + int(original_window_width * 0.6)
            crop_top = original_window_height - crop_bottom_height
            cropped_img = img[crop_top:original_window_height, crop_left:crop_right]
            window_name = f'w{win_name}'
            results = Model_Ally(cropped_img, 'card')

            for result in results:
                annotated_frame = result.plot()
                ret = Ai_Look(Type='card', Results=result, Win=win_name)
                ad_data = Ai_Decision(ret, win_name)  # AI决策核心
                if win != "off":
                    text = core.config.card.get(win_name, ad_data['text'])
                    color_bg = core.config.color.get(win_name, ad_data['color'])
                    # BoxText(fr"错误：------------ad_data={ad_data}")
                    # multiple = core.config.multiple.get(win_name, ad_data['multiple'])
                    # if not text:
                    #     break

                    window_margin = 0
                    x_position = client_rect[0] + window_margin
                    y_position = client_rect_end[1] - window_margin - int(original_window_height * 0)

                    if not cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) >= 1:
                        cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE | cv2.WINDOW_KEEPRATIO)
                        hwnd_cv2 = win32gui.FindWindow(None, window_name)
                        if hwnd_cv2:
                            new_style = win32gui.GetWindowLong(hwnd_cv2, win32con.GWL_STYLE)
                            new_style &= ~win32con.WS_CAPTION  # 移除标题栏
                            win32gui.SetWindowLong(hwnd_cv2, win32con.GWL_STYLE, new_style)
                            win32gui.SetWindowPos(hwnd_cv2, None, x_position, y_position, 0, 0,
                                                  win32con.SWP_NOZORDER | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE | win32con.SWP_FRAMECHANGED)

                    cv2.moveWindow(window_name, x_position, y_position)
                    cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)

                    color = {
                        "red": (255, 0, 0),  # BGR格式的红色
                        "yellow": (255, 255, 0),  # BGR格式的黄色
                        "blue": (0, 0, 255),  # BGR格式的蓝色
                        "green": (0, 255, 0),  # BGR格式的绿色
                    }.get(color_bg, (128, 128, 128))  # 默认灰色

                    text_color = (255, 255, 255)  # 默认白色文字

                    if color_bg == "yellow" or color_bg == "green":
                        text_color = (0, 0, 0)  # 黑色

                    # 绘制一个小矩形
                    frame_height, frame_width, _ = annotated_frame.shape
                    rect_width = int(frame_width * 0.16)  # 宽度是窗口宽度的16%
                    rect_height = int(frame_height * 0.9)  # 高度是窗口高度的90%
                    x1 = frame_width - rect_width - 28  # 左上角x坐标，距右侧28像素
                    y1 = 9  # 左上角y坐标，距顶部9像素
                    x2 = x1 + rect_width  # 右下角x坐标
                    y2 = y1 + rect_height  # 右下角y坐标

                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, thickness=cv2.FILLED)
                    pil_image = Image.fromarray(cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB))
                    draw = ImageDraw.Draw(pil_image)
                    font_path = "model/text.ttf"  # 替换为你的中文字体文件路径
                    font_size = 26  # 设置字体大小
                    font = ImageFont.truetype(font_path, font_size)
                    text_x = x1 + 10  # 文字距离矩形左边缘的距离
                    text_y = y1 + 10  # 文字距离矩形上边缘的距离
                    draw.text((text_x, text_y), text, font=font, fill=text_color)
                    annotated_frame = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
                    cv2.imshow(window_name, cv2.cvtColor(annotated_frame, cv2.COLOR_RGB2BGR))

        except Exception as e:
            BoxText(f"错误：Window_Card encountered an error: {e}. Retrying...")
            time.sleep(1)  # 等待一段时间后重试
            traceback.print_exc()
            continue

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        elapsed_time = time.time() - start_time
        wait_time = max(0, frame_interval - elapsed_time)
        time.sleep(wait_time)

        if not win32gui.IsWindow(Hwnd):
            BoxText(f"错误：窗口'{win_name}'已关闭或最小化。")
            break


def Window_Button(win_name, process_name, win='off'):
    frame_interval = 1 / 2  # seconds between frames
    global running

    window_name = f'b{win_name}'
    hwnd_cv2 = None  # Store the handle of the OpenCV window

    while running:
        Hwnd = Get_Window_Handle(win_name, process_name)
        if not Hwnd:
            # BoxText(f"错误：未找到包含'{win_name}'的窗口，请确认窗口存在且未最小化。")
            time.sleep(1)  # Wait a bit before retrying
            continue

        start_time = time.time()

        try:
            img = Capture_Client_Area(Hwnd)
            results = Model_Ally(img, 'button')
            for result in results:
                ret = Ai_Look(Type='button', Results=result, Win=win_name)
                # BoxText(f"错误：窗口，{win_name}，Window_Button，临时查看,Window_Button，ret={ret}。")

            if win != 'off':
                rect = win32gui.GetWindowRect(Hwnd)
                original_window_width = rect[2] - rect[0]
                original_window_height = rect[3] - rect[1]
                new_window_width = int(original_window_width * 0.25)
                new_window_height = int(original_window_height * 0.25)
                x_position = rect[2] - new_window_width
                y_position = rect[3]

                if not cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) >= 1:
                    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE | cv2.WINDOW_KEEPRATIO)
                    hwnd_cv2 = win32gui.FindWindow(None, window_name)
                    if hwnd_cv2:
                        new_style = win32gui.GetWindowLong(hwnd_cv2, win32con.GWL_STYLE)
                        new_style &= ~win32con.WS_CAPTION  # Remove the win_name bar
                        win32gui.SetWindowLong(hwnd_cv2, win32con.GWL_STYLE, new_style)
                        win32gui.SetWindowPos(hwnd_cv2, None, x_position, y_position, 0, 0,
                                              win32con.SWP_NOZORDER | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE | win32con.SWP_FRAMECHANGED)
                current_size = cv2.getWindowImageRect(window_name)
                if current_size[2] != new_window_width or current_size[3] != new_window_height:
                    cv2.resizeWindow(window_name, new_window_width, new_window_height)
                cv2.moveWindow(window_name, x_position, y_position)
                cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)

                for result in results:
                    annotated_frame = result.plot()
                    resized_image = cv2.resize(annotated_frame, (new_window_width, new_window_height))
                    cv2.imshow(window_name, cv2.cvtColor(resized_image, cv2.COLOR_RGB2BGR))

        except Exception as e:
            BoxText(f"错误：Window_Button encountered an error: {e}. Retrying...")
            time.sleep(1)  # Wait a bit before retrying
            traceback.print_exc()
            continue

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        elapsed_time = time.time() - start_time
        wait_time = max(0, frame_interval - elapsed_time)
        # BoxText(f"日志：[{win_name}] Frame processing time: {elapsed_time:.4f}s, Waiting for: {wait_time:.4f}s")
        time.sleep(wait_time)

        if not win32gui.IsWindow(Hwnd):
            BoxText(f"错误：窗口'{win_name}'已关闭或最小化。")
            break


def Use_Label(now_label, use='good'):
    result = ''
    now_label = [tag.strip() for tag in now_label.split(',')]
    label_button = {
        0: {"z.qxtg"},
        1: {"z.qcs", "z.cwts"},
        2: {"z.x4", "z.x3", "z.x2", "z.x1", "z.bq"},
        3: {"z.5", "z.4.5", "z.2.5", "z.2", "z.1.5", "z.1", "z.0.5"},
        4: {"z.cp", "z.lp"}
    }

    label_click = ["z.x4", "z.5", "z.4.5", "z.2.5", "z.2", "z.bq", "z.0.5", "z.cp", "z.lp", "z.qxtg", "z.qcs"]  # 全部按钮

    if use == "good":
        label_click = ["z.x4", "z.5", "z.4.5", "z.2.5", "z.2"]  # 好牌按钮
    elif use == "bad":
        label_click = ["z.0.5"]  # 坏牌按钮"z.bq",
    elif use == "button":
        label_click = ["z.cp", "z.lp", "z.qxtg", "z.qcs"]  # 常规按钮

    my_label_list = list(label_click)
    for preferred_label in my_label_list:
        if preferred_label not in now_label:
            continue
        for key, values in label_button.items():
            matched_values = set(values).intersection(now_label)
            if len(values) <= 2:
                if preferred_label in matched_values:
                    return preferred_label
            else:
                if len(matched_values) >= 2 and preferred_label in matched_values:
                    return preferred_label
    return result


def Ai_Look(Type, Results, Win):
    all_label = ''
    if Results.boxes is None:
        BoxText("日志：No boxes detected.")
        return

    for box in Results.boxes:
        class_index = int(box.cls.item())
        confidence = box.conf.item()
        if confidence < confidence_min:
            break

        label = Results.names.get(class_index, "Unknown").lower()

        # BoxText(fr"日志：窗口={Win}，置信度={confidence}，标签={label}")

        if Type == "card":
            label = label.replace('a', '1')
            label = label.replace('t', '10')
            label = label.replace('j', '11')
            label = label.replace('q', '12')
            label = label.replace('k', '13')
            label = label[:-1] + '.' + label[-1]

        if all_label:
            all_label = all_label + ',' + label
        else:
            all_label = label

    global Auto_Run
    if Type == "button":
        card_text = core.config.card.get(Win, None)
        click_text = core.config.click.get(Win, None)
        multiple_text = core.config.multiple.get(Win, None)

        # 要点标签优先顺序
        click_all_label = Use_Label(all_label, 'all')
        click_good_label = Use_Label(all_label, 'good')
        click_bad_label = Use_Label(all_label, 'bad')
        click_button_label = Use_Label(all_label, 'button')

        if click_all_label and click_all_label in all_label:
            good_order = {'z.x4', 'z.5', 'z.4.5', 'z.2'}

            # BoxText(
            #     fr"日志：--------------------Ai_Look全输出，窗口{Win}，all_label={all_label}，click_all_label={click_all_label}，click_good_label={click_good_label}，click_text={click_text}，click_bad_label={click_bad_label}，click_button_label={click_button_label}")

            # 好牌处理逻辑
            if click_text == "yes" and click_good_label and click_good_label in good_order:
                if 'z.x4' in click_good_label:
                    Win_Click_Xy(results=Results, class_name=click_good_label, win=Win)
                else:
                    valid_labels = {'z.5', 'z.4.5', 'z.2', 'z.1'}
                    if click_good_label in valid_labels:
                        if multiple_text == "5":
                            Win_Click_Xy(results=Results, class_name=click_good_label, win=Win)
                        elif multiple_text == "4.5" and click_good_label in {'z.4.5', 'z.2'}:
                            Win_Click_Xy(results=Results, class_name=click_good_label, win=Win)
                        elif multiple_text == "2":
                            Win_Click_Xy(results=Results, class_name='z.2', win=Win)
                        elif multiple_text == "1":
                            Win_Click_Xy(results=Results, class_name='z.1', win=Win)

                BoxText(
                    fr"重要：Ai_Look好牌，窗口{Win}，ct={card_text}，cgl={click_good_label}，al={all_label}，ct={click_text}")

            # 坏牌处理逻辑
            elif ((
                          click_text and click_text == "no") or multiple_text == "") and click_bad_label and click_bad_label in all_label:
                Win_Click_Xy(results=Results, class_name=click_bad_label, win=Win)
                BoxText(
                    fr"重要：Ai_Look坏牌，窗口{Win}，ct={card_text}，cbl={click_bad_label}，al={all_label}，ct={click_text}")

            # 按钮处理逻辑
            elif click_button_label:
                Win_Click_Xy(results=Results, class_name=click_button_label, win=Win)
                BoxText(fr"重要：Ai_Look按钮，窗口{Win}，ct={card_text}，cbl={click_button_label}，ct={click_text}")
                # 点击完置空，以防下次点击
                # core.config.card[Win] = None
                # core.config.click[Win] = None
                # core.config.color[Win] = None
                # core.config.multiple[Win] = None
                # 点击完置空，以防下次点击

        elif click_text == "yes":  # 好牌时，抢庄加倍
            BoxText(
                fr"重要：Ai_Look，好牌没有点击按钮，窗口{Win}，ct={card_text}，cal={click_all_label}，al={all_label}，ct={click_text}")
        else:
            BoxText(
                fr"重要：Ai_Look全跳，窗口{Win}，ct={card_text}，cal={click_all_label}，al={all_label}，ct={click_text}")

    return all_label


# AI决策核心
def Jsons_Multiple(json_string):
    """解析包含多个JSON对象的字符串"""
    decoder = json.JSONDecoder()
    idx = 0
    result = []
    while idx < len(json_string):
        try:
            obj, idx = decoder.raw_decode(json_string, idx)
            result.append(obj)
        except ValueError:
            # 如果解析失败，可能是由于多余的逗号或其他问题，尝试跳过并继续
            idx += 1
    return result


# 全局变量用于存储不同窗口的状态
window_data = {'w1': None, 'w2': None, 'w3': None, 'w4': None}
last_all_win_data = None
last_invalid_time = time.time()


def Ai_Decision(ret, win):
    current_time = time.time()
    global window_data, last_all_win_data, last_invalid_time
    data = {'text': '-_-', 'color': '-_-', 'click': '-_-', 'multiple': '-_-'}
    url = f'{global_domain}/poker/poker_auto.php'
    elements = ret.split(',')

    if len(elements) == 4:
        window_data[win] = ret
        # BoxText(fr"日志：窗口{win}，Ai_Decision，window_data={window_data[win]}")

        if all(window_data.values()):
            last_invalid_time = current_time
            all_win_data = '|'.join([window_data[w] for w in sorted(window_data.keys())])

            # 只有当 all_win_data 和上次的一样时才提交，现在采用的二次确认机制，点击状态没开半自动时，不确认
            if (
                    last_all_win_data is not None and all_win_data == last_all_win_data) or core.config.Win_Dot_Status == False:
                # 本地决策 vs 远程服务器
                if only_domain == 'localhost':
                    try:
                        parsed_data = local_decide(all_win_data)
                        for i in range(4):
                            ad_data = parsed_data[i]
                            wi = fr"w{i + 1}"
                            core.config.card[wi] = ad_data['text']
                            core.config.click[wi] = ad_data['click']
                            core.config.color[wi] = ad_data['color']
                            core.config.multiple[wi] = ad_data['multiple']
                        BoxText(fr"日志：本地决策完成，{[ad['text'] + '->' + ad['multiple'] for ad in parsed_data]}")
                    except Exception as e:
                        BoxText(fr"日志：本地决策发生错误：{e}")
                else:
                    params = {'poker': all_win_data, 'win': win, 'uuid': Uuid()}
                    response = requests.get(url, params=params)

                    if response.status_code == 200:
                        try:
                            parsed_data = Jsons_Multiple(response.text.strip())
                            # BoxText(fr"日志：牌组上传，all_win_data=[{all_win_data}]，返回：parsed_data={parsed_data}")

                            if len(parsed_data) == 4:
                                for i in range(4):
                                    ad_data = parsed_data[i]
                                    wi = fr"w{i + 1}"
                                    core.config.card[wi] = ad_data['text']
                                    core.config.click[wi] = ad_data['click']
                                    core.config.color[wi] = ad_data['color']
                                    core.config.multiple[wi] = ad_data['multiple']
                                    # BoxText(
                                    #     fr"日志：窗口{wi}，牌组上传，{wi}，card={core.config.card[wi]}，click={core.config.click[wi]}，color={core.config.color[wi]}，multiple={core.config.multiple[wi]}。")
                            else:
                                BoxText("日志：解析响应时得到的JSON对象数量不正确")
                        except Exception as e:
                            BoxText(fr"日志：解析响应时发生错误：{e}")

                # 上传后清空所有窗口的数据
                for w in window_data:
                    window_data[w] = None

                data = {'text': '^_^', 'color': '^_^', 'click': '^_^', 'multiple': '^_^'}
            else:
                BoxText("日志：all_win_data与上次不同，不提交")
                last_all_win_data = all_win_data  # 更新 last_all_win_data 为当前 all_win_data

        else:
            # 单幅牌不再决策
            # params = {'poker': ret, 'win': win}
            # response = requests.get(url, params=params)
            # if response.status_code == 200:
            #     data = json.loads(response.text.strip())
            # BoxText(fr"日志：Ai_Decision.返回 = {data},text={data['text']}")
            pass
    else:
        if current_time - last_invalid_time < 5:
            BoxText(fr"日志：牌面不是4组，不提交，当前牌面：{ret}，窗口{win}")
        else:
            window_data = {'w1': None, 'w2': None, 'w3': None, 'w4': None}
            core.config.card = {}
            core.config.click = {}
            core.config.color = {}
            core.config.multiple = {}
            last_invalid_time = current_time
            BoxText(fr"日志：无效状态持续时间过长，重置 window_data，窗口{win}")

    return data


# AI决策核心
def Window_Key(event):
    global running
    if event.name == 'up':
        BoxText("重要：开始自动化.")
        core.config.Win_Dot_Status = True
    elif event.name == 'down':
        BoxText("重要：停止自动化.")
        core.config.Win_Dot_Status = False


def check_authorization():
    """检查授权配置 - 开源版本无需在线验证，通过配置文件控制"""
    uuid = Uuid()
    auth_url = os.getenv('POKER_AUTH_URL', f'{global_domain}/poker/user.php')
    payload = {"uuid": uuid}

    try:
        response = requests.post(auth_url, data=payload)
        response_data = response.json()
        if response_data.get("status") == "ok":
            print(f"{response_data.get('message', '授权成功')}")
            return True
        else:
            print(f"机器码【{uuid}】暂无授权，请先配置授权......")
            return False

    except Exception as e:
        # 未配置授权服务器时，允许本地运行（开源模式）
        print(f"提示：未连接授权服务器，以本地模式运行: {e}")
        return True


if __name__ == "__main__":
    debug = False
    Win_Arrange()  # 四个窗口右侧对齐排列
    # 验证授权码
    if not check_authorization():
        input("按任意键退出...")
        exit(1)  # 授权失败则终止程序

    # 如果授权成功，则继续执行以下代码
    keyboard.on_press_key('up', Window_Key)
    keyboard.on_press_key('down', Window_Key)

    window_titles = ["w1", "w2", "w3", "w4"]
    process_names = ["dnplayer.exe"] * 4
    print("1、全能主机，开启全部功能")
    print("2、一般主机，开启牌面")
    print("3、较差主机，仅开启必要功能")
    print('*******************************')
    choice = input("请输入选项 (1-3): ").strip()
    threads = []
    if debug:
        print(fr"--{choice}--")
    # 根据用户选择配置显示设置
    display_card = choice in ['1', '2']
    display_button_on = choice == '1'
    start_red_dot = choice in ['1', '2']
    if debug:
        print(fr"--1111111111--")
    for title, process in zip(window_titles, process_names):
        if debug:
            print(fr"--2222222222--")
        thread_1 = threading.Thread(target=Window_Card, args=(title, process, 'on' if display_card else 'off'))
        if debug:
            print(fr"--33333333333--")
        thread_2 = threading.Thread(target=Window_Button, args=(
            title, process, 'on' if display_button_on else 'off')) if choice != '3' else None
        thread_1.start()
        if debug:
            print(fr"--4444444444444--")
        if thread_2:
            thread_2.start()
            if debug:
                print(fr"--5555555555--")
            threads.append(thread_2)
        threads.append(thread_1)
    if debug:
        print(fr"--6666666666666666--")
    for thread in threads:
        if debug:
            print(fr"--7777777--")
        thread.join()
        if debug:
            print(fr"--88888888888888888--")

    try:
        if debug:
            print(fr"--999999999999999--")
        while running:
            if debug:
                print(fr"--00000000000000--")
            time.sleep(0.1)  # 减少CPU占用率
    except Exception as e:
        running = False
        print(f"错误：{e}")
    finally:
        # Assuming cv2 and BoxText are imported from somewhere
        import cv2

        cv2.destroyAllWindows()
        running = False
        input("用户暂停程序工作，按任意键退出...")
