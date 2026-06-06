import sys
import os

# 添加父目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import save_output
from on_window import focus_bh3_window, run_as_admin, is_admin
import templates.clicks_keyboard as ck
import time
import json
from ocr.ocr_functions import find_keyin

# 权重计算函数映射 - 稍后在函数内部动态加载
type_weight_map = {}

# 延迟导入函数，避免循环导入
def lazy_import():
    global type_weight_map
    if not type_weight_map:
        from character.letu_elysia_star import read_keyin_detail, write_keyin_detail, jiushi_weights, zhenwo_weights, jielv_weights, huangjin_weights, luoxuan_weights, aomie_weights, tianhui_weights, chana_weights, xvguang_weights, wuxian_weights, fanxing_weights, fusheng_weights, kongmeng_weights
        type_weight_map.update({
            "jiushi": jiushi_weights,
            "zhenwo": zhenwo_weights,
            "jielv": jielv_weights,
            "huangjin": huangjin_weights,
            "luoxuan": luoxuan_weights,
            "aomie": aomie_weights,
            "tianhui": tianhui_weights,
            "chana": chana_weights,
            "xvguang": xvguang_weights,
            "wuxian": wuxian_weights,
            "fanxing": fanxing_weights,
            "fusheng": fusheng_weights,
            "kongmeng": kongmeng_weights
        })
        return read_keyin_detail, write_keyin_detail
    else:
        from character.letu_elysia_star import read_keyin_detail, write_keyin_detail
        return read_keyin_detail, write_keyin_detail

# 定义各刻印类别的优先级设定
priority_settings = {
    "jiushi": {
        "yuansu_index": [0, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        "wuli_index": [0, 1, 2, 5, 6, 7, 8, 9, 10, 11, 12],
        "all_use_index": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    },
    "jielv": {
        "all_use_index": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    },
    "huangjin": {
        "all_use_index": [0, 1, 5, 6, 7, 8, 9]
    },
    "luoxuan": {
        "all_use_index": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    },
    "aomie": {
        "all_use_index": [0, 1, 3, 4, 10, 11, 12, 13]
    },
    "tianhui": {
        "yuansu_index": [0, 1, 3, 5, 6, 7, 8, 9],
        "wuli_index": [0, 1, 3, 4, 6, 7, 8, 9],
        "all_use_index": [0, 1, 3, 6, 7, 8, 9]
    },
    "chana": {
        "all_use_index": [0, 1, 2, 5, 6, 7, 8, 9]
    },
    "xvguang": {
        "all_use_index": [3, 4, 6, 7, 8]
    },
    "wuxian": {
        "all_use_index": [0, 1, 3, 6, 7, 8, 9]
    },
    "fanxing": {
        "all_use_index": [0, 1, 2, 6, 7, 8, 9]
    },
    "fusheng": {
        "yuansu_index": [0, 2, 3, 4, 6, 7, 8, 9, 10],
        "wuli_index": [0, 1, 5, 4, 6, 7, 8, 9, 10],
        "all_use_index": [0, 2, 3, 4, 6, 7, 8, 9, 10]  # 默认使用元素优先级
    },
    "kongmeng": {
        "all_use_index": [0, 1, 2, 3, 6, 7, 8, 9]
    }
}

# 定义各刻印章项的索引映射 - 同时支持完整名称和显示名称
option_mappings = {
    "jiushi": {
        "救世_施予者的金杯_全伤": 0,
        "施予者的金杯": 0,
        "救世_守王者的坠饰_物理": 1,
        "守王者的坠饰": 1,
        "守望者的坠饰": 1,  # 注意：OCR识别差异
        "救世_猎杀者的假面_物理": 2,
        "猎杀者的假面": 2,
        "救世_制约者的圣器_元素": 3,
        "制约者的圣器": 3,
        "救世_不死者的烙印_元素": 4,
        "不死者的烙印": 4,
        "救世_求道者的法衣_能量": 5,
        "求道者的法衣": 5,
        "救世_救世者的王剑_核心": 6,
        "救世者的王剑": 6,
        "救世_救世者的麇集_增幅": 7,
        "救世者的麇集": 7,
        "救世_救世者的远征_增幅": 8,
        "救世者的远征": 8,
        "救世_救世者的余响_增幅": 9,
        "救世者的余响": 9,
        "救世_救世者的残梦_增幅": 10,
        "救世者的残梦": 10,
        "救世_救世者的决断_增幅": 11,
        "救世者的决断": 11,
        "救世_救世者的凯旋_增幅": 12,
        "救世者的凯旋": 12
    },
    "jielv": {
        "戒律_其一，不可背叛_普攻": 0,
        "其一，不可背叛": 0,
        "戒律_其二，不可欺瞒_免伤": 1,
        "其二，不可欺瞒": 1,
        "戒律_其三，不可roff_能量": 2,
        "其三，不可roff": 2,
        "戒律_其四，不可妄行_爆发": 3,
        "其四，不可妄行": 3,
        "戒律_其五，不可伪言_全伤": 4,
        "其五，不可伪言": 4,
        "戒律_其六，不可沉沦_全伤": 5,
        "其六，不可沉沦": 5,
        "戒律_汝，当为戒律所佑_核心": 6,
        "汝，当为戒律所佑": 6,
        "戒律_汝，当见诸恶得惩_增幅": 7,
        "汝，当见诸恶得惩": 7,
        "戒律_汝，当见诸善得行_增幅": 8,
        "汝，当见诸善得行": 8,
        "戒律_汝，当见诸愿得归_增幅": 9,
        "汝，当见诸愿得归": 9
    },
    "huangjin": {
        "黄金_乐园的宣叙_全伤": 0,
        "乐园的宣叙": 0,
        "黄金_溪流的宣叙_全伤": 1,
        "溪流的宣叙": 1,
        "黄金_飞鸟的宣叙_免伤": 2,
        "飞鸟的宣叙": 2,
        "黄金_果林的宣叙_回能": 3,
        "果林的宣叙": 3,
        "黄金_美酒的宣叙_回能": 4,
        "美酒的宣叙": 4,
        "黄金_宝玉的宣叙_能量": 5,
        "宝玉的宣叙": 5,
        "黄金_黄金的余音_核心": 6,
        "黄金的余音": 6,
        "黄金_枯荣的余音_增幅": 7,
        "枯荣的余音": 7,
        "黄金_凄风的余音_增幅": 8,
        "凄风的余音": 8,
        "黄金_寂夜的余音_增幅": 9,
        "寂夜的余音": 9
    },
    "luoxuan": {
        "螺旋_第一幕魔术_全伤": 0,
        "第一幕魔术": 0,
        "螺旋_第二幕钟摆_全伤": 1,
        "第二幕钟摆": 1,
        "螺旋_第三幕矛盾_全伤": 2,
        "第三幕矛盾": 2,
        "螺旋_第四幕汤匙_全伤": 3,
        "第四幕汤匙": 3,
        "螺旋_第五幕蛛丝_全伤": 4,
        "第五幕蛛丝": 4,
        "螺旋_第六幕嗤笑_能量": 5,
        "第六幕嗤笑": 5,
        "螺旋_幕间剧颠末的螺旋_核心": 6,
        "幕间剧颠末的螺旋": 6,
        "螺旋_木偶剧爻错的监牢_增幅": 7,
        "木偶剧爻错的监牢": 7,
        "螺旋_严肃剧沉默的始源_增幅": 8,
        "严肃剧沉默的始源": 8,
        "螺旋_传奇剧交叠的指针_增幅": 9,
        "传奇剧交叠的指针": 9
    },
    "aomie": {
        "鏖灭_剑锋·剑冢·剑痕_全伤": 0,
        "剑锋·剑冢·剑痕": 0,
        "鏖灭_赤骨·赤血·赤练_全伤": 1,
        "赤骨·赤血·赤练": 1,
        "鏖灭_狂信·狂人·狂言_免伤": 2,
        "狂信·狂人·狂言": 2,
        "鏖灭_命路·命舛·命刻_生命": 3,
        "命路·命舛·命刻": 3,
        "鏖灭_无妄·无心·无归_全伤": 4,
        "无妄·无心·无归": 4,
        "鏖灭_唯神·唯我·唯一_能量": 5,
        "唯神·唯我·唯一": 5,
        "鏖灭_鏖斗·鏖战·鏖杀·鏖灭_核心_燃血": 6,
        "鏖斗·鏖战·鏖杀·鏖灭": 6,
        "鏖灭_非人·非鬼·非神·非天_增幅_燃血": 7,
        "非人·非鬼·非神·非天": 7,
        "鏖灭_一人·一面·一契 一途_增幅_燃血": 8,
        "一人·一面·一契 一途": 8,
        "鏖灭_千钧·千转·千难·千劫_增幅_燃血": 9,
        "千钧·千转·千难·千劫": 9,
        "鏖灭_鏖兵·鏖剪·鏖馘·鏖灭_核心_回血": 10,
        "鏖兵·鏖剪·鏖馘·鏖灭": 10,
        "鏖灭_无死·无生·无灭·无存_增幅_回血": 11,
        "无死·无生·无灭·无存": 11,
        "鏖灭_故土·故国·故友·故人_增幅_回血": 12,
        "故土·故国·故友·故人": 12,
        "鏖灭_焚身·焚骨·焚心·焚魂_增幅_回血": 13,
        "焚身·焚骨·焚心·焚魂": 13
    },
    "tianhui": {
        "天慧_宿命之箴言_全伤": 0,
        "宿命之箴言": 0,
        "天慧_天眼之箴言_全伤": 1,
        "天眼之箴言": 1,
        "天慧_天耳之箴言_免伤": 2,
        "天耳之箴言": 2,
        "天慧_他心之箴言_能量": 3,
        "他心之箴言": 3,
        "天慧_神足之箴言_物理": 4,
        "神足之箴言": 4,
        "天慧_漏尽之箴言_元素": 5,
        "漏尽之箴言": 5,
        "天慧_天慧之真言_核心": 6,
        "天慧之真言": 6,
        "天慧_无常之真言_增幅": 7,
        "无常之真言": 7,
        "天慧_无我之真言_增幅": 8,
        "无我之真言": 8,
        "天慧_寂静之真言_增幅": 9,
        "寂静之真言": 9
    },
    "chana": {
        "刹那_缭乱百花梅_速度": 0,
        "缭乱百花梅": 0,
        "刹那_缭乱百花虹_全伤": 1,
        "缭乱百花虹": 1,
        "刹那_缭乱百花牡丹_全伤": 2,
        "缭乱百花牡丹": 2,
        "刹那_缭乱百花菊_闪避": 3,
        "缭乱百花菊": 3,
        "刹那_缭乱百花藤_闪避": 4,
        "缭乱百花藤": 4,
        "刹那_缭乱百花菖蒲_能量": 5,
        "缭乱百花菖蒲": 5,
        "刹那_刹那一刀樱上幕_核心": 6,
        "刹那一刀樱上幕": 6,
        "刹那_刹那一刀雨四光_增幅": 7,
        "刹那一刀雨四光": 7,
        "刹那_刹那一刀月见酒_增幅": 8,
        "刹那一刀月见酒": 8,
        "刹那_刹那一刀猪鹿蝶_增幅": 9,
        "刹那一刀猪鹿蝶": 9
    },
    "xvguang": {
        "旭光_亵渎不归之爪_流血": 0,
        "亵渎不归之爪": 0,
        "旭光_掩蔽血月之翼_流血": 1,
        "掩蔽血月之翼": 1,
        "旭光_撕裂暗空之角_流血": 2,
        "撕裂暗空之角": 2,
        "旭光_俯视邪渊之眼_全伤": 3,
        "俯视邪渊之眼": 3,
        "旭光_毁谤硫磺之息_能量": 4,
        "毁谤硫磺之息": 4,
        "旭光_逆结七罪之心_增益": 5,
        "逆结七罪之心": 5,
        "旭光_旭光_长明不落_核心": 6,
        "旭光_长明不落": 6,
        "旭光_英雄_独担兴衰_增幅": 7,
        "英雄_独担兴衰": 7,
        "旭光_善恶_两分难渡_增幅": 8,
        "善恶_两分难渡": 8,
        "旭光_宿诺_百折未易_增益": 9,
        "宿诺_百折未易": 9
    },
    "wuxian": {
        "无限_利齿的V_全伤": 0,
        "利齿的V": 0,
        "无限_缠环的P_全伤": 1,
        "缠环的P": 1,
        "无限_静默的B_免伤": 2,
        "静默的B": 2,
        "无限_吻毒的E_全伤": 3,
        "吻毒的E": 3,
        "无限_栖影的C_冷却": 4,
        "栖影的C": 4,
        "无限_黯瞳的T_冷却": 5,
        "黯瞳的T": 5,
        "无限_无限的X_核心": 6,
        "无限的X": 6,
        "无限_死亡的X_增幅": 7,
        "死亡的X": 7,
        "无限_未知的X_增幅": 8,
        "未知的X": 8,
        "无限_新生的X_增幅": 9,
        "新生的X": 9
    },
    "fanxing": {
        "繁星_红色的_热热的_全伤": 0,
        "红色的_热热的": 0,
        "繁星_蓝色的_冷冷的_减益": 1,
        "蓝色的_冷冷的": 1,
        "繁星_黄色的_暖暖的_全伤": 2,
        "黄色的_暖暖的": 2,
        "繁星_黑色的_暗暗的_全伤": 3,
        "黑色的_暗暗的": 3,
        "繁星_白色的_亮亮的_能量": 4,
        "白色的_亮亮的": 4,
        "繁星_灰色的_空空的_增益": 5,
        "灰色的_空空的": 5,
        "繁星_像是繁星_闪耀着的_核心": 6,
        "像是繁星_闪耀着的": 6,
        "繁星_像是野花_绽放着的_增幅": 7,
        "像是野花_绽放着的": 7,
        "繁星_像是火焰_燃烧着的_增益": 8,
        "像是火焰_燃烧着的": 8,
        "繁星_像是叶子_舒展着的_增幅": 9,
        "像是叶子_舒展着的": 9
    },
    "fusheng": {
        "浮生_行路漫漫_全伤": 0,
        "行路漫漫": 0,
        "浮生_日月蹉跎_物理": 1,
        "日月蹉跎": 1,
        "浮生_玄衣不再_元素": 2,
        "玄衣不再": 2,
        "浮生_旧梦如昨_元素": 3,
        "旧梦如昨": 3,
        "浮生_纵使寻得_免伤": 4,
        "纵使寻得": 4,
        "浮生_与谁诉说_物理": 5,
        "与谁诉说": 5,
        "浮生_浮生茫茫_百态皆苦_核心": 6,
        "浮生茫茫_百态皆苦": 6,
        "浮生_凡尘总总_一苇难渡_增幅": 7,
        "凡尘总总_一苇难渡": 7,
        "浮生_如羽随风_似浪逐流_增幅": 8,
        "如羽随风_似浪逐流": 8,
        "浮生_怎堪梦醒_难觅归途_增幅": 9,
        "怎堪梦醒_难觅归途": 9,
        "浮生_似曾相识，却又相忘_增幅": 10,
        "似曾相识，却又相忘": 10
    },
    "kongmeng": {
        "空梦_猫猫之箴言_全伤": 0,
        "猫猫之箴言": 0,
        "空梦_钢刃逆卷之尾_全伤": 1,
        "钢刃逆卷之尾": 1,
        "空梦_街巷的宣叙_能量": 2,
        "街巷的宣叙": 2,
        "空梦_灵动的P&C_能量": 3,
        "灵动的P&C": 3,
        "空梦_行商者的哲学_银币": 4,
        "行商者的哲学": 4,
        "空梦_值钱的，闪闪的_银币": 5,
        "值钱的，闪闪的": 5,
        "空梦_空梦_空集_空我_空欢_核心": 6,
        "空梦_空集_空我_空欢": 6,
        "空梦_即兴短剧老板_增幅": 7,
        "即兴短剧老板": 7,
        "空梦_刹那一爪猫猫拳_增幅": 8,
        "刹那一爪猫猫拳": 8,
        "空梦_咱_此地命不该绝_增幅": 9,
        "咱_此地命不该绝": 9
    }
}

# 获取刻印名称对应的类别
def get_category_from_keyin_name(keyin_name):
    """
    根据刻印名称获取对应的类别
    
    :param keyin_name: 刻印名称
    :return: 类别字符串，如果未找到返回None
    """
    for category, mappings in option_mappings.items():
        if keyin_name in mappings:
            return category
    return None

# 定义各刻印选项的索引映射
def get_keyin_option_index(keyin_name, category):
    """
    获取刻印名称在对应类别中的索引
    
    :param keyin_name: 刻印名称
    :param category: 刻印类别
    :return: 刻印索引，如果未找到返回-1
    """
    if category in option_mappings and keyin_name in option_mappings[category]:
        return option_mappings[category][keyin_name]
    return -1

def select_keyin(found_keyins, character_type="yuansu"):
    """
    根据人物的优先级设定，从find_keyin返回的列表中选择一个刻印
    
    :param found_keyins: find_keyin函数返回的列表，每个元素为(类别, 刻印名称, 坐标)
    :param character_type: 人物类型，可选值为"yuansu"(元素)、"wuli"(物理)、"all"(全部)
    :return: 选中的刻印元组(类别, 刻印名称, 坐标)，如果没有找到返回None
    """
    if not found_keyins:
        return None
    
    # 获取所有唯一的刻印类别
    categories = list(set([item[0] for item in found_keyins]))
    
    # 遍历每个类别，寻找符合优先级的刻印
    for category in categories:
        if category not in priority_settings:
            continue
        
        # 获取该类别的优先级设定
        settings = priority_settings[category]
        
        # 根据人物类型选择对应的优先级索引列表
        if character_type == "yuansu" and "yuansu_index" in settings:
            priority_indexes = settings["yuansu_index"]
        elif character_type == "wuli" and "wuli_index" in settings:
            priority_indexes = settings["wuli_index"]
        else:
            priority_indexes = settings.get("all_use_index", [])
        
        # 根据优先级索引列表，选择第一个匹配的刻印
        for priority_idx in priority_indexes:
            for keyin_item in found_keyins:
                item_category, item_name, item_coords = keyin_item
                if item_category == category:
                    # 获取该刻印的索引
                    item_index = get_keyin_option_index(item_name, category)
                    if item_index == priority_idx:
                        return keyin_item
    
    # 如果没有找到符合优先级的刻印，返回第一个找到的刻印
    return found_keyins[0]
def single_select_keyin(region, confidence=0.7, preprocess=False, category=None, character_type="yuansu", use_similarity=False, show_debug=False, use_special_matching=False):
    """
    执行单次刻印选择流程，基于main中的逻辑
    
    Args:
        region: 查找区域，格式为(x1, y1, x2, y2)
        confidence: 匹配置信度，默认0.7
        preprocess: 是否预处理图像，默认False
        category: 刻印类别，如果为None则自动识别
        character_type: 人物类型，可选值为"yuansu"(元素)、"wuli"(物理)、"all"(全部)
        use_similarity: 是否使用相似度匹配
        use_special_matching: 是否使用特殊匹配（包括箴言和偏僻字），默认False
    
    Returns:
        str: 选中的刻印类别，如 "fusheng"、"jiushi"、"jielv"，如果没有找到返回None
    """
    # 根据category自动设置匹配模式
    # tianhui: 开启相似度匹配，关闭特殊匹配
    # aomie: 关闭相似度匹配，开启特殊匹配  
    # None: 两者都开启
    # 其他: 使用传入的默认值
    current_use_similarity = use_similarity
    current_special_matching = use_special_matching
    
    if category == "tianhui":
        current_use_similarity = True
        current_special_matching = False
        print(f"tianhui刻印: 开启相似度匹配，关闭特殊匹配")
    elif category == "aomie":
        current_use_similarity = False
        current_special_matching = True
        print(f"aomie刻印: 关闭相似度匹配，开启特殊匹配")
    elif category is None:
        current_use_similarity = True
        current_special_matching = True
        print(f"category=None: 开启相似度匹配和特殊匹配")
    else:
        # 其他category保持传入的默认值
        print(f"category={category}: 使用传入的相似度匹配={use_similarity}, 特殊匹配={use_special_matching}")
    
    # 点击当前位置
    time.sleep(2)
    # 点击中心位置 (960, 540)
    ck.click_at_position(960, 540)
    time.sleep(4)
    # 点击中心位置 (960, 540)
    ck.click_at_position(960, 540)
    time.sleep(3)
    # 点击中心位置 (960, 540)
    ck.click_at_position(960, 540)
    # 查找刻印
    print("执行find_keyin函数：")
    found_keyins = find_keyin(region=region, confidence=confidence, preprocess=preprocess, category=category, show_debug=True, use_similarity=current_use_similarity, use_special_matching=current_special_matching)
    print(f"找到的刻印: {found_keyins}")
    
    # 如果没有匹配到keyin文本，且category不为None，尝试将category设为None再试一次
    if not found_keyins and category is not None:
        print("没有匹配到keyin文本，尝试将category设为None再试一次...")
        # 当category设为None时，开启特殊匹配
        found_keyins = find_keyin(region=region, confidence=confidence, preprocess=preprocess, category=None, show_debug=True, use_similarity=True, use_special_matching=True)
        print(f"第二次查找的刻印: {found_keyins}")
    
    # 如果没有提供category，尝试根据找到的刻印名称识别类别
    if category is None and found_keyins:
        print("未提供category，尝试自动识别类别...")
        for item in found_keyins:
            item_name = item[1]
            identified_category = get_category_from_keyin_name(item_name)
            if identified_category:
                print(f"识别到类别: {identified_category} 对应刻印: {item_name}")
                # 重新构造只包含该类别的刻印列表
                filtered_keyins = [item for item in found_keyins if get_category_from_keyin_name(item[1]) == identified_category]
                found_keyins = filtered_keyins
                break
    
    # 使用select_keyin函数选择刻印
    print("执行select_keyin函数：")
    selected_keyin = select_keyin(found_keyins, character_type)
    print(f"根据优先级选择的刻印: {selected_keyin}")
    
    # 如果找到合适的刻印，点击它
    if selected_keyin:
        print(f"准备点击选择的刻印: {selected_keyin[1]}")
        # 点击位置（已在OCR处理中减去padding）
        ck.click_at_position(selected_keyin[2][0], selected_keyin[2][1])
        ck.keyboard_i_press_release()
        
        # 更新count和weight
        item_category = selected_keyin[0]
        read_keyin_detail, write_keyin_detail = lazy_import()
        keyin_data = read_keyin_detail()
        
        # 更新count
        count_key = f"{item_category}_count"
        keyin_data[count_key] = keyin_data.get(count_key, 0) + 1
        print(f"{count_key} +1，现在为: {keyin_data[count_key]}")
        write_keyin_detail(keyin_data)
        
        # 更新weight
        if item_category in type_weight_map:
            new_weight = type_weight_map[item_category]()
            print(f"权重已更新: {item_category} = {new_weight:.2f}")
    
    # 只返回类别
    return selected_keyin[0] if selected_keyin else None

def double_select_keyin(region, category=None, character_type="yuansu", use_special_matching=False, use_similarity=False):
    """
    执行两次刻印选择流程：click-find-select-find-select
    
    Args:
        region: 查找区域，格式为(x1, y1, x2, y2)
        category: 刻印类别，如果为None则自动识别
        character_type: 人物类型，可选值为"yuansu"(元素)、"wuli"(物理)、"all"(全部)
        use_special_matching: 是否使用特殊匹配（包括箴言和偏僻字），默认False
    
    Returns:
        str: 选中的刻印类别，如 "fusheng"、"jiushi"、"jielv"，如果没有找到返回 None
    """
    selected_keyins = []
    
    # 根据category自动设置匹配模式
    # tianhui: 开启相似度匹配，关闭特殊匹配
    # aomie: 关闭相似度匹配，开启特殊匹配  
    # None: 两者都开启
    # 其他: 使用传入的默认值
    current_use_similarity = use_similarity
    current_special_matching = use_special_matching
    
    if category == "tianhui":
        current_use_similarity = True
        current_special_matching = False
        print(f"tianhui刻印: 开启相似度匹配，关闭特殊匹配")
    elif category == "aomie":
        current_use_similarity = False
        current_special_matching = True
        print(f"aomie刻印: 关闭相似度匹配，开启特殊匹配")
    elif category is None:
        current_use_similarity = True
        current_special_matching = True
        print(f"category=None: 开启相似度匹配和特殊匹配")
    else:
        # 其他category保持传入的默认值
        print(f"category={category}: 使用传入的相似度匹配={use_similarity}, 特殊匹配={use_special_matching}")
    
    time.sleep(4)
    # 第一步：点击当前位置以刷新选项
    # 点击中心位置 (960, 540)
    ck.click_at_position(960, 540)
    time.sleep(3)
    # 点击中心位置 (960, 540)
    ck.click_at_position(960, 540)
    time.sleep(3)
    # 点击中心位置 (960, 540)
    ck.click_at_position(960, 540)
    time.sleep(3)  # 等待3秒，确保界面更新
    
    # 第一次查找和选择
    print("第一次查找刻印...")
    found_keyins1 = find_keyin(region=region, category=category, use_similarity=current_use_similarity, use_special_matching=current_special_matching)
    print(f"第一次找到的刻印: {found_keyins1}")
    
    # 如果没有匹配到keyin文本，且category不为None，尝试将category设为None再试一次
    if not found_keyins1 and category is not None:
        print("没有匹配到keyin文本，尝试将category设为None再试一次...")
        # 当category设为None时，开启特殊匹配
        found_keyins1 = find_keyin(region=region, category=None, use_similarity=True, use_special_matching=True)
        print(f"第一次查找的刻印（重试）: {found_keyins1}")
    
    # 过滤掉zhenwo刻印
    found_keyins1 = [item for item in found_keyins1 if get_category_from_keyin_name(item[1]) != "zhenwo"]
    if found_keyins1:
        print(f"过滤后剩余的刻印: {found_keyins1}")
    
    # 如果没有提供category，尝试根据找到的刻印名称识别类别
    if category is None and found_keyins1:
        print("未提供category，尝试自动识别类别...")
        for item in found_keyins1:
            item_name = item[1]
            identified_category = get_category_from_keyin_name(item_name)
            if identified_category:
                print(f"识别到类别: {identified_category} 对应刻印: {item_name}")
                # 重新构造只包含该类别的刻印列表
                filtered_keyins = [item for item in found_keyins1 if get_category_from_keyin_name(item[1]) == identified_category]
                found_keyins1 = filtered_keyins
                break
    
    if found_keyins1:
        selected_keyin1 = select_keyin(found_keyins1, character_type)
        if selected_keyin1:
                print(f"第一次选择的刻印: {selected_keyin1}")
                # 点击位置（已在OCR处理中减去padding）
                ck.click_at_position(selected_keyin1[2][0], selected_keyin1[2][1])
                ck.keyboard_i_press_release()
                selected_keyins.append(selected_keyin1)
                
                # 更新count和weight
                item_category = selected_keyin1[0]
                read_keyin_detail, write_keyin_detail = lazy_import()
                keyin_data = read_keyin_detail()
                
                # 更新count
                count_key = f"{item_category}_count"
                keyin_data[count_key] = keyin_data.get(count_key, 0) + 1
                print(f"{count_key} +1，现在为: {keyin_data[count_key]}")
                write_keyin_detail(keyin_data)
                
                # 更新weight
                if item_category in type_weight_map:
                    new_weight = type_weight_map[item_category]()
                    print(f"权重已更新: {item_category} = {new_weight:.2f}")
    
    time.sleep(4)  # 等待2秒，确保界面更新
    # 点击中心位置 (960, 540)
    ck.click_at_position(960, 540)
    time.sleep(2)  # 等待2秒，确保界面更新
    # 点击中心位置 (960, 540)
    ck.click_at_position(960, 540)
    time.sleep(3)  # 等待3秒，确保界面更新

    # 第二次查找和选择
    print("第二次查找刻印...")
    found_keyins2 = find_keyin(region=region, category=category, use_similarity=current_use_similarity, use_special_matching=current_special_matching)
    print(f"第二次找到的刻印: {found_keyins2}")
    
    # 如果没有匹配到keyin文本，且category不为None，尝试将category设为None再试一次
    if not found_keyins2 and category is not None:
        print("没有匹配到keyin文本，尝试将category设为None再试一次...")
        # 当category设为None时，开启特殊匹配
        found_keyins2 = find_keyin(region=region, category=None, use_similarity=True, use_special_matching=True)
        print(f"第二次查找的刻印（重试）: {found_keyins2}")
    
    # 过滤掉zhenwo刻印
    found_keyins2 = [item for item in found_keyins2 if get_category_from_keyin_name(item[1]) != "zhenwo"]
    if found_keyins2:
        print(f"过滤后剩余的刻印: {found_keyins2}")
    
    # 如果没有提供category，尝试根据找到的刻印名称识别类别
    if category is None and found_keyins2:
        print("未提供category，尝试自动识别类别...")
        for item in found_keyins2:
            item_name = item[1]
            identified_category = get_category_from_keyin_name(item_name)
            if identified_category:
                print(f"识别到类别: {identified_category} 对应刻印: {item_name}")
                # 重新构造只包含该类别的刻印列表
                filtered_keyins = [item for item in found_keyins2 if get_category_from_keyin_name(item[1]) == identified_category]
                found_keyins2 = filtered_keyins
                break
    
    if found_keyins2:
        selected_keyin2 = select_keyin(found_keyins2, character_type)
        if selected_keyin2:
                print(f"第二次选择的刻印: {selected_keyin2}")
                # 点击位置（已在OCR处理中减去padding）
                ck.click_at_position(selected_keyin2[2][0], selected_keyin2[2][1])
                ck.keyboard_i_press_release()
                selected_keyins.append(selected_keyin2)
                
                # 更新count和weight
                item_category = selected_keyin2[0]
                read_keyin_detail, write_keyin_detail = lazy_import()
                keyin_data = read_keyin_detail()
                
                # 更新count
                count_key = f"{item_category}_count"
                keyin_data[count_key] = keyin_data.get(count_key, 0) + 1
                print(f"{count_key} +1，现在为: {keyin_data[count_key]}")
                write_keyin_detail(keyin_data)
                
                # 更新weight
                if item_category in type_weight_map:
                    new_weight = type_weight_map[item_category]()
                    print(f"权重已更新: {item_category} = {new_weight:.2f}")
    
    # 只返回类别（两次选择的是同一个类别）
    return selected_keyins[0][0] if selected_keyins else None


if __name__ == "__main__":
    # 检查是否以管理员身份运行
    if not is_admin():
        print("程序需要以管理员身份运行才能正常工作！")
        print("正在尝试自动提权...")
        
        if run_as_admin():
            print("请在弹出的UAC提示中选择'是'以继续...")
            sys.exit(0)  # 退出当前进程，等待管理员权限进程启动
        else:
            print("自动提权失败，请手动右键点击程序并选择'以管理员身份运行'")
            input("按回车键退出...")
            sys.exit(1)
            
    # 聚焦BH3窗口
    print("\n0. 执行focus_bh3_window函数：")
    success_focus = focus_bh3_window()
    if success_focus:
        print("BH3窗口已聚焦！")
    else:
        print("BH3窗口聚焦失败！\n请确保游戏打开\n或联系tokutouseki")

    time.sleep(2)
    
    # 调用single_select_keyin函数执行单次刻印选择
    print("\n执行single_select_keyin函数：")
    selected_keyin = single_select_keyin(region=(748, 267, 1864, 933), character_type="yuansu", show_debug=False,preprocess=True,use_special_matching=True)
    print(f"\n最终选择的刻印: {selected_keyin}")