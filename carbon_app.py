from __future__ import annotations
import os
from datetime import date
from typing import Dict
import streamlit as st
from supabase import create_client, Client
import pandas as pd

# ==========================================
# 1. 排放係數設定 (移除衣，新增一次性用品)
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
# 2. 功能函式 (計算、衝擊指標、評分)
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

def _calc_impact_metrics(total_kg):
    total_tons = total_kg / 1000
    # 放大 1000 萬人的倍率
    scale = 10_000_000
    total_scale_kg = total_kg * scale
    total_scale_tons = total_scale_kg / 1000

    return {
        "glacier": total_scale_tons * 3,                # 冰川消融
        "temp": total_scale_kg * 1.5e-12,              # 升溫壓力
        "tree_days": (total_scale_kg / 22),            # 需多少棵樹吸收一年
        "sea_acid": total_scale_kg * 0.05,             # 海洋酸化體積
        "social_cost": total_scale_tons * 6500,        # 未來社會成本
        "ac_hours": total_scale_kg * 1.2               # 生活電力耗用當量
    }

def _write_supabase(date_str, user_name, food, disposable, home, transport, total):
    try:
        supabase = get_supabase()
        supabase.table("carbon_records").insert({
            "user_name": user_name, "date": date_str,
            "food": food, "clothes": disposable, 
            "home": home, "transport": transport, "total": total,
        }).execute()
        st.success(f"數據已同步至雲端")
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

# --- 輸入區塊 ---
c1, c2 = st.columns(2)
with c1:
    st.subheader("食（kg）")
    f_in = {n: st.number_input(n, min_value=0.0, key=f"f_{n}") for n in EF_FOOD.keys()}
with c2:
    st.subheader("一次性用品（個）")
    d_in = {n: st.number_input(n, min_value=0.0, key=f"d_{n}") for n in EF_DISPOSABLE.keys()}

c3, c4 = st.columns(2)
with c3:
    st.subheader("住（小時/次）")
    power_list = {k: v for k, v in EF_LIVE.items() if "瓦斯" not in k}
    gas_list   = {k: v for k, v in EF_LIVE.items() if "瓦斯" in k}
    p_in = {n: st.number_input(n, min_value=0.0, key=f"p_{n}") for n in power_list.keys()}
    g_in = {n: st.number_input(n, min_value=0.0, key=f"g_{n}") for n in gas_list.keys()}
with c4:
    st.subheader("行（公里）")
    t_in = {n: st.number_input(n, min_value=0.0, key=f"t_{n}") for n in EF_TRAFFIC.keys()}

# ==========================================
# 4. 計算與環境生態工程 (1000萬人模擬版)
# ==========================================
if st.button("計算並儲存"):
    f_total = _calc(EF_FOOD, f_in)
    d_total = _calc(EF_DISPOSABLE, d_in)
    h_total = round(_calc(power_list, p_in, use_power=True) + _calc(gas_list, g_in, use_gas=True), 2)
    t_total = _calc(EF_TRAFFIC, t_in)
    total   = round(f_total + d_total + h_total + t_total, 2)

    today_score = _get_score(total)
    st.divider()
    st.header(f"今日效率評分：{'⭐' * today_score}")
    st.markdown(f"### 今日個人總計：{total:.2f} kgCO2e")

    # --- 核心：6 大環境生態工程報告 (放大 1000 萬倍) ---
    st.header("🌎 環境生態工程：1000 萬人集體衝擊模擬")
    st.info("如果全台灣有一千萬人跟妳做一樣的事，一天的影響力將會是：")
    
    impacts = _calc_impact_metrics(total)
    
    r1_c1, r1_c2 = st.columns(2)
    with r1_c1:
        st.write("🧊 **冰川消融面積**")
        st.code(f"{impacts['glacier']:,.2f} m²", language='markdown')
    with r1_c2:
        st.write("🌡️ **升溫壓力貢獻**")
        st.code(f"{impacts['temp']:.10f} °C", language='markdown')

    r2_c1, r2_c2 = st.columns(2)
    with r2_c1:
        st.write("🌳 **全台所需吸收大樹**")
        st.code(f"{int(impacts['tree_days']):,} 棵", language='markdown')
        st.caption("需這麼多大樹吸收一年才能中和這一天的集體排碳")
    with r2_c2:
        st.write("🌊 **海洋酸化壓力體積**")
        st.code(f"{impacts['sea_acid']:,.2f} m³", language='markdown')

    r3_c1, r3_c2 = st.columns(2)
    with r3_c1:
        st.write("💰 **全球社會修復成本**")
        st.code(f"NT$ {impacts['social_cost']:,.0f}", language='markdown')
    with r3_c2:
        st.write("⚡ **生活電力耗用當量**")
        st.code(f"{impacts['ac_hours']:,.0f} 小時", language='markdown')
    
    _write_supabase(date_str, user_name, f_total, d_total, h_total, t_total, total)

# ==========================================
# 5. 歷史分析與長期評分
# ==========================================
st.divider()
st.header(f"📊 {user_name} 的趨勢分析")
try:
    supabase = get_supabase()
    res = supabase.table("carbon_records").select("*").eq("user_name", user_name).order("date", desc=False).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        df['date'] = pd.to_datetime(df['date'])
        st.line_chart(df.sort_values('date').set_index('date')[['total']])

        avg_val = df['total'].mean()
        long_score = _get_score(avg_val)
        c_m1, c_m2, c_m3 = st.columns(3)
        with c_m1: st.metric("歷史最高", f"{df['total'].max()} kg")
        with c_m2: st.metric("平均日排放", f"{round(avg_val, 2)} kg")
        with c_m3: st.metric("長期效率星級", "⭐" * long_score)
    else:
        st.info("尚無歷史數據。")
except Exception as e:
    st.error(f"讀取資料庫失敗")
