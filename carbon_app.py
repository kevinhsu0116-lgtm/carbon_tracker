from __future__ import annotations
import os
from datetime import date
from typing import Dict
import streamlit as st
from supabase import create_client, Client
import pandas as pd

# ==========================================
# 1. 排放係數設定
# ==========================================
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
EF_DISPOSABLE: Dict[str, float] = {
    "塑膠袋": 0.05, "紙杯": 0.04, "塑膠吸管": 0.01,
    "免洗餐具": 0.03, "餐盒": 0.15, "寶特瓶": 0.08,
}
EF_GRID = 0.52
EF_GAS = 2.0
EF_LIVE: Dict[str, float] = {
    "冷氣": 1.2, "電風扇": 0.05, "電燈": 0.01, "電視": 0.10,
    "電腦": 0.15, "手機充電": 0.015, "洗衣": 0.5,
    "烘衣": 1.2, "煮飯_電": 0.4, "暖氣_電": 2.0,
    "洗澡_瓦斯": 0.2, "煮飯_瓦斯": 0.2,
}

# ==========================================
# 2. 功能函式
# ==========================================
@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

def _calc(items, inputs, use_power=False, use_gas=False):
    subtotal = 0.0
    for name, factor in items.items():
        qty = float(inputs.get(name, 0.0) or 0.0)
        val = qty * factor
        if use_power: val *= EF_GRID
        if use_gas: val *= EF_GAS
        subtotal += val
    return round(subtotal, 2)

def _get_score(total_val):
    if total_val <= 5: return 5
    elif total_val <= 13: return 4
    elif total_val <= 24: return 3
    elif total_val <= 42: return 2
    else: return 1

def _write_supabase(date_str, user_name, food, disposable, home, transport, total):
    try:
        supabase = get_supabase()
        supabase.table("carbon_records").insert({
            "user_name": user_name, 
            "date":      date_str,
            "food":      food,
            "clothes":   disposable,
            "home":      home,
            "transport": transport,
            "total":     total,
        }).execute()
        st.success(f"數據已同步")
    except Exception as e:
        st.error(f"儲存失敗：{e}")

# ==========================================
# 3. 介面呈現
# ==========================================
st.set_page_config(page_title="生活效率計算", layout="wide")
st.title("個人生活效率碳排計算機")
st.subheader("Kevin is a handsome boy, and he's very talented")

user_name = st.text_input("請輸入您的姓名或代號", placeholder="例如：凱鈜")

if not user_name:
    st.warning("請先輸入姓名以開啟空間。")
    st.stop()

with st.sidebar:
    d = st.date_input("日期", value=date.today())
    date_str = d.strftime("%Y-%m-%d")

st.write(f"### 您好 {user_name}")

c1, c2 = st.columns(2)
with c1:
    st.subheader("食（kg）")
    food_inputs = {n: st.number_input(n, min_value=0.0, key=f"f_{n}") for n in EF_FOOD.keys()}

with c2:
    st.subheader("一次性用品（個）")
    disposable_inputs = {n: st.number_input(n, min_value=0.0, key=f"d_{n}") for n in EF_DISPOSABLE.keys()}

c3, c4 = st.columns(2)
with c3:
    st.subheader("住（小時/次）")
    power_list = {k: v for k, v in EF_LIVE.items() if "瓦斯" not in k}
    gas_list   = {k: v for k, v in EF_LIVE.items() if "瓦斯" in k}
    p_in = {n: st.number_input(n, min_value=0.0, key=f"p_{n}") for n in power_list.keys()}
    g_in = {n: st.number_input(n, min_value=0.0, key=f"g_{n}") for n in gas_list.keys()}

with c4:
    st.subheader("行（公里）")
    traffic_inputs = {n: st.number_input(n, min_value=0.0, key=f"t_{n}") for n in EF_TRAFFIC.keys()}

# ==========================================
# 4. 計算與集體衝擊模擬
# ==========================================
if st.button("計算並儲存紀錄"):
    f_total = _calc(EF_FOOD, food_inputs)
    d_total = _calc(EF_DISPOSABLE, disposable_inputs)
    h_total = round(_calc(power_list, p_in, use_power=True) + _calc(gas_list, g_in, use_gas=True), 2)
    t_total = _calc(EF_TRAFFIC, traffic_inputs)
    total   = round(f_total + d_total + h_total + t_total, 2)

    today_score = _get_score(total)
    
    st.divider()
    st.header(f"今日效率評分：{'⭐' * today_score}")
    st.markdown(f"### 今日總計：{total:.2f} kgCO2e")

    # 1000萬人模擬邏輯
    st.subheader("💡 如果 1000 萬人跟妳做一樣的事...")
    
    # 換算數據：1kg * 10^7 = 1萬噸
    m_total_tons = (total * 10000000) / 1000
    
    ic1, ic2 = st.columns(2)
    with ic1:
        st.info(f"**單日總排量將達到**")
        st.title(f"{int(m_total_tons):,} 噸")
        st.caption("這相當於台灣單日總排放量的巨大佔比")
    
    with ic2:
        st.info(f"**全台生態需承擔**")
        # 以一棵樹每年吸收22kg計算
        trees_needed = (total * 10000000) / 22
        st.title(f"{int(trees_needed):,} 棵大樹")
        st.caption("需這麼多大樹同時吸收一年才能抵銷這一天的活動")

    _write_supabase(date_str, user_name, f_total, d_total, h_total, t_total, total)

# ==========================================
# 5. 歷史分析
# ==========================================
st.divider()
st.header(f"📊 {user_name} 的趨勢分析")

try:
    supabase = get_supabase()
    response = supabase.table("carbon_records").select("*").eq("user_name", user_name).order("date", desc=False).execute()
    
    if response.data:
        df = pd.DataFrame(response.data)
        df['date'] = pd.to_datetime(df['date'])
        st.line_chart(df.sort_values('date').set_index('date')[['total']])

        avg_val = df['total'].mean()
        long_score = _get_score(avg_val)
        star_str = "⭐" * long_score + "✨" * (5 - long_score)

        c_m1, c_m2, c_m3 = st.columns(3)
        with c_m1: st.metric("歷史最高", f"{df['total'].max()} kg")
        with c_m2: st.metric("平均日排放", f"{round(avg_val, 2)} kg")
        with c_m3: st.metric("長期效率星級", star_str)
    else:
        st.info("尚無歷史數據。")
except Exception as e:
    st.error(f"讀取失敗")
