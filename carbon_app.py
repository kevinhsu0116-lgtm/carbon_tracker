from __future__ import annotations
import os
from datetime import date
from typing import Dict

import streamlit as st
from supabase import create_client, Client

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

# ====== 2. 連線 Supabase ======
# 請在 Streamlit Cloud 的 Secrets 或 .streamlit/secrets.toml 裡設定：
#
# [supabase]
# url = "https://xxxxxxxxxxxx.supabase.co"
# key = "eyJ..."
#
@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

# ====== 3. 計算函式 ======
def _calc(items, inputs, use_power=False, use_gas=False):
    subtotal = 0.0
    for name, factor in items.items():
        qty = float(inputs.get(name, 0.0) or 0.0)
        val = qty * factor
        if use_power:
            val *= EF_GRID
        if use_gas:
            val *= EF_GAS
        subtotal += val
    return round(subtotal, 2)

# ====== 4. 寫入 Supabase ======
def _write_supabase(date_str, food, clothes, home, transport, total):
    try:
        supabase = get_supabase()
        supabase.table("carbon_records").insert({
            "date":      date_str,
            "food":      food,
            "clothes":   clothes,
            "home":      home,
            "transport": transport,
            "total":     total,
        }).execute()
        st.success("✅ 紀錄已存入雲端！")
    except Exception as e:
        st.error(f"❌ 儲存失敗：{e}")

# ====== 5. 介面 ======
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
gas_list   = {k: v for k, v in EF_LIVE.items() if "瓦斯" in k}

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

# ====== 6. 防連按鎖 ======
if "submitted" not in st.session_state:
    st.session_state.submitted = False

if st.button("計算並儲存") and not st.session_state.submitted:
    st.session_state.submitted = True

    food_total    = _calc(EF_FOOD, food_inputs)
    clothes_total = _calc(EF_CLOTHES, clothes_inputs)
    power_total   = _calc(power_list, power_inputs, use_power=True)
    gas_total     = _calc(gas_list, gas_inputs, use_gas=True)
    home_total    = round(power_total + gas_total, 2)
    traffic_total = _calc(EF_TRAFFIC, traffic_inputs)
    total         = round(food_total + clothes_total + home_total + traffic_total, 2)

    st.subheader("結果 (kgCO2e)")
    st.write(f"食：{food_total:.2f} | 衣：{clothes_total:.2f} | 住：{home_total:.2f} | 行：{traffic_total:.2f}")
    st.markdown(f"### **合計：{total:.2f}**")

    _write_supabase(date_str, food_total, clothes_total, home_total, traffic_total, total)

    st.session_state.submitted = False

# ====== 7. 管理員後台 ======
if admin_pw == st.secrets.get("admin", {}).get("password", ""):
    st.divider()
    st.header("🛡️ 管理員匿名後台")
    try:
        supabase = get_supabase()
        response = supabase.table("carbon_records").select("*").order("date", desc=True).execute()
        import pandas as pd
        df = pd.DataFrame(response.data)
        st.dataframe(df, use_container_width=True)
        st.download_button("下載備份 CSV", df.to_csv(index=False), "backup.csv")
    except Exception as e:
        st.error(f"讀取失敗：{e}")pi