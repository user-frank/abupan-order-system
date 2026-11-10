import streamlit as st
import pandas as pd
import datetime

# ==========================================
# 👑 潘大廚 - 潘董戰情室 (總裁儀表板)
# ==========================================
def show():
    current_user = st.session_state.get("user_name", "潘哥")
    today = datetime.date.today()
    weekdays = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
    today_str = f"{today.strftime('%Y-%m-%d')} ({weekdays[today.weekday()]})"

    # 頂部控制列 (潘董歡迎詞 + 週期切換)
    col_t1, col_t2 = st.columns([3, 2])
    with col_t1:
        st.markdown(f"### 👑 潘大廚戰情室 ｜ 直營總部營運監控")
        st.caption(f"登入身份：{current_user}｜營運數據基準：{today_str}")
    with col_t2:
        period_option = st.segmented_control(
            "檢視週期", ["今日數據", "本週累計", "本月損益"], default="今日數據"
        ) if hasattr(st, "segmented_control") else st.radio("檢視週期", ["今日數據", "本週累計", "本月損益"], horizontal=True)

    st.markdown("<div style='margin-top: -10px;'></div>", unsafe_allow_html=True)
    st.divider()

    # ==========================================
    # 一、 頂部 4 大營運核心指標 (KPI 卡片)
    # ==========================================
    # 模擬/連動營運真實數據
    est_rev = 65000
    actual_rev = 68500
    rev_rate = (actual_rev / est_rev * 100) if est_rev > 0 else 0
    
    total_purchase = 22400  # 叫菜 + 叫貨支出
    food_cost_rate = (total_purchase / actual_rev * 100) if actual_rev > 0 else 0
    
    waste_loss_amount = 2450  # 報廢損失換算金額

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)

    with kpi1:
        with st.container(border=True):
            st.markdown("<p style='font-size:12px; color:#888; margin:0;'>💰 營業額達成率</p>", unsafe_allow_html=True)
            st.markdown(f"<h3 style='margin:4px 0; color:#FFF;'>NT$ {actual_rev:,}</h3>", unsafe_allow_html=True)
            color_rev = "#00C853" if rev_rate >= 100 else "#FF9800"
            st.markdown(f"<span style='font-size:12px; color:{color_rev}; font-weight:bold;'>達成率 {rev_rate:.1f}%</span> (目標 {est_rev:,})", unsafe_allow_html=True)

    with kpi2:
        with st.container(border=True):
            st.markdown("<p style='font-size:12px; color:#888; margin:0;'>🥗 食材成本率 (Food Cost)</p>", unsafe_allow_html=True)
            # 成本率超過 40% 自動轉紅燈
            is_cost_alert = food_cost_rate > 40.0
            color_cost = "#FF3B3B" if is_cost_alert else "#00C853"
            st.markdown(f"<h3 style='margin:4px 0; color:{color_cost};'>{food_cost_rate:.1f} %</h3>", unsafe_allow_html=True)
            badge_text = "🚨 偏高警示 (警戒線 40%)" if is_cost_alert else "🟢 健康標準區間 (30~38%)"
            st.markdown(f"<span style='font-size:11px; color:{color_cost}; font-weight:bold;'>{badge_text}</span>", unsafe_allow_html=True)

    with kpi3:
        with st.container(border=True):
            st.markdown("<p style='font-size:12px; color:#888; margin:0;'>⚠️ 耗損與報廢損失</p>", unsafe_allow_html=True)
            st.markdown(f"<h3 style='margin:4px 0; color:#FFD93D;'>NT$ {waste_loss_amount:,}</h3>", unsafe_allow_html=True)
            st.markdown("<span style='font-size:11px; color:#FF6B6B; font-weight:bold;'>損失佔營收 3.5%</span> (可控水位)", unsafe_allow_html=True)

    with kpi4:
        with st.container(border=True):
            st.markdown("<p style='font-size:12px; color:#888; margin:0;'>📋 今日採購總支出</p>", unsafe_allow_html=True)
            st.markdown(f"<h3 style='margin:4px 0; color:#FFF;'>NT$ {total_purchase:,}</h3>", unsafe_allow_html=True)
            st.markdown("<span style='font-size:11px; color:#A0A0A0;'>叫菜 4 筆 ｜ 叫貨 2 筆</span>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ==========================================
    # 二、 🚨 異常警示看板 (Exception Alert)
    # ==========================================
    st.markdown("#### 🚨 門市異常風控看板")
    
    # 假定有檢測到兩項異常 (若無異常則顯示綠色正常狀態)
    exceptions = [
        {"type": "採購暴增", "item": "高山高麗菜", "detail": "今日叫貨量 60 斤，超過近 7 天同星期平均 30% (同星期均值: 42 斤)", "level": "alert"},
        {"type": "報廢偏高", "item": "招牌秘製燒肉", "detail": "昨日單品報廢率達 14.2% (超過 10% 警戒線)，報廢損失金額 NT$ 1,280", "level": "warning"}
    ]

    if not exceptions:
        st.success("✅ 目前全店各項採購與報廢指標均在安全標準內，無異常狀況！")
    else:
        for ex in exceptions:
            border_color = "#FF3B3B" if ex["level"] == "alert" else "#FF9800"
            icon = "🚨" if ex["level"] == "alert" else "⚠️"
            st.markdown(f"""
            <div style='
                background-color: #1A1112; 
                border-left: 5px solid {border_color}; 
                border-top: 1px solid rgba(255,255,255,0.05);
                border-right: 1px solid rgba(255,255,255,0.05);
                border-bottom: 1px solid rgba(255,255,255,0.05);
                padding: 12px 16px; 
                border-radius: 4px; 
                margin-bottom: 10px;
            '>
                <div style='font-size: 14px; font-weight: bold; color: {border_color}; margin-bottom: 4px;'>
                    {icon} 【{ex['type']}警示】品項：{ex['item']}
                </div>
                <div style='font-size: 13px; color: #E0E0E0;'>
                    {ex['detail']}
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ==========================================
    # 三、 廠商採購支出分佈 (誰拿走最多貨款？)
    # ==========================================
    st.markdown("#### 🏢 供應商支出佔比排行 (掌握主要成本流向)")
    
    vendor_spending = [
        {"vendor": "萬豐蔬果行", "amount": 9800, "pct": 43.7, "cat": "生鮮青菜"},
        {"vendor": "大成長城肉品", "amount": 7600, "pct": 33.9, "cat": "核心肉品"},
        {"vendor": "益盛包材工業", "amount": 3200, "pct": 14.3, "cat": "便當外帶包材"},
        {"vendor": "金冠南北乾貨調味", "amount": 1800, "pct": 8.1, "cat": "米與醬料"}
    ]

    for v in vendor_spending:
        col_v_name, col_v_bar, col_v_amt = st.columns([3, 4, 2])
        with col_v_name:
            st.markdown(f"<p style='font-size:14px; font-weight:bold; margin:6px 0;'>{v['vendor']} <span style='font-size:11px; color:#888;'>({v['cat']})</span></p>", unsafe_allow_html=True)
        with col_v_bar:
            # 進度條直觀展示佔比
            st.progress(v['pct'] / 100)
        with col_v_amt:
            st.markdown(f"<p style='font-size:14px; font-weight:bold; color:#00C853; text-align:right; margin:6px 0;'>NT$ {v['amount']:,} <span style='font-size:12px; color:#888;'>({v['pct']}%)</span></p>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ==========================================
    # 四、 潘董專屬 AI 幕僚摘要 (30 秒掌握重點)
    # ==========================================
    with st.container(border=True):
        st.markdown("#### 💡 今日 AI 幕僚 30 秒總結診斷")
        st.markdown("""
        * 🟢 **營收表現**：今日預估營收達成率 **105.4%**，午市快餐客單表現強勁，現金流狀況健康。
        * ⚠️ **成本預警**：青菜類採購金額有上揚趨勢，其中「高山高麗菜」叫量較基準偏高，建議抽查廚房冷藏庫存避免積壓。
        * ☁️ **明日天氣動態**：明日台中北屯區預報**降雨機率 75%**（午後有雷陣雨），晚市外帶可能受影響，系統已自動建議前台調降晚班現場便當備料約 **12%**。
        """)

    st.caption("潘大廚餐飲集團 總裁決策管理後台 ｜ 機密商業數據")
