from __future__ import annotations
import os, csv
from datetime import datetime, date
from typing import Tuple, List, Dict

import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# ====== 1. 常數 ======
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
    "冷氣": 1.2, "電風扇": 0.05, "電燈": 0.01, "電視": 0.10,
    "電腦": 0.15, "手機充電": 0.015, "洗衣": 0.5,
    "烘衣": 1.2, "煮飯_電": 0.4, "暖氣_電": 2.0,
    "洗澡_瓦斯": 0.2, "煮飯_瓦斯": 0.2,
}

EF_CLOTHES: Dict[str, float] = {
    "T恤": 6.5, "牛仔褲": 33.0, "外套": 20.0,
    "襪子": 1.0, "鞋子": 14.0,
    "二手衣": 1.0, "修補再用": 0.5,
}

# --- 初始化雲端連線 ---
conn = st.connection("gsheets", type=GSheetsConnection)

# ====== 2. 計算函式 ======
def _calc(items, inputs, use_power=False, use_gas=False):
    subtotal = 0.0
    used = []
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


# ====== 3. 雲端寫入（🔥 改成 append 版） ======
def _write_cloud_log(date_str, food, clothes, home, transport, total):
    new_data = pd.DataFrame(
        [[date_str, food, clothes, home, transport, total]],
        columns=["date", "food", "clothes", "home", "transport", "total"]
    )

    try:
        conn.append(data=new_data, append=True)
        st.success("紀錄已存入雲端後台！")
    except Exception:
        st.error("Google 目前忙碌中，請稍後再試。")


# ====== 4. 介面 ======
st.set_page_config(page_title="一日碳排計算（食／衣／住／行）", layout="wide")
st.title("一日碳排計算（食／衣／住／行）")

with st.sidebar:
    d = st.date_input("日期", value=date.today())
    date_str = d.strftime("%Y-%m-%d")
    admin_pw = st.text_input("管理員後台密碼", type="password")

# --- 食 ---
st.subheader("食（kg）")
cols = st.columns(4)
food_inputs = {}
for i, name in enumerate(EF_FOOD.keys()):
    with cols[i % 4]:
        food_inputs[name] = st.number_input(name, min_value=0.0, key=f"food_{name}")

# --- 衣 ---
st.subheader("衣（件/次）")
cols = st.columns(4)
clothes_inputs = {}
for i, name in enumerate(EF_CLOTHES.keys()):
    with cols[i % 4]:
        clothes_inputs[name] = st.number_input(name, min_value=0.0, key=f"clothes_{name}")

# --- 住 ---
st.subheader("住（小時/次）")
power_list = {k: v for k, v in EF_LIVE.items() if "瓦斯" not in k}
gas_list = {k: v for k, v in EF_LIVE.items() if "瓦斯" in k}

cols = st.columns(4)
power_inputs = {}
for i, name in enumerate(power_list.keys()):
    with cols[i % 4]:
        power_inputs[name] = st.number_input(name, min_value=0.0, key=f"power_{name}")

gas_inputs = {}
for i, name in enumerate(gas_list.keys()):
    with cols[i % 4]:
        gas_inputs[name] = st.number_input(name, min_value=0.0, key=f"gas_{name}")

# --- 行 ---
st.subheader("行（公里）")
cols = st.columns(4)
traffic_inputs = {}
for i, name in enumerate(EF_TRAFFIC.keys()):
    with cols[i % 4]:
        traffic_inputs[name] = st.number_input(name, min_value=0.0, key=f"traffic_{name}")

# ====== 5. 防連按鎖 ======
if "submitted" not in st.session_state:
    st.session_state.submitted = False

if st.button("計算並儲存") and not st.session_state.submitted:

    st.session_state.submitted = True

    food_total, _ = _calc(EF_FOOD, food_inputs)
    clothes_total, _ = _calc(EF_CLOTHES, clothes_inputs)
    power_total, _ = _calc(power_list, power_inputs, use_power=True)
    gas_total, _ = _calc(gas_list, gas_inputs, use_gas=True)
    home_total = power_total + gas_total
    traffic_total, _ = _calc(EF_TRAFFIC, traffic_inputs)

    total = round(food_total + clothes_total + home_total + traffic_total, 2)

    st.subheader("結果 (kgCO2e)")
    st.write(f"食：{food_total:.2f} | 衣：{clothes_total:.2f} | 住：{home_total:.2f} | 行：{traffic_total:.2f}")
    st.markdown(f"### **合計：{total:.2f}**")

    _write_cloud_log(date_str, food_total, clothes_total, home_total, traffic_total, total)

    st.session_state.submitted = False


# ====== 6. 管理員後台 ======
if admin_pw == "你的秘密密碼":
    st.divider()
    st.header("🛡️ 管理員匿名後台")

    try:
        all_data = conn.read()
        st.dataframe(all_data, use_container_width=True)
        st.download_button("下載備份 CSV", all_data.to_csv(index=False), "backup.csv")
    except:
        st.info("目前雲端尚無紀錄。")
