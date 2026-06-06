import sys
import os
import time
import json
# 将父目录添加到sys.path中，以便能够导入上层目录的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import save_output
from on_window import focus_bh3_window, run_as_admin, is_admin
import ocr.ocr_click as oc
import templates.clicks_keyboard as ck

# 定义keyin_detail.json文件路径
KEYIN_DETAIL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ocr", "keyin_detail.json")

# 读取keyin_detail.json文件
def read_keyin_detail():
    """读取keyin_detail.json文件内容"""
    if os.path.exists(KEYIN_DETAIL_PATH):
        with open(KEYIN_DETAIL_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # 如果文件不存在，返回默认值
        return {
            "need_init": False,
            "jiushi_count": 0,
            "jiushi_weight": 0.73,
            "zhenwo_count": 0,
            "zhenwo_weight": 1.0,
            "jielv_count": 0,
            "jielv_weight": 0.1,
            "huangjin_count": 0,
            "huangjin_weight": 0.72,
            "luoxuan_count": 0,
            "luoxuan_weight": 0.1,
            "aomie_count": 0,
            "aomie_weight": 0.70,
            "tianhui_count": 0,
            "tianhui_weight": 0.1,
            "chana_count": 0,
            "chana_weight": 0.4,
            "xvguang_count": 0,
            "xvguang_weight": 0.1,
            "wuxian_count": 0,
            "wuxian_weight": 0.1,
            "fanxing_count": 0,
            "fanxing_weight": 0.48,
            "fusheng_count": 0,
            "fusheng_weight": 0.71,
            "kongmeng_count": 0,
            "kongmeng_weight": 0.49,
            "letu_reset_count": 0,
            "letu_reset_weight": 0.5
        }

# 写入keyin_detail.json文件
def write_keyin_detail(data):
    """写入内容到keyin_detail.json文件"""
    with open(KEYIN_DETAIL_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 救世
def jiushi(all=True,yuansu=False,wuli=False):
    # 读取keyin_detail.json文件
    keyin_data = read_keyin_detail()
    jiushi_count = keyin_data.get("jiushi_count", 0)
    jiushi_weight = keyin_data.get("jiushi_weight", 0)
    print(f"jiushi_count: {jiushi_count}")
    print(f"jiushi_weight: {jiushi_weight}")
    jiushi_options = [
        (oc.click_jiushi_shiyuzhedejinbei, "救世_施予者的金杯_全伤",0),
        (oc.click_jiushi_shouwangzhedezhuishi, "救世_守王者的坠饰_物理",1),
        (oc.click_jiushi_lieshazhedejiamian, "救世_猎杀者的假面_物理",2),
        (oc.click_jiushi_zhiyuezhedeshengqi, "救世_制约者的圣器_元素",3),
        (oc.click_jiushi_busizhedelaoyin, "救世_不死者的烙印_元素",4),
        (oc.click_jiushi_qiudaozhedefayi, "救世_求道者的法衣_能量",5),
        (oc.click_jiushi_jiushizhedewangjian, "救世_救世者的王剑_核心",6),
        (oc.click_jiushi_jiushizhedequnji, "救世_救世者的麇集_增幅",7),
        (oc.click_jiushi_jiushizhedeyuanzheng, "救世_救世者的远征_增幅",8),
        (oc.click_jiushi_jiushizhedeyuxiang, "救世_救世者的余响_增幅",9),
        (oc.click_jiushi_jiushizhedecanmeng, "救世_救世者的残梦_增幅",10),
        (oc.click_jiushi_jiushizhedejueduan, "救世_救世者的决断_增幅",11),
        (oc.click_jiushi_jiushizhedekaixuan, "救世_救世者的凯旋_增幅",12)
    ]
    yuansu_index = [0,3,4,5,6,7,8,9,10,11,12]
    wuli_index = [0,1,2,5,6,7,8,9,10,11,12]
    all_use_index = [0,1,2,3,4,5,6,7,8,9,10,11,12]
    
    if all:
        target_index = all_use_index
    elif yuansu:
        target_index = yuansu_index
    elif wuli:
        target_index = wuli_index
    else:
        target_index = all_use_index
    
    # 第一次尝试：按照逻辑选择的index来
    print("\n第一次尝试：按照逻辑选择的index来")
    for index in target_index:
        click_func, description, _ = jiushi_options[index]
        if click_func():
            print(f"\n 点击{description}")
            jiushi_count += 1
            # 更新keyin_data并写入文件
            keyin_data["jiushi_count"] = jiushi_count
            write_keyin_detail(keyin_data)
            print(f"jiushi_count: {jiushi_count}")
            ck.keyboard_i_press_release()
            return
    
    # 第二次尝试：把所有可以选择的options都试一次
    print("\n第二次尝试：把所有可以选择的options都试一次")
    for click_func, description, _ in jiushi_options:
        if click_func():
            print(f"\n 点击{description}")
            jiushi_count += 1
            # 更新keyin_data并写入文件
            keyin_data["jiushi_count"] = jiushi_count
            write_keyin_detail(keyin_data)
            print(f"jiushi_count: {jiushi_count}")
            ck.keyboard_i_press_release()
            return

# 戒律
def jielv(all=True,yuansu=False,wuli=False):
    # 读取keyin_detail.json文件
    keyin_data = read_keyin_detail()
    jielv_count = keyin_data.get("jielv_count", 0)
    jielv_weight = keyin_data.get("jielv_weight", 0)
    print(f"jielv_count: {jielv_count}")
    print(f"jielv_weight: {jielv_weight}")
    jielv_options = [
        (oc.click_jielv_qiyi_bukebeipan, "戒律_其一，不可背叛_普攻",0),
        (oc.click_jielv_qier_bukeqiman, "戒律_其二，不可欺瞒_免伤",1),
        (oc.click_jielv_qisan_bukebaoli, "戒律_其三，不可roff_能量",2),
        (oc.click_jielv_qisi_bukewangxin, "戒律_其四，不可妄行_爆发",3),
        (oc.click_jielv_qiwu_bukeweiyan, "戒律_其五，不可伪言_全伤",4),
        (oc.click_jielv_qiliu_bukechenlun, "戒律_其六，不可沉沦_全伤",5),
        (oc.click_jielv_ru_dangweijielvsuoyou, "戒律_汝，当为戒律所佑_核心",6),
        (oc.click_jielv_ru_dangjianzhuedechen, "戒律_汝，当见诸恶得惩_增幅",7),
        (oc.click_jielv_ru_dangjianzhushandexing, "戒律_汝，当见诸善得行_增幅",8),
        (oc.click_jielv_ru_dangjianzhuyuandegui, "戒律_汝，当见诸愿得归_增幅",9),
    ]
    all_use_index = [0,1,2,3,4,5,6,7,8,9]
    
    if all:
        target_index = all_use_index
    elif yuansu:
        target_index = all_use_index
    elif wuli:
        target_index = all_use_index
    else:
        target_index = all_use_index
    
    # 第一次尝试：按照逻辑选择的index来
    print("\n第一次尝试：按照逻辑选择的index来")
    for index in target_index:
        click_func, description, _ = jielv_options[index]
        if click_func():
            print(f"\n 点击{description}")
            jielv_count += 1
            # 更新keyin_data并写入文件
            keyin_data["jielv_count"] = jielv_count
            write_keyin_detail(keyin_data)
            print(f"jielv_count: {jielv_count}")
            ck.keyboard_i_press_release()
            return
    
    # 第二次尝试：把所有可以选择的options都试一次
    print("\n第二次尝试：把所有可以选择的options都试一次")
    for click_func, description, _ in jielv_options:
        if click_func():
            print(f"\n 点击{description}")
            jielv_count += 1
            # 更新keyin_data并写入文件
            keyin_data["jielv_count"] = jielv_count
            write_keyin_detail(keyin_data)
            print(f"jielv_count: {jielv_count}")
            ck.keyboard_i_press_release()
            return

# 黄金  
def huangjin(all=True,yuansu=False,wuli=False):
    # 读取keyin_detail.json文件
    keyin_data = read_keyin_detail()
    huangjin_count = keyin_data.get("huangjin_count", 0)
    huangjin_weight = keyin_data.get("huangjin_weight", 0)
    print(f"huangjin_count: {huangjin_count}")
    print(f"huangjin_weight: {huangjin_weight}")
    huangjin_options = [
        (oc.click_huangjin_leyuandexuanxv, "黄金_乐园的宣叙_全伤",0),
        (oc.click_huangjin_xiliudexuanxv, "黄金_溪流的宣叙_全伤",1),
        (oc.click_huangjin_feiniaodexuanxv, "黄金_飞鸟的宣叙_免伤",2),
        (oc.click_huangjin_guolindexuanxv, "黄金_果林的宣叙_回能",3),
        (oc.click_huangjin_meijiudexuanxv, "黄金_美酒的宣叙_回能",4),
        (oc.click_huangjin_baoyvdexuanshu, "黄金_宝玉的宣叙_能量",5),
        (oc.click_huangjin_huangjindeyuyin, "黄金_黄金的余音_核心",6),
        (oc.click_huangjin_kurandeyuyin, "黄金_枯荣的余音_增幅",7),
        (oc.click_huangjin_qifengdeyuyin, "黄金_凄风的余音_增幅",8),
        (oc.click_huangjin_jiyedeyuyin, "黄金_寂夜的余音_增幅",9)
    ]

    all_use_index = [0,1,5,6,7,8,9]
    
    if all:
        target_index = all_use_index
    elif yuansu:
        target_index = all_use_index
    elif wuli:
        target_index = all_use_index
    else:
        target_index = all_use_index
    
    # 第一次尝试：按照逻辑选择的index来
    print("\n第一次尝试：按照逻辑选择的index来")
    for index in target_index:
        click_func, description, _ = huangjin_options[index]
        if click_func():
            print(f"\n 点击{description}")
            huangjin_count += 1
            # 更新keyin_data并写入文件
            keyin_data["huangjin_count"] = huangjin_count
            write_keyin_detail(keyin_data)
            print(f"huangjin_count: {huangjin_count}")
            ck.keyboard_i_press_release()
            return
    
    # 第二次尝试：把所有可以选择的options都试一次
    print("\n第二次尝试：把所有可以选择的options都试一次")
    for click_func, description, _ in huangjin_options:
        if click_func():
            print(f"\n 点击{description}")
            huangjin_count += 1
            # 更新keyin_data并写入文件
            keyin_data["huangjin_count"] = huangjin_count
            write_keyin_detail(keyin_data)
            print(f"huangjin_count: {huangjin_count}")
            ck.keyboard_i_press_release()
            return

#螺旋  
def luoxuan(all=True,yuansu=False,wuli=False):
    # 读取keyin_detail.json文件
    keyin_data = read_keyin_detail()
    luoxuan_count = keyin_data.get("luoxuan_count", 0)
    luoxuan_weight = keyin_data.get("luoxuan_weight", 0)
    print(f"luoxuan_count: {luoxuan_count}")
    print(f"luoxuan_weight: {luoxuan_weight}")
    luoxuan_options = [
        (oc.click_luoxuan_diyimumoshu, "螺旋_第一幕魔术_全伤",0),
        (oc.click_luoxuan_diermuzhongbai, "螺旋_第二幕钟摆_全伤",1),
        (oc.click_luoxuan_disanmumaodun, "螺旋_第三幕矛盾_全伤",2),
        (oc.click_luoxuan_disimutangchi, "螺旋_第四幕汤匙_全伤",3),
        (oc.click_luoxuan_diwumuzhusi, "螺旋_第五幕蛛丝_全伤",4),
        (oc.click_luoxuan_diliumuchixiao, "螺旋_第六幕嗤笑_能量",5),
        (oc.click_luoxuan_mujianjvdianmodeluoxuan, "螺旋_幕间剧颠末的螺旋_核心",6), 
        (oc.click_luoxuan_muoujvyaocuodejianlao, "螺旋_木偶剧爻错的监牢_增幅",7),
        (oc.click_luoxuan_yansujvchenmodeshiyuan, "螺旋_严肃剧沉默的始源_增幅",8),
        (oc.click_luoxuan_chuanqijvjiaodiedezhizhen, "螺旋_传奇剧交叠的指针_增幅",9),
       
    ]

    all_use_index = [0,1,2,3,4,5,6,7,8,9]
    
    if all:
        target_index = all_use_index
    elif yuansu:
        target_index = all_use_index
    elif wuli:
        target_index = all_use_index
    else:
        target_index = all_use_index
    
    # 第一次尝试：按照逻辑选择的index来
    print("\n第一次尝试：按照逻辑选择的index来")
    for index in target_index:
        click_func, description, _ = luoxuan_options[index]
        if click_func():
            print(f"\n 点击{description}")
            luoxuan_count += 1
            # 更新keyin_data并写入文件
            keyin_data["luoxuan_count"] = luoxuan_count
            write_keyin_detail(keyin_data)
            print(f"luoxuan_count: {luoxuan_count}")
            ck.keyboard_i_press_release()
            return
    
    # 第二次尝试：把所有可以选择的options都试一次
    print("\n第二次尝试：把所有可以选择的options都试一次")
    for click_func, description, _ in luoxuan_options:
        if click_func():
            print(f"\n 点击{description}")
            luoxuan_count += 1
            # 更新keyin_data并写入文件
            keyin_data["luoxuan_count"] = luoxuan_count
            write_keyin_detail(keyin_data)
            print(f"luoxuan_count: {luoxuan_count}")
            ck.keyboard_i_press_release()
            return

# 鏖灭
def aomie(all=True,yuansu=False,wuli=False):
    # 读取keyin_detail.json文件
    keyin_data = read_keyin_detail()
    aomie_count = keyin_data.get("aomie_count", 0)
    aomie_weight = keyin_data.get("aomie_weight", 0)
    print(f"aomie_count: {aomie_count}")
    print(f"aomie_weight: {aomie_weight}")
    aomie_options = [
        (oc.click_aomie_jianfeng_jianzhong_jianheng, "鏖灭_剑锋·剑冢·剑痕_全伤",0),
        (oc.click_aomie_chigu_chixie_chilian, "鏖灭_赤骨·赤血·赤练_全伤",1),
        (oc.click_aomie_kuangxin_kuangren_kuangyan, "鏖灭_狂信·狂人·狂言_免伤",2),
        (oc.click_aomie_minglu_mingchuan_mingke, "鏖灭_命路·命舛·命刻_生命",3),
        (oc.click_aomie_wuwang_wuxin_wugui, "鏖灭_无妄·无心·无归_全伤",4),
        (oc.click_aomie_weishen_weiwo_weiyi, "鏖灭_唯神·唯我·唯一_能量",5),
        (oc.click_aomie_aodou_aozhan_aosha_aomie, "鏖灭_鏖斗·鏖战·鏖杀·鏖灭_核心_燃血",6),
        (oc.click_aomie_feiren_feigui_feishen_feitian, "鏖灭_非人·非鬼·非神·非天_增幅_燃血",7),
        (oc.click_aomie_yiren_yimian_yiqi_yitu, "鏖灭_一人·一面·一契 一途_增幅_燃血",8),
        (oc.click_aomie_qianjun_qianzhuan_qiannan_qianjie, "鏖灭_千钧·千转·千难·千劫_增幅_燃血",9),
        (oc.click_aomie_aobing_aojian_aoguo_aomie, "鏖灭_鏖兵·鏖剪·鏖馘·鏖灭_核心_回血",10),
        (oc.click_aomie_wusi_wusheng_wumie_wucun, "鏖灭_无死·无生·无灭·无存_增幅_回血",11),
        (oc.click_aomie_gutu_guguo_guyou_guren, "鏖灭_故土·故国·故友·故人_增幅_回血",12),
        (oc.click_aomie_fenshen_fengu_fenxin_fenhun, "鏖灭_焚身·焚骨·焚心·焚魂_增幅_回血",13)
    ]

    all_use_index = [0,1,3,4,10,11,12,13]
    
    if all:
        target_index = all_use_index
    elif yuansu:
        target_index = all_use_index
    elif wuli:
        target_index = all_use_index
    else:
        target_index = all_use_index
    
    # 第一次尝试：按照逻辑选择的index来
    print("\n第一次尝试：按照逻辑选择的index来")
    for index in target_index:
        click_func, description, _ = aomie_options[index]
        if click_func():
            print(f"\n 点击{description}")
            aomie_count += 1
            # 更新keyin_data并写入文件
            keyin_data["aomie_count"] = aomie_count
            write_keyin_detail(keyin_data)
            print(f"aomie_count: {aomie_count}")
            ck.keyboard_i_press_release()
            return
    
    # 第二次尝试：把所有可以选择的options都试一次
    print("\n第二次尝试：把所有可以选择的options都试一次")
    for click_func, description, _ in aomie_options:
        if click_func():
            print(f"\n 点击{description}")
            aomie_count += 1
            # 更新keyin_data并写入文件
            keyin_data["aomie_count"] = aomie_count
            write_keyin_detail(keyin_data)
            print(f"aomie_count: {aomie_count}")
            ck.keyboard_i_press_release()
            return

# 天慧
def tianhui(all=True,yuansu=False,wuli=False):
    # 读取keyin_detail.json文件
    keyin_data = read_keyin_detail()
    tianhui_count = keyin_data.get("tianhui_count", 0)
    tianhui_weight = keyin_data.get("tianhui_weight", 0)
    print(f"tianhui_count: {tianhui_count}")
    print(f"tianhui_weight: {tianhui_weight}")
    tianhui_options = [ 
        (oc.click_tianhui_sumingzhizhenyan, "天慧_宿命之箴言_全伤",0),
        (oc.click_tianhui_tianyanzhizhenyan, "天慧_天眼之箴言_全伤",1),
        (oc.click_tianhui_tianerzhizhenyan, "天慧_天耳之箴言_免伤",2),
        (oc.click_tianhui_taxinzhizhenyan, "天慧_他心之箴言_能量",3),
        (oc.click_tianhui_shenzuzhizhenyan, "天慧_神足之箴言_物理",4),
        (oc.click_tianhui_loujinzhizhenyan, "天慧_漏尽之箴言_元素",5),
        (oc.click_tianhui_tianhuizhizhenyan, "天慧_天慧之真言_核心",6),
        (oc.click_tianhui_wuchangzhizhenyan, "天慧_无常之真言_增幅",7),
        (oc.click_tianhui_wuwozhizhenyan, "天慧_无我之真言_增幅",8),
        (oc.click_tianhui_jijingzhizhenyan, "天慧_寂静之真言_增幅",9),  
    ]
    all_use_index = [0,1,3,6,7,8,9]
    
    if all:
        target_index = all_use_index
    elif yuansu:
        target_index = all_use_index
    elif wuli:
        target_index = all_use_index
    else:
        target_index = all_use_index
    
    # 第一次尝试：按照逻辑选择的index来
    print("\n第一次尝试：按照逻辑选择的index来")
    for index in target_index:
        click_func, description, _ = tianhui_options[index]
        if click_func():
            print(f"\n 点击{description}")
            tianhui_count += 1
            # 更新keyin_data并写入文件
            keyin_data["tianhui_count"] = tianhui_count
            write_keyin_detail(keyin_data)
            print(f"tianhui_count: {tianhui_count}")
            ck.keyboard_i_press_release()
            return
    
    # 第二次尝试：把所有可以选择的options都试一次
    print("\n第二次尝试：把所有可以选择的options都试一次")
    for click_func, description, _ in tianhui_options:
        if click_func():
            print(f"\n 点击{description}")
            tianhui_count += 1
            # 更新keyin_data并写入文件
            keyin_data["tianhui_count"] = tianhui_count
            write_keyin_detail(keyin_data)
            print(f"tianhui_count: {tianhui_count}")
            ck.keyboard_i_press_release()
            return

# 刹那
def chana(all=True,yuansu=False,wuli=False):
    # 读取keyin_detail.json文件
    keyin_data = read_keyin_detail()
    chana_count = keyin_data.get("chana_count", 0)
    chana_weight = keyin_data.get("chana_weight", 0)
    print(f"chana_count: {chana_count}")
    print(f"chana_weight: {chana_weight}")
    chana_options = [

        (oc.click_chana_liaoluanbaihuamei, "刹那_缭乱百花梅_速度",0),
        (oc.click_chana_liaoluanbaihuahongye, "刹那_缭乱百花虹_全伤",1),
        (oc.click_chana_liaoluanbaihuamudan, "刹那_缭乱百花牡丹_全伤",2),
        (oc.click_chana_liaoluanbaihuajv, "刹那_缭乱百花菊_闪避",3),
        (oc.click_chana_liaoluanbaihuateng, "刹那_缭乱百花藤_闪避",4),
        (oc.click_chana_liaoluanbaihuachangpu, "刹那_缭乱百花菖蒲_能量",5),
        (oc.click_chana_chanayidaoyingshangmu, "刹那_刹那一刀樱上幕_核心",6),
        (oc.click_chana_chanayidaoyusiguang, "刹那_刹那一刀雨四光_增幅",7),
        (oc.click_chana_chanayidaoyuejianjiu, "刹那_刹那一刀月见酒_增幅",8),
        (oc.click_chana_chanayidaozhuludie, "刹那_刹那一刀猪鹿蝶_增幅",9),
    ]

    all_use_index = [0,1,2,5,6,7,8,9]
    
    if all:
        target_index = all_use_index
    elif yuansu:
        target_index = all_use_index
    elif wuli:
        target_index = all_use_index
    else:
        target_index = all_use_index
    
    # 第一次尝试：按照逻辑选择的index来
    print("\n第一次尝试：按照逻辑选择的index来")
    for index in target_index:
        click_func, description, _ = chana_options[index]
        if click_func():
            print(f"\n 点击{description}")
            chana_count += 1
            # 更新keyin_data并写入文件
            keyin_data["chana_count"] = chana_count
            write_keyin_detail(keyin_data)
            print(f"chana_count: {chana_count}")
            ck.keyboard_i_press_release()
            return
    
    # 第二次尝试：把所有可以选择的options都试一次
    print("\n第二次尝试：把所有可以选择的options都试一次")
    for click_func, description, _ in chana_options:
        if click_func():
            print(f"\n 点击{description}")
            chana_count += 1
            # 更新keyin_data并写入文件
            keyin_data["chana_count"] = chana_count
            write_keyin_detail(keyin_data)
            print(f"chana_count: {chana_count}")
            ck.keyboard_i_press_release()
            return

# 旭光
def xvguang(all=True,yuansu=False,wuli=False):
    # 读取keyin_detail.json文件
    keyin_data = read_keyin_detail()
    xvguang_count = keyin_data.get("xvguang_count", 0)
    xvguang_weight = keyin_data.get("xvguang_weight", 0)
    print(f"xvguang_count: {xvguang_count}")
    print(f"xvguang_weight: {xvguang_weight}")
    xvguang_options = [ 
        (oc.click_xvguang_xiedubuguizhizhua, "旭光_亵渎不归之爪_流血",0),
        (oc.click_xvguang_yanbixueyezhiyi, "旭光_掩蔽血月之翼_流血",1),
        (oc.click_xvguang_silieankongzhijiao, "旭光_撕裂暗空之角_流血",2),
        (oc.click_xvang_fushixieyuanzhiyan, "旭光_俯视邪渊之眼_全伤",3),
        (oc.click_xvguang_huibangliuhuangzhixi, "旭光_毁谤硫磺之息_能量",4),
        (oc.click_xvguang_nijieqizuizhixin, "旭光_逆结七罪之心_增益",5),
        (oc.click_xvguang_xvguang_changmingbuluo, "旭光_旭光_长明不落_核心",6),
        (oc.click_xvguang_yingxiong_dudanxingshuai, "旭光_英雄_独担兴衰_增幅",7),
        (oc.click_xvguang_shane_liangfennandu, "旭光_善恶_两分难渡_增幅",8),
        (oc.click_xvguang_sunuo_baizheweiyi, "旭光_宿诺_百折未易_增益",9),
    ]

    all_use_index = [3,4,6,7,8]
    
    if all:
        target_index = all_use_index
    elif yuansu:
        target_index = all_use_index
    elif wuli:
        target_index = all_use_index
    else:
        target_index = all_use_index
    
    # 第一次尝试：按照逻辑选择的index来
    print("\n第一次尝试：按照逻辑选择的index来")
    for index in target_index:
        click_func, description, _ = xvguang_options[index]
        if click_func():
            print(f"\n 点击{description}")
            xvguang_count += 1
            # 更新keyin_data并写入文件
            keyin_data["xvguang_count"] = xvguang_count
            write_keyin_detail(keyin_data)
            print(f"xvguang_count: {xvguang_count}")
            ck.keyboard_i_press_release()
            return
    
    # 第二次尝试：把所有可以选择的options都试一次
    print("\n第二次尝试：把所有可以选择的options都试一次")
    for click_func, description, _ in xvguang_options:
        if click_func():
            print(f"\n 点击{description}")
            xvguang_count += 1
            # 更新keyin_data并写入文件
            keyin_data["xvguang_count"] = xvguang_count
            write_keyin_detail(keyin_data)
            print(f"xvguang_count: {xvguang_count}")
            ck.keyboard_i_press_release()
            return
        
# 无限
def wuxian(all=True,yuansu=False,wuli=False):
    # 读取keyin_detail.json文件
    keyin_data = read_keyin_detail()
    wuxian_count = keyin_data.get("wuxian_count", 0)
    wuxian_weight = keyin_data.get("wuxian_weight", 0)
    print(f"wuxian_count: {wuxian_count}")
    print(f"wuxian_weight: {wuxian_weight}")
    wuxian_options = [
        (oc.click_wuxian_lichideV, "无限_利齿的V_全伤",0),
        (oc.click_wuxian_chanhuandeP, "无限_缠环的P_全伤",1),
        (oc.click_wuxian_jingmodeB, "无限_静默的B_免伤",2),
        (oc.click_wuxian_wendudeE, "无限_吻毒的E_全伤",3),
        (oc.click_wuxian_xiyingdeC, "无限_栖影的C_冷却",4),
        (oc.click_wuxian_antongdeT, "无限_黯瞳的T_冷却",5),
        (oc.click_wuxian_wuxiandeX, "无限_无限的X_核心",6),
        (oc.click_wuxian_siwangdeX, "无限_死亡的X_增幅",7),
        (oc.click_wuxian_weizhideX, "无限_未知的X_增幅",8),
        (oc.click_wuxian_xinshengdeX, "无限_新生的X_增幅",9),
    ]
    all_use_index = [0,1,3,6,7,8,9]
    
    if all:
        target_index = all_use_index
    elif yuansu:
        target_index = all_use_index
    elif wuli:
        target_index = all_use_index
    else:
        target_index = all_use_index
    
    # 第一次尝试：按照逻辑选择的index来
    print("\n第一次尝试：按照逻辑选择的index来")
    for index in target_index:
        click_func, description, _ = wuxian_options[index]
        if click_func():
            print(f"\n 点击{description}")
            wuxian_count += 1
            # 更新keyin_data并写入文件
            keyin_data["wuxian_count"] = wuxian_count
            write_keyin_detail(keyin_data)
            print(f"wuxian_count: {wuxian_count}")
            ck.keyboard_i_press_release()
            return
    
    # 第二次尝试：把所有可以选择的options都试一次
    print("\n第二次尝试：把所有可以选择的options都试一次")
    for click_func, description, _ in wuxian_options:
        if click_func():
            print(f"\n 点击{description}")
            wuxian_count += 1
            # 更新keyin_data并写入文件
            keyin_data["wuxian_count"] = wuxian_count
            write_keyin_detail(keyin_data)
            print(f"wuxian_count: {wuxian_count}")
            ck.keyboard_i_press_release()
            return

# 繁星
def fanxing(all=True,yuansu=False,wuli=False):
    # 读取keyin_detail.json文件
    keyin_data = read_keyin_detail()
    fanxing_count = keyin_data.get("fanxing_count", 0)
    fanxing_weight = keyin_data.get("fanxing_weight", 0)
    print(f"fanxing_count: {fanxing_count}")
    print(f"fanxing_weight: {fanxing_weight}")
    fanxing_options = [
        (oc.click_fanxing_hongsede_rerede, "繁星_红色的_热热的_全伤",0),
        (oc.click_fanxing_lansede_lenlende, "繁星_蓝色的_冷冷的_减益",1),
        (oc.click_fanxing_huangsede_nuannuande, "繁星_黄色的_暖暖的_全伤",2),
        (oc.click_fanxing_heisede_anande, "繁星_黑色的_暗暗的_全伤",3),
        (oc.click_fanxing_baiseed_liangliangde, "繁星_白色的_亮亮的_能量",4),
        (oc.click_fanxing_huisede_kongkongde, "繁星_灰色的_空空的_增益",5),
        (oc.click_fanxing_xiangshifanxing_shanyaozhede, "繁星_像是繁星_闪耀着的_核心",6),
        (oc.click_fanxing_xiangshiyehua_zhanfangzhede, "繁星_像是野花_绽放着的_增幅",7),
        (oc.click_fanxing_xiangshihuoyan_ranshaozhede, "繁星_像是火焰_燃烧着的_增益",8),
        (oc.click_fanxing_xiangshiyezi_shuzhanzhede, "繁星_像是叶子_舒展着的_增幅",9),
    ]

    all_use_index = [0,1,2,6,7,8,9]
    
    if all:
        target_index = all_use_index
    elif yuansu:
        target_index = all_use_index
    elif wuli:
        target_index = all_use_index
    else:
        target_index = all_use_index
    
    # 第一次尝试：按照逻辑选择的index来
    print("\n第一次尝试：按照逻辑选择的index来")
    for index in target_index:
        click_func, description, _ = fanxing_options[index]
        if click_func():
            print(f"\n 点击{description}")
            fanxing_count += 1
            # 更新keyin_data并写入文件
            keyin_data["fanxing_count"] = fanxing_count
            write_keyin_detail(keyin_data)
            print(f"fanxing_count: {fanxing_count}")
            ck.keyboard_i_press_release()
            return
    
    # 第二次尝试：把所有可以选择的options都试一次
    print("\n第二次尝试：把所有可以选择的options都试一次")
    for click_func, description, _ in fanxing_options:
        if click_func():
            print(f"\n 点击{description}")
            fanxing_count += 1
            # 更新keyin_data并写入文件
            keyin_data["fanxing_count"] = fanxing_count
            write_keyin_detail(keyin_data)
            print(f"fanxing_count: {fanxing_count}")
            ck.keyboard_i_press_release()
            return

# 浮生
def fusheng(all=True,yuansu=False,wuli=False):
    # 读取keyin_detail.json文件
    keyin_data = read_keyin_detail()
    fusheng_count = keyin_data.get("fusheng_count", 0)
    fusheng_weight = keyin_data.get("fusheng_weight", 0)
    print(f"fusheng_count: {fusheng_count}")
    print(f"fusheng_weight: {fusheng_weight}")
    fusheng_options = [
        (oc.click_fusheng_xinglumanman, "浮生_行路漫漫_全伤",0),
        (oc.click_fusheng_riyuecuotuo, "浮生_日月蹉跎_物理",1),
        (oc.click_fusheng_xuanyibuzai, "浮生_玄衣不再_元素",2),
        (oc.click_fusheng_jiumengruzuo, "浮生_旧梦如昨_元素",3),
        (oc.click_fusheng_zongshixunde, "浮生_纵使寻得_免伤",4),
        (oc.click_fusheng_yusheiyanshuo, "浮生_与谁诉说_物理",5),
        (oc.click_fusheng_fushengmangmang_baitaijieku, "浮生_浮生茫茫_百态皆苦_核心",6),
        (oc.click_fusheng_fanchenzongzong_yiweinandu, "浮生_凡尘总总_一苇难渡_增幅",7),
        (oc.click_fusheng_ruyusuifeng_silangzhuliu, "浮生_如羽随风_似浪逐流_增幅",8),
        (oc.click_fusheng_zenkanmengxing_nanxmikuitu, "浮生_怎堪梦醒_难觅归途_增幅",9),
        (oc.click_fusheng_sicengxiangshi_queyouxiangwang, "浮生_似曾相识，却又相忘_增幅",10)
    ]
    yuansu_index = [0,2,3,4,6,7,8,9,10]
    wuli_index = [0,1,5,4,6,7,8,9,10]
    
    if all:
        target_index = yuansu_index
    elif yuansu:
        target_index = yuansu_index
    elif wuli:
        target_index = wuli_index
    else:
        target_index = yuansu_index
    
    # 第一次尝试：按照逻辑选择的index来
    print("\n第一次尝试：按照逻辑选择的index来")
    for index in target_index:
        click_func, description, _ = fusheng_options[index]
        if click_func():
            print(f"\n 点击{description}")
            fusheng_count += 1
            # 更新keyin_data并写入文件
            keyin_data["fusheng_count"] = fusheng_count
            write_keyin_detail(keyin_data)
            print(f"fusheng_count: {fusheng_count}")
            ck.keyboard_i_press_release()
            return
    
    # 第二次尝试：把所有可以选择的options都试一次
    print("\n第二次尝试：把所有可以选择的options都试一次")
    for click_func, description, _ in fusheng_options:
        if click_func():
            print(f"\n 点击{description}")
            fusheng_count += 1
            # 更新keyin_data并写入文件
            keyin_data["fusheng_count"] = fusheng_count
            write_keyin_detail(keyin_data)
            print(f"fusheng_count: {fusheng_count}")
            ck.keyboard_i_press_release()
            return

# 空梦
def kongmeng(all=True,yuansu=False,wuli=False):
    # 读取keyin_detail.json文件
    keyin_data = read_keyin_detail()
    kongmeng_count = keyin_data.get("kongmeng_count", 0)
    kongmeng_weight = keyin_data.get("kongmeng_weight", 0)
    print(f"kongmeng_count: {kongmeng_count}")
    print(f"kongmeng_weight: {kongmeng_weight}")
    kongmeng_options = [
        (oc.click_kongmeng_maomaozhizhenyan, "空梦_猫猫之箴言_全伤",0),
        (oc.click_kongmeng_gangrennijuanzhiwei, "空梦_钢刃逆卷之尾_全伤",1),
        (oc.click_kongmeng_jiexiangdexuanxv, "空梦_街巷的宣叙_能量",2),
        (oc.click_kongmeng_lingdongdePaC, "空梦_灵动的P&C_能量",3),
        (oc.click_kongmeng_xingshangzhedezhexue, "空梦_行商者的哲学_银币",4),
        (oc.click_kongmeng_zhiqiande_shanshande, "空梦_值钱的，闪闪的_银币",5),
        (oc.click_kongmeng_kongmeng_kongji_kongwo_konghuan, "空梦_空梦_空集_空我_空欢_核心",6),
        (oc.click_kongmeng_jixingduanjvlaoban, "空梦_即兴短剧老板_增幅",7),
        (oc.click_kongmeng_chanayizhuamaomaoquan, "空梦_刹那一爪猫猫拳_增幅",8),
        (oc.click_kongmeng_zan_cidimingbugaijue, "空梦_咱_此地命不该绝_增幅",9),
    ]

    all_use_index = [0,1,2,3,6,7,8,9]
    
    if all:
        target_index = all_use_index
    elif yuansu:
        target_index = all_use_index
    elif wuli:
        target_index = all_use_index
    else:
        target_index = all_use_index
    
    # 第一次尝试：按照逻辑选择的index来
    print("\n第一次尝试：按照逻辑选择的index来")
    for index in target_index:
        click_func, description, _ = kongmeng_options[index]
        if click_func():
            print(f"\n 点击{description}")
            kongmeng_count += 1
            # 更新keyin_data并写入文件
            keyin_data["kongmeng_count"] = kongmeng_count
            write_keyin_detail(keyin_data)
            print(f"kongmeng_count: {kongmeng_count}")
            ck.keyboard_i_press_release()
            return
    
    # 第二次尝试：把所有可以选择的options都试一次
    print("\n第二次尝试：把所有可以选择的options都试一次")
    for click_func, description, _ in kongmeng_options:
        if click_func():
            print(f"\n 点击{description}")
            kongmeng_count += 1
            # 更新keyin_data并写入文件
            keyin_data["kongmeng_count"] = kongmeng_count
            write_keyin_detail(keyin_data)
            print(f"kongmeng_count: {kongmeng_count}")
            ck.keyboard_i_press_release()
            return
        


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
        print("BH3窗口聚焦失败！")
