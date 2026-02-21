from __future__ import annotations
import os
from datetime import date
from typing import Dict
import streamlit as st
from supabase import create_client, Client
import pandas as pd

# ==========================================
# 1. 排放係數設定 (保留你原本的所有數據)
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

# ==========================================
# 2. 功能函式 (保留原本邏輯)
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

def _write_supabase(date_str, user_name, food, clothes, home, transport, total):
    try:
        supabase = get_supabase()
        supabase.table("carbon_records").insert({
            "user_name": user_name, 
            "date":      date_str,
            "food":      food,
            "clothes":   clothes,
            "home":      home,
            "transport": transport,
            "total":     total,
        }).execute()
        st.success(f"✅ {user_name} 的紀錄已存入雲端！")
    except Exception as e:
        st.error(f"❌ 儲存失敗：{e}")

# ==========================================
# 3. 介面呈現 (保留原本佈局)
# ==========================================
st.set_page_config(page_title="一日碳排計算 ", layout="wide")
st.title(" 個人碳排計算機")
st.subheader("Kevin is a handsome boy, and he's very talented")
st.info(" 請輸入您的代號開始使用。")

user_name = st.text_input(" 請輸入您的姓名或代號 )", placeholder="例如：凱鈜很帥 或 手機號碼")

if not user_name:
    st.warning("👈 請先輸入姓名/代號，要不你沒有空間使用喇。")
    st.stop()

with st.sidebar:
    d = st.date_input("日期", value=date.today())
    date_str = d.strftime("%Y-%m-%d")
    admin_pw = st.text_input("管理員後台密碼", type="password")

st.write(f"###  您好嗎 {user_name}，請填寫今日數據：")

# 食
st.subheader("食（kg）")
cols = st.columns(4)
food_inputs = {}
for i, name in enumerate(EF_FOOD.keys()):
    with cols[i % 4]: food_inputs[name] = st.number_input(name, min_value=0.0, key=f"food_{name}")

# 衣
st.subheader("衣（件/次）")
cols = st.columns(4)
clothes_inputs = {}
for i, name in enumerate(EF_CLOTHES.keys()):
    with cols[i % 4]: clothes_inputs[name] = st.number_input(name, min_value=0.0, key=f"clothes_{name}")

# 住
st.subheader("住（小時/次）")
power_list = {k: v for k, v in EF_LIVE.items() if "瓦斯" not in k}
gas_list   = {k: v for k, v in EF_LIVE.items() if "瓦斯" in k}
cols = st.columns(4)
power_inputs = {}
for i, name in enumerate(power_list.keys()):
    with cols[i % 4]: power_inputs[name] = st.number_input(name, min_value=0.0, key=f"power_{name}")
gas_inputs = {}
for i, name in enumerate(gas_list.keys()):
    with cols[i % 4]: gas_inputs[name] = st.number_input(name, min_value=0.0, key=f"gas_{name}")

# 行
st.subheader("行（公里）")
cols = st.columns(4)
traffic_inputs = {}
for i, name in enumerate(EF_TRAFFIC.keys()):
    with cols[i % 4]: traffic_inputs[name] = st.number_input(name, min_value=0.0, key=f"traffic_{name}")

# ==========================================
# 4. 計算、儲存與【環境衝擊報告】
# ==========================================
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

    # 原本的結算顯示
    st.subheader("📊 計算結果 (kgCO2e)")
    st.write(f"食：{food_total:.2f} | 衣：{clothes_total:.2f} | 住：{home_total:.2f} | 行：{traffic_total:.2f}")
    st.markdown(f"### **合計：{total:.2f}**")

    # --- 新增：環境生態工程報告區 (指標 1: 冰川) ---
    st.divider()
    st.header("🧊 環境衝擊報告：冰川消融指標")
    
    # 科學計算：1 噸 = 3 平方公尺冰川
    glacier_area = (total / 1000) * 3
    # 單位轉換：一張瑜珈墊約 1.08 平方公尺 (1.8m * 0.6m)
    yoga_mats = glacier_area / 1.08
    
    rep_col1, rep_col2 = st.columns([1, 3])
    with rep_col1:
        st.title("❄️")
    with rep_col2:
        st.write(f"您的今日碳排將導致 **{glacier_area:.6f}** $m^2$ 的北極冰川消失。")
        st.info(f"這大約是 **{yoga_mats:.2f}** 張瑜珈墊的面積。保護環境，刻不容緩！")
    # --------------------------------------------

    _write_supabase(date_str, user_name, food_total, clothes_total, home_total, traffic_total, total)
    st.session_state.submitted = False

# ==========================================
# 5. 歷史紀錄與管理後台 (保留原本邏輯)
# ==========================================
st.divider()
st.header(f" {user_name} 的歷史紀錄")
try:
    supabase = get_supabase()
    response = supabase.table("carbon_records").select("*").eq("user_name", user_name).order("date", desc=True).execute()
    if response.data:
        df = pd.DataFrame(response.data)
        st.dataframe(df, use_container_width=True)
    else:
        st.write("還沒有您的紀錄，快點開始！")
except Exception as e:
    st.error(f"讀取失敗哈：{e}")

if admin_pw and admin_pw == st.secrets.get("admin", {}).get("password", ""):
    st.divider()
    st.header("🛡️ 管理員總後台 (顯示所有人)")
    try:
        all_res = supabase.table("carbon_records").select("*").order("date", desc=True).execute()
        df_all = pd.DataFrame(all_res.data)
        st.dataframe(df_all, use_container_width=True)
    except Exception as e:
        st.error(f"後台讀取失敗：{e}")
