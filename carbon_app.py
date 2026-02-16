from __future__ import annotations
import os, csv
from datetime import datetime, date
from typing import Tuple, List, Dict

import streamlit as st
import pandas as pd
# 引入雲端連線套件
from streamlit_gsheets import GSheetsConnection

# ====== 1. 常數（完全保留你的原始數據） ======
EF_FOOD: Dict[str, float] = {
    "牛肉": 60.0, "羊肉": 24.0, "豬肉": 7.0, "雞肉": 6.0, "魚肉": 6.0,
    "牛奶": 3.0, "蛋": 4.5, "起司": 9.0, "植物奶": 1.2,
    "穀物": 2.0, "蔬菜": 2.2, "水果": 1.5, "豆腐": 2.0, "豆類": 1.8,
}
EF_TRAFFIC: Dict[str, float] = {
    "汽車": 0.21, "機車": 0.07, "公車": 0.08, "捷運": 0.05,
    "火車": 0.04, "高鐵": 0.03, "飛機": 0.15, "船": 0.25,
    "自行車": 0.0, "走路": 0.0,
}
EF_GRID = 0.52
EF_GAS = 2.0
EF_LIVE: Dict[str, float] = {
    "冷氣": 1.2, "電風扇": 0.05, "電燈": 0.01, "電視": 0.10, "電腦": 0.15, "手機充電": 0.015, "洗衣": 0.5,
    "烘衣": 1.2, "煮飯_電": 0.4, "暖氣_電": 2.0, "洗澡_瓦斯": 0.2, "煮飯_瓦斯": 0.2,
}
EF_CLOTHES: Dict[str, float] = {
    "T恤": 6.5, "牛仔褲": 33.0, "外套": 20.0, "襪子": 1.0, "鞋子": 14.0, "二手衣": 1.0, "修補再用": 0.5,
}
SUGGESTIONS: Dict[str, str] = {
    "牛肉": "把紅肉改成豆類/豆腐/雞肉或減量。", "羊肉": "改選白肉或植物性蛋白，或調整份量。",
    "豬肉": "以雞肉/豆類取代部分餐次，增加蔬菜比例。", "雞肉": "嘗試部分改為豆製品或菇類，降低動物性比例。",
    "魚肉": "選擇在地當季、減少遠洋魚種，或以豆類替代。", "牛奶": "以植物奶或減糖優先；視情況改小包裝。",
    "蛋": "避免浪費，掌握份量；搭配植物性蛋白。", "起司": "份量控制，改選風味重但用量少的起司。",
    "植物奶": "留意無糖款，減少加工糖帶來的額外足跡。", "穀物": "多選糙米、燕麥等全穀，兼顧健康與環境。",
    "蔬菜": "優先在地當季，減少高冷運輸菜。", "水果": "在地當季為主，避免長途空運品。",
    "豆腐": "很好！可嘗試更多豆製品料理。", "豆類": "很好！可當主要蛋白來源之一。",
    "冷氣": "溫度設 26-28°C、電扇輔助、門窗熱橋改善與定期清洗濾網。", "電風扇": "善用循環扇搭配冷氣可調高1-2°C。",
    "電燈": "全面改 LED，關燈隨手做。", "電視": "待機拔插頭或用延長線總開關。", "電腦": "開啟省電模式與休眠；降低螢幕亮度。",
    "手機充電": "集中充電避免過度插充；使用共用插座。", "洗衣": "滿桶清洗、低溫節能行程；與家人合併洗。",
    "烘衣": "能晾就晾；若需烘衣，選熱泵式與低溫長時程。", "煮飯_電": "計畫化烹調，一次煮足分裝冷藏。",
    "暖氣_電": "改善保溫（門窗縫/窗簾/地墊），降低暖氣時數。", "洗澡_瓦斯": "縮短淋浴時間、裝節流蓮蓬頭。",
    "煮飯_瓦斯": "鍋具加蓋、火焰不外溢、用小火慢煮。",
    "汽車": "合併行程、共乘或改大眾運輸。", "機車": "定期保養、短程可步行/自行車。",
    "公車": "感謝選擇大眾運輸，離峰搭乘更舒適。", "捷運": "已是低碳選擇，持續加油！",
    "火車": "長途優先選擇，取代自駕與飛機。", "高鐵": "城際移動首選之一，可搭配接駁大眾運輸。",
    "飛機": "能不飛就不飛；必要時直飛、減少托運重量。", "船": "必要才搭乘；若可，改陸路鐵道。",
    "自行車": "持續以零碳交通移動。", "走路": "也兼顧健康。",
    "T恤": "選耐穿材質。", "牛仔褲": "延長壽命。", "外套": "購買耐用經典款。", "襪子": "集中清洗避免遺失。",
    "鞋子": "保養與修鞋延壽。", "二手衣": "用平台／交換社群循環利用。", "修補再用": "學習基本修補術延長壽命。",
}

# --- 初始化雲端資料庫連線 ---
conn = st.connection("gsheets", type=GSheetsConnection)

# ====== 2. 工具函式（保留原邏輯） ======
def _calc(items: Dict[str, float], inputs: Dict[str, float], use_power=False, use_gas=False) -> Tuple[float, List[Tuple[str, float]]]:
    subtotal = 0.0
    used: List[Tuple[str, float]] = []
    for name, factor in items.items():
        qty = float(inputs.get(name, 0.0) or 0.0)
        if qty > 0:
            used.append((name, qty))
        val = qty * factor
        if use_power:
            val *= EF_GRID
        if use_gas:
            val *= EF_GAS
        subtotal += val
    return round(subtotal, 2), used

def _write_cloud_log(date_str, food, clothes, home, transport, total):
    """將資料同步至 Google Sheets 後台"""
    try:
        df = conn.read(ttl=0)
    except:
        df = pd.DataFrame(columns=["date", "food", "clothes", "home", "transport", "total"])
    
    new_data = pd.DataFrame([[date_str, food, clothes, home, transport, total]], 
                            columns=["date", "food", "clothes", "home", "transport", "total"])
    updated_df = pd.concat([df, new_data], ignore_index=True)
    conn.update(data=updated_df)

def _suggest(used: List[Tuple[str, float]]) -> List[str]:
    tips = []
    for name, _q in used:
        if name in SUGGESTIONS:
            tips.append(f"- {name}: {SUGGESTIONS[name]}")
    return tips

# ====== 3. 介面與輸入（保留原設計） ======
st.set_page_config(page_title="一日碳排計算（食／衣／住／行）", layout="wide")
st.title("一日碳排計算（食／衣／住／行）")

with st.sidebar:
    st.header("設定")
    d: date = st.date_input("日期", value=date.today())
    date_str = d.strftime("%Y-%m-%d")
    st.markdown("---")
    admin_pw = st.text_input("管理員後台密碼", type="password")

# --- 食 ---
st.subheader("食（kg）")
cols = st.columns(4)
food_inputs: Dict[str, float] = {}
for i, name in enumerate(EF_FOOD.keys()):
    with cols[i % 4]:
        food_inputs[name] = st.number_input(name, min_value=0.0, key=f"food_{name}")

# --- 衣 ---
st.subheader("衣（件/次）")
cols = st.columns(4)
clothes_inputs: Dict[str, float] = {}
for i, name in enumerate(EF_CLOTHES.keys()):
    with cols[i % 4]:
        clothes_inputs[name] = st.number_input(name, min_value=0.0, key=f"clothes_{name}")

# --- 住 ---
st.subheader("住（小時/次）")
power_list = {k: v for k, v in EF_LIVE.items() if "瓦斯" not in k}
gas_list = {k: v for k, v in EF_LIVE.items() if "瓦斯" in k}

cols = st.columns(4)
power_inputs: Dict[str, float] = {}
for i, name in enumerate(power_list.keys()):
    with cols[i % 4]:
        power_inputs[name] = st.number_input(name, min_value=0.0, key=f"power_{name}")

gas_inputs: Dict[str, float] = {}
for i, name in enumerate(gas_list.keys()):
    with cols[i % 4]:
        gas_inputs[name] = st.number_input(name, min_value=0.0, key=f"gas_{name}")

# --- 行 ---
st.subheader("行（公里）")
cols = st.columns(4)
traffic_inputs: Dict[str, float] = {}
for i, name in enumerate(EF_TRAFFIC.keys()):
    with cols[i % 4]:
        traffic_inputs[name] = st.number_input(name, min_value=0.0, key=f"traffic_{name}")

# ====== 4. 計算與結果輸出 ======
if st.button("計算並儲存"):
    food_total, food_used = _calc(EF_FOOD, food_inputs)
    clothes_total, clothes_used = _calc(EF_CLOTHES, clothes_inputs)
    power_total, power_used = _calc(power_list, power_inputs, use_power=True)
    gas_total, gas_used = _calc(gas_list, gas_inputs, use_gas=True)
    home_total = power_total + gas_total
    home_used = power_used + gas_used
    traffic_total, traffic_used = _calc(EF_TRAFFIC, traffic_inputs)

    total = round(food_total + clothes_total + home_total + traffic_total, 2)

    st.subheader("結果 (kgCO2e)")
    st.write(f"食：{food_total:.2f} | 衣：{clothes_total:.2f} | 住：{home_total:.2f} | 行：{traffic_total:.2f}")
    st.markdown(f"### **合計：{total:.2f}**")

    # 顯示建議
    for title, used in [("食", food_used), ("衣", clothes_used), ("住", home_used), ("行", traffic_used)]:
        tips = _suggest(used)
        if tips:
            with st.expander(f"{title} 改善建議"):
                for tip in tips: st.write(tip)

    # 寫入雲端
    _write_cloud_log(date_str, food_total, clothes_total, home_total, traffic_total, total)
    st.success("紀錄已存入雲端後台！")

# ====== 5. 管理員後台顯示 ======
if admin_pw == "你的秘密密碼": # 這裡改成你自己想設的密碼
    st.divider()
    st.header("🛡️ 管理員匿名後台 (所有使用者紀錄)")
    try:
        all_data = conn.read(ttl=0)
        st.dataframe(all_data, use_container_width=True)
        st.download_button("下載備份 CSV", all_data.to_csv(index=False), "backup.csv")
    except:
        st.info("目前雲端尚無紀錄。")