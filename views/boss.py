import streamlit as st
import pandas as pd
import datetime
import traceback

def show():
    st.markdown("## 📊 總管理處 - 抓蟲除錯模式 🐛")
    
    try:
        st.info("🚀 步驟 1：準備載入 ERP 歷史商品庫 (load_sales_data)...")
        from data_engine import load_sales_data
        df_sales, _ = load_sales_data()
        st.success("✅ 步驟 1 完成！")
        
        all_categories = df_sales['cat'].unique().tolist() if not df_sales.empty else ["生魚片", "壽司", "冰鮮", "活體"]
        
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

        st.info("🚀 步驟 2：準備連線雲端讀取每日紀錄 (load_daily_record)...")
        from record_engine import load_daily_record
        df_record = load_daily_record(date_str)
        st.success("✅ 步驟 2 完成！")

        # --- 算錢邏輯 (省略顯示以精簡) ---
        est_revenue = 0
        actual_revenue = 0
        achieve_rate = "0.0"
        
        if not df_record.empty:
            calc_df = df_record.copy()
            if selected_dept != "🏢 全公司總覽":
                calc_df = calc_df[calc_df['cat'] == selected_dept]
                
            for col in ['ordered_qty', 'actual_qty', 'pos_qty', 'pos_revenue', 'price']:
                if col not in calc_df.columns: calc_df[col] = 0
                    
            calc_df['ordered_qty'] = pd.to_numeric(calc_df['ordered_qty'], errors='coerce').fillna(0).astype(int)
            calc_df['price'] = pd.to_numeric(calc_df['price'], errors='coerce').fillna(0).astype(int)
            calc_df['pos_revenue'] = pd.to_numeric(calc_df['pos_revenue'], errors='coerce').fillna(0).astype(int)
            calc_df['item_id'] = calc_df['item_id'].astype(str).apply(lambda x: x.split('_')[0])
            
            calc_df['price'] = calc_df.apply(
                lambda row: price_map.get(row['item_id'], 0) if row['price'] == 0 else row['price'], 
                axis=1
            )
            
            est_revenue = (calc_df['ordered_qty'] * calc_df['price']).sum()
            actual_revenue = calc_df['pos_revenue'].sum()

        st.markdown("#### 💰 營業額戰情板")
        metric_cols = st.columns(4)
        with metric_cols[0]: st.metric(label="預估營收", value=f"NT$ {est_revenue:,}")
        with metric_cols[1]: st.metric(label="實際營收", value=f"NT$ {actual_revenue:,}")
            
        st.info("🚀 步驟 3：準備處理資料表格式...")
        
        if df_record.empty:
            st.info(f"📅 {date_str} 尚未有出餐計畫。")
        else:
            display_df = df_record.copy()
            if selected_dept != "🏢 全公司總覽":
                display_df = display_df[display_df['cat'] == selected_dept]
                
            if display_df.empty:
                st.info("尚未送出計畫。")
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
                    'item_id': '編號', 'name': '品名', 'price': '單價', 
                    'ordered_qty': '預估', 'actual_qty': '回報', 'pos_qty': 'POS 🛒', 
                    'match_status': '差異', 'pos_revenue': 'POS營收'
                }
                display_df = display_df[list(cols_to_show.keys())].rename(columns=cols_to_show)
                
                st.success("✅ 步驟 3 完成！準備畫出表格...")
                
                # 🛡️ 【聽從 GPT 建議的隔離測試】：不畫 dataframe，改印文字！
                safe_display_df = display_df.astype(str)
                st.write("這是表格的前 5 筆資料 (st.write 模式)：")
                st.write(safe_display_df.head())
                st.success("✅ 步驟 4 (表格繪製) 成功通過，沒有當機！")

        st.divider()
        st.info("🚀 步驟 5：測試是否為 AI 引擎當機？(點擊下方按鈕載入 AI)")
        
        # 把 AI 藏在按鈕後面，確認不是一進來就當機
        if st.button("🤖 測試載入 AI 引擎"):
            try:
                from ai_engine import render_ai_assistant
                render_ai_assistant("總管理處", df_sales)
                st.success("✅ AI 引擎載入成功！")
            except Exception as e:
                st.error(f"❌ AI 引擎掛了: {e}")

    except Exception as e:
        st.error(f"❌ 發生未預期的 Python 錯誤：{e}")
        st.code(traceback.format_exc())
