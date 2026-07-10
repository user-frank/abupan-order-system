import streamlit as st
import pandas as pd
import datetime
from data_engine import load_sales_data
from record_engine import load_daily_record
from ai_engine import render_ai_assistant

def show():
    st.markdown("## 📊 總管理處 - 老闆戰情室")
    st.markdown("<p style='color: #888; font-size: 14px;'>全公司營運數據總覽與人員操作追蹤 </p>", unsafe_allow_html=True)
    
    df_sales, _ = load_sales_data()
    all_categories = df_sales['cat'].unique().tolist() if not df_sales.empty else ["生魚片", "壽司", "冰鮮", "活體"]
    
    # 🌟 建立最新價格字典 (Auto-Heal 準備，防止舊單價為0)
    price_map = {}
    if not df_sales.empty:
        df_sales['item_id'] = df_sales['item_id'].astype(str)
        price_map = dict(zip(df_sales['item_id'], pd.to_numeric(df_sales['price'], errors='coerce').fillna(0).astype(int)))
    
    col_date, col_dept = st.columns(2)
    with col_date:
        target_date = st.date_input("🗓️ 選擇檢視日期", value=datetime.date.today())
        date_str = target_date.strftime("%Y-%m-%d")
    with col_dept:
        dept_options = ["🏢 全公司總覽"] + all_categories
        selected_dept = st.selectbox("📌 選擇檢視部門", dept_options)
        
    st.divider()

    with st.spinner("載入戰情數據中..."):
        df_record = load_daily_record(date_str)

    # ==========================================
    # 💰 營業額戰情板 (真實計算邏輯)
    # ==========================================
    est_revenue = 0
    actual_revenue = 0
    achieve_rate = "0.0"
    
    if not df_record.empty:
        calc_df = df_record.copy()
        
        if selected_dept != "🏢 全公司總覽":
            calc_df = calc_df[calc_df['cat'] == selected_dept]
            
        for col in ['ordered_qty', 'actual_qty', 'pos_qty', 'pos_revenue', 'price']:
            if col not in calc_df.columns:
                calc_df[col] = 0
                
        calc_df['ordered_qty'] = pd.to_numeric(calc_df['ordered_qty'], errors='coerce').fillna(0).astype(int)
        calc_df['price'] = pd.to_numeric(calc_df['price'], errors='coerce').fillna(0).astype(int)
        calc_df['pos_revenue'] = pd.to_numeric(calc_df['pos_revenue'], errors='coerce').fillna(0).astype(int)
        calc_df['item_id'] = calc_df['item_id'].astype(str).apply(lambda x: x.split('_')[0])
        
        # 🌟 單價自動修復 (Auto-Heal)：如果紀錄為0，從主檔補上最新單價
        calc_df['price'] = calc_df.apply(
            lambda row: price_map.get(row['item_id'], 0) if row['price'] == 0 else row['price'], 
            axis=1
        )
        
        est_revenue = (calc_df['ordered_qty'] * calc_df['price']).sum()
        actual_revenue = calc_df['pos_revenue'].sum()
        
        if est_revenue > 0:
            achieve_rate = f"{(actual_revenue / est_revenue) * 100:.1f}"
        elif actual_revenue > 0:
            achieve_rate = "破表 (無預估)"

    st.markdown("#### 💰 營業額戰情板")
    metric_cols = st.columns(4)
    with metric_cols[0]:
        st.metric(label=f"【{selected_dept}】預估營收", value=f"NT$ {est_revenue:,}")
    with metric_cols[1]:
        st.metric(label=f"【{selected_dept}】實際營收", value=f"NT$ {actual_revenue:,}")
    with metric_cols[2]:
        diff = actual_revenue - est_revenue
        st.metric(label="營收落差", value=f"NT$ {diff:,}")
    with metric_cols[3]:
        st.metric(label="營收達成率", value=f"{achieve_rate} %")
        
    st.markdown("<br>", unsafe_allow_html=True)

    # ==========================================
    # 📋 現場執行狀況與人員追蹤
    # ==========================================
    st.markdown(f"#### 📋 {date_str} 出餐與回報追蹤表")
    
    if df_record.empty:
        st.info(f"📅 {date_str} 尚未有任何部門送出出餐計畫。")
    else:
        display_df = df_record.copy()
        
        if selected_dept != "🏢 全公司總覽":
            display_df = display_df[display_df['cat'] == selected_dept]
            
        if display_df.empty:
            st.info(f"📅 {date_str} 【{selected_dept}】尚未送出出餐計畫。")
        else:
            display_df['item_id'] = display_df['item_id'].astype(str).apply(lambda x: x.split('_')[0])
            
            for col in ['plan_operator', 'plan_time', 'report_operator', 'report_time']:
                if col not in display_df.columns: display_df[col] = "未記錄"
            for col in ['pos_qty', 'pos_revenue', 'price']:
                if col not in display_df.columns: display_df[col] = 0
            
            display_df['ordered_qty'] = pd.to_numeric(display_df['ordered_qty'], errors='coerce').fillna(0).astype(int)
            display_df['actual_qty'] = pd.to_numeric(display_df['actual_qty'], errors='coerce').fillna(0).astype(int)
            display_df['pos_qty'] = pd.to_numeric(display_df['pos_qty'], errors='coerce').fillna(0).astype(int)
            
            display_df['price'] = display_df.apply(
                lambda row: price_map.get(row['item_id'], 0) if row['price'] == 0 else row['price'], 
                axis=1
            )

            def check_match(row):
                actual = row['actual_qty']
                pos = row['pos_qty']
                if actual == pos: return "🟢 相符"
                else:
                    diff = actual - pos
                    if diff > 0: return f"🔴 報廢 (+{diff})"
                    else: return f"🔴 短少 ({diff})"

            display_df['match_status'] = display_df.apply(check_match, axis=1)
            
            cols_to_show = {
                'cat': '部門',
                'item_id': '編號',
                'name': '品名',
                'price': '單價', 
                'ordered_qty': '預估出餐',
                'actual_qty': '實際回報',
                'pos_qty': 'POS銷售 🛒', 
                'match_status': '差異比對 ⚖️', 
                'pos_revenue': 'POS營收💰',
                'plan_operator': '建檔人員 📝',
                'plan_time': '建檔時間',
                'report_operator': '回報人員 ✅',
                'report_time': '回報時間'
            }
            
            if selected_dept != "🏢 全公司總覽":
                del cols_to_show['cat']
                
            display_df = display_df[list(cols_to_show.keys())].rename(columns=cols_to_show)
            
            total_items = len(display_df)
            reported_items = len(display_df[display_df['實際回報'] > 0])
            
            # 🛡️ 【終極防彈裝甲】：強制將整張表轉換為純文字字串，徹底杜絕 PyArrow 崩潰！
            safe_display_df = display_df.astype(str)
            
            st.dataframe(
                safe_display_df,
                use_container_width=True,
                hide_index=True,
                height=500 
            )
            
            st.caption(f"💡 數據總覽：共 {total_items} 個品項，已有 {reported_items} 項完成實際回報。")

    st.divider()
    
    # ==========================================
    # 🌟 啟動老闆專屬的最高權限 AI 幕僚
    # ==========================================
    try:
        render_ai_assistant("總管理處", df_sales)
    except Exception as e:
        st.error(f"🤖 AI 幕僚系統準備中... ({e})")
