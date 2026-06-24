import streamlit as st
import pandas as pd
import datetime
from data_engine import load_sales_data
from record_engine import load_daily_record

def show():
    st.markdown("## 📊 總管理 - 老闆")
    st.markdown("<p style='color: #888; font-size: 14px;'>全公司營運數據總覽與人員操作追蹤 </p>", unsafe_allow_html=True)
    
    df_sales, _ = load_sales_data()
    all_categories = df_sales['cat'].unique().tolist() if not df_sales.empty else ["生魚片", "壽司", "冰鮮", "活體"]
    
    col_date, col_dept = st.columns(2)
    with col_date:
        target_date = st.date_input("🗓️ 選擇檢視日期", value=datetime.date.today())
        date_str = target_date.strftime("%Y-%m-%d")
    with col_dept:
        dept_options = ["🏢 全公司總覽"] + all_categories
        selected_dept = st.selectbox("📌 選擇檢視部門", dept_options)
        
    st.divider()

    st.markdown("#### 💰 營業額戰情板 (預留擴充區段...)")
    metric_cols = st.columns(4)
    with metric_cols[0]:
        st.metric(label="今日預估總營業額", value="NT$ ---", delta="待單價串接", delta_color="off")
    with metric_cols[1]:
        st.metric(label=f"【{selected_dept}】預估營收", value="NT$ ---")
    with metric_cols[2]:
        st.metric(label=f"【{selected_dept}】實際營收", value="NT$ ---")
    with metric_cols[3]:
        st.metric(label="營收達成率", value="--- %")
        
    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(f"#### 📋 {date_str} 出餐與回報追蹤表")
    
    with st.spinner("載入戰情數據中..."):
        df_record = load_daily_record(date_str)
    
    if df_record.empty:
        st.info(f"📅 {date_str} 尚未有任何部門送出出餐計畫。")
    else:
        if selected_dept != "🏢 全公司總覽":
            df_record = df_record[df_record['cat'] == selected_dept]
            
        if df_record.empty:
            st.info(f"📅 {date_str} 【{selected_dept}】尚未送出出餐計畫。")
        else:
            display_df = df_record.copy()
            display_df['item_id'] = display_df['item_id'].astype(str).apply(lambda x: x.split('_')[0])
            
            # 確保所有需要的追蹤與 POS 欄位都存在 (相容性防護)
            for col in ['plan_operator', 'plan_time', 'report_operator', 'report_time']:
                if col not in display_df.columns: display_df[col] = "未記錄"
            if 'pos_qty' not in display_df.columns: display_df['pos_qty'] = 0
            
            # 確保計算欄位都是整數數字
            display_df['ordered_qty'] = pd.to_numeric(display_df['ordered_qty'], errors='coerce').fillna(0).astype(int)
            display_df['actual_qty'] = pd.to_numeric(display_df['actual_qty'], errors='coerce').fillna(0).astype(int)
            display_df['pos_qty'] = pd.to_numeric(display_df['pos_qty'], errors='coerce').fillna(0).astype(int)

            # 🌟 核心商業邏輯：計算差異與紅綠燈
            def check_match(row):
                actual = row['actual_qty']
                pos = row['pos_qty']
                if actual == pos:
                    return "🟢 相符"
                else:
                    diff = actual - pos
                    if diff > 0:
                        return f"🔴 較多 (+{diff})"
                    else:
                        return f"🔴 短少 ({diff})"

            # 套用計算邏輯
            display_df['match_status'] = display_df.apply(check_match, axis=1)
            
            # 重新排列老闆要看的欄位 (把重點數字放在中間)
            cols_to_show = {
                'cat': '部門',
                'item_id': '編號',
                'name': '品名',
                'ordered_qty': '預估出餐',
                'actual_qty': '實際回報',
                'pos_qty': 'POS銷售 🛒',        # 🌟 新增 POS 欄位
                'match_status': '差異比對 ⚖️',  # 🌟 新增比對結果
                'plan_operator': '建檔人員 📝',
                'plan_time': '建檔時間',
                'report_operator': '回報人員 ✅',
                'report_time': '回報時間'
            }
            
            if selected_dept != "🏢 全公司總覽":
                del cols_to_show['cat']
                
            display_df = display_df[list(cols_to_show.keys())].rename(columns=cols_to_show)
            
            # 使用 dataframe 顯示
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                height=500 
            )
            
            total_items = len(display_df)
            reported_items = len(display_df[display_df['實際回報'] > 0])
            st.caption(f"💡 數據總覽：共 {total_items} 個品項，已有 {reported_items} 項完成實際回報。")
