from __future__ import annotations
import os
from datetime import date
from typing import Dict
import streamlit as st
from supabase import create_client, Client
import pandas as pd

# ==========================================
# 1. CSS 美化：設定綠色背景與元件樣式
# ==========================================
st.set_page_config(page_title="生活效率計算", layout="wide")

st.markdown("""
    <style>
    /* 全域背景變為淡綠色 */
    .stApp {
        background-color: #F1F8E9;
    }
    /* 標籤頁樣式優化 */
    .stTabs [data-baseweb="tab-list"] { 
        gap: 10px; 
    }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        background-color: #DCEDC8;
        border-radius: 5px 5px 0px 0px;
        color: #33691E;
        padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] { 
        background-color: #558B2F !important; 
        color: white !important; 
    }
    /* 按鈕樣式 */
    .stButton>button {
        background-color: #558B2F;
        color: white;
        border-radius: 10px;
        border: none;
    }
    .stButton>button:hover {
        background-color: #33691E;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. 排放係數設定
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
EF_GRID, EF_GAS = 0.52, 2.0
EF_LIVE: Dict[str, float] = {
    "冷氣": 1.2, "電風扇": 0.05, "電燈": 0.01, "電視": 0.10,
    "電腦": 0.15, "手機充電": 0.015, "洗衣": 0.5,
    "烘衣": 1.2, "煮飯_電": 0.4, "暖氣_電": 2.0,
    "洗澡_瓦斯": 0.2, "煮飯_瓦斯": 0.2,
}

# ==========================================
# 3. 功能函式
# ==========================================
@st.cache_resource
def get_supabase() -> Client:
    return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])

def _calc(items, inputs, use_power=False, use_gas=False):
    subtotal = sum(float(inputs.get(n, 0) or 0) * f * (EF_GRID if use_power else 1) * (EF_GAS if use_gas else 1) for n, f in items.items())
    return round(subtotal, 2)

def _get_score(total_val):
    if total_val <= 5: return 5
    elif total_val <= 13: return 4
    elif total_val <= 24: return 3
    elif total_val <= 42: return 2
    else: return 1

# ==========================================
# 4. 網頁架構與分頁
# ==========================================
st.title(" 生活效率碳排計算機")
st.caption("Kevin is a handsome boy, and he's very talented")

user_name = st.text_input("👤 請輸入姓名或代號")
if not user_name:
    st.warning(" 請先輸入姓名以開啟系統。")
    st.stop()

with st.sidebar:
    d = st.date_input("📅 選擇日期", value=date.today())
    date_str = d.strftime("%Y-%m-%d")

tab1, tab2, tab3 = st.tabs(["🚀 今日計算", "🌎 影響力模擬", "📈 趨勢分析"])

# --- TAB 1: 今日計算 ---
with tab1:
    st.write(f"### {user_name}，填寫今日數據")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader(" 食（kg）")
        f_in = {n: st.number_input(n, min_value=0.0, key=f"f_{n}") for n in EF_FOOD.keys()}
    with c2:
        st.subheader(" 一次性用品（個）")
        d_in = {n: st.number_input(n, min_value=0.0, key=f"d_{n}") for n in EF_DISPOSABLE.keys()}

    c3, c4 = st.columns(2)
    with c3:
        st.subheader(" 住（小時/次）")
        p_list = {k: v for k, v in EF_LIVE.items() if "瓦斯" not in k}
        g_list = {k: v for k, v in EF_LIVE.items() if "瓦斯" in k}
        p_in = {n: st.number_input(n, min_value=0.0, key=f"p_{n}") for n in p_list.keys()}
        g_in = {n: st.number_input(n, min_value=0.0, key=f"g_{n}") for n in g_list.keys()}
    with c4:
        st.subheader("行（公里）")
        t_in = {n: st.number_input(n, min_value=0.0, key=f"t_{n}") for n in EF_TRAFFIC.keys()}

    if st.button("🚀 計算並儲存數據"):
        f_total = _calc(EF_FOOD, f_in)
        d_total = _calc(EF_DISPOSABLE, d_in)
        h_total = round(_calc(p_list, p_in, True) + _calc(g_list, g_in, False, True), 2)
        t_total = _calc(EF_TRAFFIC, t_in)
        total   = round(f_total + d_total + h_total + t_total, 2)
        
        st.session_state['last_total'] = total
        try:
            get_supabase().table("carbon_records").insert({
                "user_name": user_name, "date": date_str, "food": f_total, 
                "clothes": d_total, "home": h_total, "transport": t_total, "total": total,
            }).execute()
            st.success("計算完成！請切換至『影響力模擬』標籤。")
        except Exception as e:
            st.error(f"儲存失敗：{e}")

# --- TAB 2: 影響力模擬 (含 6 大工程指標) ---
with tab2:
    if 'last_total' in st.session_state:
        total = st.session_state['last_total']
        scale = 10_000_000
        st.header(f"今日效率評分：{'⭐' * _get_score(total)}")
        st.subheader(f"💡 如果 1000 萬人跟妳做一樣的事...")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(" 冰川消融面積")
            st.code(f"{(total * scale / 1000 * 3):,.2f} m²")
            st.write(" 升溫壓力貢獻")
            st.code(f"{total * scale * 1.5e-12:.10f} °C")
            st.write(" 全台所需吸收大樹")
            st.code(f"{int(total * scale / 22):,} 棵")
        with col2:
            st.write(" 海洋酸化壓力體積")
            st.code(f"{total * scale * 0.05:,.2f} m³")
            st.write(" 全球社會修復成本")
            st.code(f"NT$ {int(total * scale / 1000 * 6500):,}")
            st.write(" 生活電力耗用當量")
            st.code(f"{total * scale * 1.2:,.0f} 小時")
    else:
        st.info("請先完成今日計算。")

# --- TAB 3: 趨勢分析 ---
with tab3:
    try:
        res = get_supabase().table("carbon_records").select("*").eq("user_name", user_name).order("date", desc=False).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df['date'] = pd.to_datetime(df['date'])
            st.line_chart(df.sort_values('date').set_index('date')[['total']])
            
            avg_v = df['total'].mean()
            m1, m2, m3 = st.columns(3)
            m1.metric("歷史最高", f"{df['total'].max()} kg")
            m2.metric("平均排放", f"{round(avg_v, 2)} kg")
            m3.metric("長期星級", "⭐" * _get_score(avg_v))
        else:
            st.info("尚無紀錄。")
    except:
        st.error("讀取失敗")
