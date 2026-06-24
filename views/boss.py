import streamlit as st
import pandas as pd
import datetime
from data_engine import load_sales_data
from record_engine import load_daily_record

def show():
    # ==========================================
    # 1. 頁面標題與基本設定
    # ==========================================
    st.markdown("## 📊 總管理處 - 老闆戰情室")
    st.markdown("<p style='color: #888; font-size: 14px;'>全公司營運數據總覽與人員操作追蹤 (唯讀模式)</p>", unsafe_allow_html=True)
    
    # 讀取 ERP 歷史銷售資料 (用於抓取部門列表與排行榜)
    df_sales, _ = load_sales_data()
    all_categories = df_sales['cat'].unique().tolist() if not df_sales.empty else ["生魚片", "壽司", "冰鮮", "活體"]
    
    # ==========================================
    # 2. 戰情室控制台 (日期與部門篩選)
    # ==========================================
    col_date, col_dept = st.columns(2)
    with col_date:
        target_date = st.date_input("🗓️ 選擇檢視日期", value=datetime.date.today())
        date_str = target_date.strftime("%Y-%m-%d")
    with col_dept:
        dept_options = ["🏢 全公司總覽"] + all_categories
        selected_dept = st.selectbox("📌 選擇檢視部門", dept_options)
        
    st.divider()

    # ==========================================
    # 3. 💰 營業額戰情板 (預留擴充區塊)
    # ==========================================
    st.markdown("#### 💰 營業額戰情板 (系統建置串接中...)")
    metric_cols = st.columns(4)
    with metric_cols[0]:
        st.metric(label="今日預估總營業額", value="NT$ ---", delta="待 ERP 單價串接", delta_color="off")
    with metric_cols[1]:
        st.metric(label=f"【{selected_dept}】預估營收", value="NT$ ---")
    with metric_cols[2]:
        st.metric(label=f"【{selected_dept}】實際營收", value="NT$ ---")
    with metric_cols[3]:
        st.metric(label="營收達成率", value="--- %")
        
    st.markdown("<br>", unsafe_allow_html=True)

    # ==========================================
    # 4. 📋 現場執行狀況與人員追蹤
    # ==========================================
    st.markdown(f"#### 📋 {date_str} 出餐與回報追蹤表")
    
    df_record = load_daily_record(date_str)
    
    if df_record.empty:
        st.info(f"📅 {date_str} 尚未有任何部門送出出餐計畫。")
    else:
        # 依照選擇過濾部門
        if selected_dept != "🏢 全公司總覽":
            df_record = df_record[df_record['cat'] == selected_dept]
            
        if df_record.empty:
            st.info(f"📅 {date_str} 【{selected_dept}】尚未送出出餐計畫。")
        else:
            # 整理要給老闆看的欄位
            display_df = df_record.copy()
            
            # 清理 item_id (把後面附加的字串拿掉)
            display_df['item_id'] = display_df['item_id'].astype(str).apply(lambda x: x.split('_')[0])
            
            # 確保操作人與更新時間的欄位存在 (相容舊資料)
            if 'operator' not in display_df.columns: display_df['operator'] = "未記錄"
            if 'update_time' not in display_df.columns: display_df['update_time'] = "未記錄"
            
            # 選取並重新命名欄位
            cols_to_show = {
                'cat': '部門',
                'item_id': '編號',
                'name': '品名',
                'ordered_qty': '預估出餐 (份)',
                'actual_qty': '實際回報 (份)',
                'operator': '建檔/操作人員 👤',
                'update_time': '系統登錄時間 🕒'
            }
            
            # 如果是看單一部門，就把「部門」欄位隱藏讓畫面更乾淨
            if selected_dept != "🏢 全公司總覽":
                del cols_to_show['cat']
                
            display_df = display_df[list(cols_to_show.keys())].rename(columns=cols_to_show)
            
            # 使用 dataframe 顯示 (設定為不可編輯)
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                height=400 # 固定高度讓版面整齊
            )
            
            # 計算回報進度小工具
            total_items = len(display_df)
            reported_items = len(display_df[display_df['實際回報 (份)'] > 0])
            st.caption(f"💡 數據總覽：共 {total_items} 個品項，已有 {reported_items} 項完成實際回報。")

    st.divider()

    # ==========================================
    # 5. 📈 歷史銷售數據排行榜
    # ==========================================
    if not df_sales.empty:
        st.markdown(f"#### 📈 歷史銷售數據排行")
        st.markdown("<span style='font-size:12px;color:#888;'>數據來源：ERP 歷史銷售資料</span>", unsafe_allow_html=True)
        
        # 決定要排名的 DataFrame
        rank_df = df_sales.copy()
        if selected_dept != "🏢 全公司總覽":
            rank_df = rank_df[rank_df['cat'] == selected_dept]
            
        col_top, col_bot = st.columns(2)
        
        with col_top:
            st.success(f"🏆 歷史總銷量 前 10 名")
            top_df = rank_df.sort_values(by="total_sales", ascending=False).head(10)
            st.dataframe(
                top_df[['item_id', 'name', 'wd_avg', 'we_avg']].rename(columns={'item_id':'編號', 'name':'品名', 'wd_avg':'平日均銷', 'we_avg':'假日均銷'}),
                hide_index=True, use_container_width=True
            )
            
        with col_bot:
            st.error(f"⚠️ 本月銷售 倒數 10 名 (滯銷警示)")
            bot_df = rank_df[rank_df['cm_sales'] > 0].sort_values(by="cm_sales", ascending=True).head(10)
            if bot_df.empty:
                st.info("本月尚無有效銷售數據可供排名。")
            else:
                st.dataframe(
                    bot_df[['item_id', 'name', 'cm_sales']].rename(columns={'item_id':'編號', 'name':'品名', 'cm_sales':'本月銷量'}),
                    hide_index=True, use_container_width=True
                )
