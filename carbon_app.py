from __future__ import annotations
import os
from datetime import date
from typing import Dict
import streamlit as st
from supabase import create_client, Client
import pandas as pd

# ==========================================
# 1. 排放係數 (已換算為 kgCO2e)
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
# 2. 策略建議內容
# ==========================================
STRATEGY_DATA = {
    "food": {
        "title": "一. 針對間接排放:",
        "desc": "作法: 改變食物來源，降低食物背後的隱形排碳",
        "points": [
            "1. 低碳里程: 優先挑選在地食材，減少長途物流與冷鏈電力消耗。",
            "2. 低碳加工技術替代：常溫在地蔬菜比冷凍蔬菜更能省下巨大電力間接排放。",
            "3. 物流整合與去節點化：要求供應商採用大包裝，減少物流中心停留與二次包裝。",
            "4. 高生產效率選擇: 挑選採用智慧農場、再生水灌的供應商。"
        ],
        "perfect": "5. 100分"
    },
    "disposable": {
        "title": "二. 一次性用品(間接排放):",
        "desc": "作法: 減少物料消耗與優化廢棄物路徑",
        "points": [
            "1. 環保餐具: 隨身攜帶環保餐具與杯子，從源頭減少一次性用品。",
            "2. 丟對垃圾桶：確保可回收物進入循環路徑，將廢棄物轉化為再生資源。",
            "3. 可堆肥材質：針對無法回收的耗材，轉向「工業可堆肥」材質。",
            "4. 減少包裝: 選擇裸裝或簡約包裝商品，降低材料生產與處理排放。"
        ],
        "perfect": "5. 不錯嘛"
    },
    "energy": {
        "title": "三. 針對能源使用:",
        "desc": "作法: 轉向高能效設備與行為，提高每度電的效率。",
        "points": [
            "1. 高能效比：升級為一級能效設備，可減少 30%-50% 的電力間接排放。",
            "2. 能源轉型: 支持政府加速低碳能源配比。當國家電網係數下降，你的排碳也會降低。",
            "3. 行為優化：消除電器待機功耗，透過自動排程在非使用時段切斷電源。",
            "4. 支持環保: 優先選擇綠電店家，將消費轉向綠電與環保投資。"
        ],
        "perfect": "5. 讚"
    },
    "transport": {
        "title": "四. 針對直接排放運輸:",
        "desc": "作法: 優化移動效率，減油又減碳",
        "points": [
            "1. 搭大眾運輸: 透過多人載運平分碳排，減少個人移動排放量。",
            "2. 輕量化：移除車上長期堆積物品。每減少45公斤負載，油耗約可降低 1%-2%。",
            "3. 定期保養載具: 確保載具處於低阻力狀態，維持引擎最高效率。",
            "4. 智慧路徑規劃: 避開塞車。穩定時速就是能量轉換率最高的移動方式。"
        ],
        "perfect": "5. 好棒"
    }
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

def _get_total_stars(total_val):
    if total_val <= 5: return 5
    elif total_val <= 13: return 4
    elif total_val <= 24: return 3
    elif total_val <= 42: return 2
    else: return 1

def _get_item_stars(val, low, mid):
    if val <= low: return 5
    elif val <= mid: return 3
    else: return 1

# ==========================================
# 4. 網頁佈局
# ==========================================
st.set_page_config(page_title="生活碳排計算機", layout="wide")
st.title("🌱 生活碳排計算機")

user_name = st.text_input("請輸入代號")
if not user_name:
    st.info("請輸入代號以開啟功能。")
    st.stop()

with st.sidebar:
    d = st.date_input("選擇日期", value=date.today())
    date_str = d.strftime("%Y-%m-%d")

tab1, tab2, tab3 = st.tabs(["今日計算", "策略報告", "趨勢分析"])

# --- TAB 1: 今日計算 ---
with tab1:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🍱 食（kg）")
        f_in = {n: st.number_input(n, min_value=0.0, key=f"f_{n}") for n in EF_FOOD.keys()}
        st.subheader("♻️ 一次性用品（個）")
        d_in = {n: st.number_input(n, min_value=0.0, key=f"d_{n}") for n in EF_DISPOSABLE.keys()}
    with c2:
        st.subheader("🏠 住（小時）")
        p_list = {k: v for k, v in EF_LIVE.items() if "瓦斯" not in k}
        p_in = {n: st.number_input(n, min_value=0.0, key=f"p_{n}") for n in p_list.keys()}
        st.subheader("🚲 行（公里）")
        t_in = {n: st.number_input(n, min_value=0.0, key=f"t_{n}") for n in EF_TRAFFIC.keys()}

    if st.button("計算並儲存"):
        f_t, d_t = _calc(EF_FOOD, f_in), _calc(EF_DISPOSABLE, d_in)
        h_t, t_t = _calc(p_list, p_in, True), _calc(EF_TRAFFIC, t_in)
        total = round(f_t + d_t + h_t + t_t, 2)
        st.session_state['res'] = {"food": f_t, "disp": d_t, "home": h_t, "move": t_t, "total": total}
        try:
            get_supabase().table("carbon_records").insert({
                "user_name": user_name, "date": date_str, "food": f_t, 
                "clothes": d_t, "home": h_t, "transport": t_t, "total": total,
            }).execute()
            st.success("計算成功！請切換至『策略報告』查看。")
        except: st.error("儲存失敗")

# --- TAB 2: 策略報告 ---
with tab2:
    if 'res' in st.session_state:
        r = st.session_state['res']
        st.header("📊 今日碳盤查數據摘要 (單位: kgCO2e)")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("🍱 食", f"{r['food']} kg")
        m2.metric("♻️ 用品", f"{r['disp']} kg")
        m3.metric("🏠 住", f"{r['home']} kg")
        m4.metric("🚲 行", f"{r['move']} kg")
        m5.metric("🌟 總計", f"{r['total']} kg")
        
        total_stars = _get_total_stars(r['total'])
        st.subheader(f"今日效率總評：{'⭐' * total_stars}")

        scale = 10_000_000
        st.subheader("🌎 如果 1000 萬人跟妳做一樣的事...")
        ic1, ic2, ic3 = st.columns(3)
        ic1.metric("冰川消融", f"{(r['total'] * scale / 1000 * 3):,.0f} m²")
        ic2.metric("所需大樹", f"{int(r['total'] * scale / 22):,} 棵")
        ic3.metric("社會成本", f"NT$ {int(r['total'] * scale / 1000 * 6500):,}")
        st.divider()

        item_scores = {
            "food": _get_item_stars(r['food'], 5, 15),
            "disposable": _get_item_stars(r['disp'], 0.5, 2),
            "energy": _get_item_stars(r['home'], 3, 10),
            "transport": _get_item_stars(r['move'], 1, 5)
        }

        for key, stars in item_scores.items():
            data = STRATEGY_DATA[key]
            st.subheader(f"{data['title']} ({'⭐' * stars})")
            if stars == 5: st.success(data['perfect'])
            else:
                show_count = 5 - stars
                for i in range(min(show_count, 4)): st.write(data['points'][i])
            st.divider()
    else: st.info("請先完成計算。")

# --- TAB 3: 趨勢分析 (已整合每日明細表格與各項佔比圖) ---
with tab3:
    try:
        res = get_supabase().table("carbon_records").select("*").eq("user_name", user_name).order("date", desc=False).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df_renamed = df.rename(columns={
                "date": "日期", "food": "飲食 (kgCO2e)", "clothes": "用品 (kgCO2e)", 
                "home": "能源 (kgCO2e)", "transport": "交通 (kgCO2e)", "total": "今日總排放 (kgCO2e)"
            })
            
            st.subheader("📅 碳排放趨勢分析")
            st.line_chart(df_renamed.set_index('日期')[['今日總排放 (kgCO2e)']])
            
            st.subheader("📊 排放熱點組成分析")
            st.area_chart(df_renamed.set_index('日期')[["飲食 (kgCO2e)", "用品 (kgCO2e)", "能源 (kgCO2e)", "交通 (kgCO2e)"]])
            
            st.divider()
            st.subheader("📋 每日盤查紀錄明細表")
            st.dataframe(df_renamed.set_index("日期"), use_container_width=True)
            
            avg_v = df['total'].mean()
            st.metric("平均日排放", f"{round(avg_v, 2)} kgCO2e", delta=f"{round(avg_v - 19.6, 2)} vs 台灣平均", delta_color="inverse")
    except Exception as e: st.error(f"讀取失敗: {e}")
