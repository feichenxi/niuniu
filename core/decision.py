"""
本地决策模块 — 抢庄牛牛

替代远程决策服务器，本地计算牌型并给出策略建议。
纯数学计算，无需网络请求，延迟从网络级降至微秒级。

规则：
- 每人 4 张牌，从 4 张中选 3 张，若 3 张之和为 10 的倍数则有牛
- 剩余 1 张的点数 % 10 = 牛数（0 即牛牛）
- 无任何 3 张之和为 10 的倍数则为无牛
- 牌面大小：K(13) > Q(12) > J(11) > 10 > 9 > ... > A(1)
- 花色大小：♠ > ♥ > ♦ > ♣
"""

import re


def _card_value(value):
    """将牌面数值转为牛牛计算用的点数（J/Q/K 都算 10）"""
    v = int(value)
    return 10 if v > 10 else v


def _card_value_raw(value):
    """牌面原始数值，用于比大小"""
    return int(value)


def _parse_card(card_str: str):
    """
    解析单张牌字符串，返回 (原始面值, 牛牛面值, 花色)
    输入: "13.0" (K♠), "1.1" (A♥), "10.2" (10♦), "7.3" (7♣)
    花色: 0=♠, 1=♥, 2=♦, 3=♣
    """
    parts = card_str.strip().split('.')
    if len(parts) != 2:
        raise ValueError(f"无法解析牌面数据: {card_str}")
    val = int(parts[0])
    suit = int(parts[1])
    return _card_value_raw(val), _card_value(val), suit


def _parse_window_data(window_data: str):
    """
    解析一个窗口的牌面数据
    输入: "13.0,1.1,10.2,7.3"
    返回: [(原始面值, 牛牛面值, 花色), ...]
    """
    return [_parse_card(c) for c in window_data.split(',')]


def calc_hand(hand: list):
    """
    计算一手牌（4张）的牛牛类型

    参数:
        hand: [(原始面值, 牛牛面值, 花色), ...]  共4张牌

    返回:
        (牛数, 最大牌值, 最大牌花色)
        - 牛数: 0=牛牛, 1~9=牛几, -1=无牛
        - 最大牌值: 用于同牛数时比大小
        - 最大牌花色: 牌值相同时比花色
    """
    n = len(hand)
    # 找到所有 3 张牌的组合
    best_niu = -1  # -1 表示无牛
    best_remain = None

    # 4 张牌中选 3 张的所有组合（共 4 种）
    combinations = [(0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)]

    for combo in combinations:
        # 计算 3 张牌的牛牛值之和
        three_sum = sum(hand[i][1] for i in combo)
        if three_sum % 10 == 0:
            # 有牛！剩余那张牌
            remain_idx = (set(range(n)) - set(combo)).pop()
            remain_val = hand[remain_idx][1]
            niu = remain_val % 10  # 0 就是牛牛
            if niu > best_niu:
                best_niu = niu
                best_remain = hand[remain_idx]
            elif niu == best_niu and best_remain is not None:
                # 同牛数，比剩余牌大小
                if best_remain[0] < hand[remain_idx][0]:
                    best_remain = hand[remain_idx]
                elif best_remain[0] == hand[remain_idx][0]:
                    # 同牌值比花色 (0=♠ 最大 → 3=♣ 最小)
                    if best_remain[2] > hand[remain_idx][2]:
                        best_remain = hand[remain_idx]

    if best_niu >= 0:
        return best_niu, best_remain[0], best_remain[2]

    # 无牛：找出最大的一张牌
    max_card = max(hand, key=lambda c: (c[0], -c[2]))
    return -1, max_card[0], max_card[2]


def _hand_display_name(niu: int):
    """牛数 → 中文名称"""
    if niu == 0:
        return "牛牛"
    elif niu > 0:
        return f"牛{niu}"
    else:
        return "无牛"


def _compare_hands(hand1: tuple, hand2: tuple):
    """
    比较两手牌，返回 True 表示 hand1 > hand2

    比较规则：
    1. 牛数优先（牛牛=0 > 牛9=9 > ... > 无牛=-1）
    2. 同牛数比最大牌值
    3. 同牌值比花色（♠>♥>♦>♣）
    """
    niu1, val1, suit1 = hand1
    niu2, val2, suit2 = hand2

    # 牛数比较（牛牛=0 最好，无牛=-1 最差）
    rank1 = -niu1 if niu1 > 0 else (0 if niu1 == 0 else 999)
    rank2 = -niu2 if niu2 > 0 else (0 if niu2 == 0 else 999)

    if rank1 != rank2:
        return rank1 < rank2

    # 同牛数比最大牌值
    if val1 != val2:
        return val1 > val2

    # 同牌值比花色
    return suit1 < suit2


def decide(hands: dict):
    """
    对 4 个窗口的牌面进行本地决策

    参数:
        hands: {"w1": (牛数, 最大牌值, 最大牌花色), ...}

    返回:
        {"w1": {"text": "牛牛", "click": "yes", "color": "red", "multiple": "5"}, ...}
    """
    # 按牌力排序
    rankings = sorted(hands.keys(), key=lambda w: hands[w], reverse=True)

    # 根据排名分配策略
    strategy_map = {
        0: {"text_suffix": "", "click": "yes", "color": "red",    "multiple": "5"},
        1: {"text_suffix": "", "click": "yes", "color": "yellow", "multiple": "2"},
        2: {"text_suffix": "", "click": "yes", "color": "green",  "multiple": "1"},
        3: {"text_suffix": "", "click": "no",  "color": "blue",   "multiple": ""},
    }

    result = {}
    for rank, win in enumerate(rankings):
        niu, val, suit = hands[win]
        strategy = strategy_map[rank].copy()

        # 如果排名最末且牌力差距大，强化"不抢"建议
        if rank == 3 and niu <= 2:
            strategy["multiple"] = ""

        # 如果排名最优且牛数特别好，提高倍率
        if rank == 0 and niu in (0, 1, 2, 3):
            strategy["multiple"] = "5"
        elif rank == 0 and niu in (4, 5, 6):
            strategy["multiple"] = "4.5"
        elif rank == 1 and niu == 0:
            # 排第二但是牛牛，可以抢高倍
            strategy["multiple"] = "4.5"
            strategy["color"] = "red"

        strategy["text"] = _hand_display_name(niu)
        result[win] = strategy

    return result


def parse_all_win_data(all_win_data: str):
    """
    解析服务器模式的数据格式，返回每个窗口的牌面数据

    输入: "13.0,1.1,10.2,7.3|2.3,5.0,8.1,11.2|..."
    返回: {"w1": [(13,10,0), (1,1,1), (10,10,2), (7,7,3)], ...}
    """
    parts = all_win_data.split('|')
    if len(parts) != 4:
        raise ValueError(f"需要4个窗口的牌面数据，实际收到 {len(parts)} 个")

    result = {}
    for i, part in enumerate(parts):
        win = f"w{i + 1}"
        result[win] = _parse_window_data(part)
    return result


def local_decide(all_win_data: str):
    """
    一站式本地决策：输入聚合数据字符串，输出与服务器相同格式的结果

    参数:
        all_win_data: "13.0,1.1,10.2,7.3|..." (4窗口数据，|分隔)

    返回:
        [
            {"text": "牛牛", "click": "yes", "color": "red", "multiple": "5"},
            ...
        ]  (4个对象的列表，对应w1~w4)
    """
    # 解析牌面
    parsed = parse_all_win_data(all_win_data)

    # 计算每手牌的牛数
    hands = {}
    for win, cards in parsed.items():
        hands[win] = calc_hand(cards)

    # 决策
    result = decide(hands)

    # 转为列表格式（与服务器返回一致）
    return [result[f"w{i+1}"] for i in range(4)]
