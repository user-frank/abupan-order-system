import streamlit as st
import pandas as pd
import datetime
import urllib.parse
from data_engine import load_sales_data
from record_engine import save_ordered_data, load_daily_record, batch_update_record_qty
from bom_engine import calculate_bom

def show():
    # 房間標題
    st.title("🔪 生魚片部 - 專屬工作區")
    st.markdown("<p style='color: #888; margin-top: -15px;'>請直接在表格的【預估數量】或【實際出餐】欄位中輸入數字。</p>", unsafe_allow_html=True)
    
    # 載入資料並過濾出「生魚片」部門
    df, _ = load_sales_data()
    if df.empty:
        st.warning("⚠️ 無法讀取商品資料，請確認 ERP 同步狀態。")
        return
        
    sashimi_df = df[df['cat'] == '生魚片'].copy()
    # 依照編號排序，讓同類商品(如黑鮪魚系列)排在一起，符合 Excel 習慣
    sashimi_df = sashimi_df.sort_values(by='item_id') 

    # 建立兩個分頁，對應早上的「預估」和下午的「回報」
    tab_plan, tab_report = st.tabs(["📝 1. 早班預估出餐 (填寫計畫)", "✅ 2. 下午實際回報 (下班前填寫)"])

    # ==========================================
    # 分頁 1：早班預估出餐
    # ==========================================
    with tab_plan:
        # 日期選擇
        today = datetime.date.today()
        date_options = [
            f"今天 ({today.strftime('%m/%d')})",
            f"明天 ({(today + datetime.timedelta(days=1)).strftime('%m/%d')})"
        ]
        selected_date_label = st.radio("📌 選擇出餐日期", date_options, horizontal=True)
        target_date_str = today.strftime("%Y-%m-%d") if "今天" in selected_date_label else (today + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        
        st.divider()
        
        # 準備要顯示在 Excel 表格裡的資料
        # 我們只挑選需要的欄位，並加上一個預設為 0 的「預估數量」欄位
        editor_df = sashimi_df[['item_id', 'name', 'wd_avg']].copy()
        editor_df['預估數量'] = 0
        editor_df = editor_df.rename(columns={'item_id': '編號', 'name': '品名', 'wd_avg': '平日均銷(參考)'})
        
        # 顯示互動式資料表格 (激似 Excel)
        st.markdown("#### 📊 出餐計畫表")
        edited_df = st.data_editor(
            editor_df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "編號": st.column_config.TextColumn("編號", disabled=True),
                "品名": st.column_config.TextColumn("品名", disabled=True),
                "平日均銷(參考)": st.column_config.NumberColumn("參考", disabled=True),
                # 讓這格變成可輸入的數字，並加上筆的圖示提示
                "預估數量": st.column_config.NumberColumn("預估數量 ✍️", min_value=0, step=1, format="%d")
            }
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        note = st.text_input("📝 備註事項 (人員排班或特殊交代)", placeholder="例如：切魚-阿君、開魚-阿君...")
        
        # 處理送出邏輯
        if st.button("💾 確認存檔並產生 LINE 指令", type="primary", use_container_width=True):
            # 把填寫數量大於 0 的商品挑出來
            valid_items = edited_df[edited_df['預估數量'] > 0]
            
            if valid_items.empty:
                st.warning("請至少輸入一項商品的預估數量！")
            else:
                # 1. 轉換成 record_engine 存檔需要的格式
                cart_dict = {}
                for _, row in valid_items.iterrows():
                    cart_key = f"{row['編號']}_{row['品名']}"
                    cart_dict[cart_key] = {
                        'item_id': row['編號'],
                        'name': row['品名'],
                        'cat': '生魚片',
                        'qty': row['預估數量']
                    }
                
                # 2. 存入資料庫
                save_ordered_data(target_date_str, cart_dict)
                
                # 3. 產生跟以前一模一樣的 LINE 訊息
                msg = f"🐟 【阿布潘員工系統 - 生魚片部】 🐟\n🗓️ 出餐日期：{target_date_str}\n──────────────────\n📋 【預估出餐明細】\n"
                for _, data in cart_dict.items():
                    msg += f"🔸 {data['name']} ➜ {data['qty']} 份\n"
                
                msg += "\n──────────────────\n📦 【預估備料需求】\n"
                bom_df = calculate_bom(cart_dict)
                if not bom_df.empty and '原物料名稱' in bom_df.columns:
                    for _, r in bom_df.iterrows(): 
                        msg += f"🔹 {r['原物料名稱']} ➜ {r['預估需求量']}\n"
                else:
                    msg += "尚無對應原料設定。\n"
                
                if note: msg += f"\n──────────────────\n💡 【備註】：\n{note}\n"
                
                # 4. 產生 LINE 連結並顯示
                line_url = f"https://line.me/R/msg/text/?{urllib.parse.quote(msg)}"
                st.success(f"✅ {target_date_str} 的出餐計畫已存檔！")
                st.link_button("🚀 點擊這裡打開 LINE 發送至群組", url=line_url, type="primary", use_container_width=True)

    # ==========================================
    # 分頁 2：下午實際回報
    # ==========================================
    with tab_report:
        report_date = st.date_input("📌 選擇回報日期", value=today)
        date_str = report_date.strftime("%Y-%m-%d")
        
        df_record = load_daily_record(date_str)
        
        if df_record.empty:
            st.info(f"資料庫中尚未有 {date_str} 的生魚片出餐紀錄。")
        else:
            # 只顯示生魚片部的紀錄
            sashimi_records = df_record[df_record['cat'] == '生魚片'].copy()
            
            if sashimi_records.empty:
                st.info(f"該日生魚片部無出餐紀錄。")
            else:
                st.markdown(f"#### 📝 {date_str} 實際出餐回報表")
                st.markdown("<p style='color: #FF6B6B;'>※ 請在下午三點前，將【實際出餐】欄位填妥並按下底部的儲存。</p>", unsafe_allow_html=True)
                
                # 準備回報用的 Excel 表格
                sashimi_records['item_id_clean'] = sashimi_records['item_id'].apply(lambda x: str(x).split('_')[0])
                report_df = sashimi_records[['item_id_clean', 'name', 'ordered_qty', 'actual_qty', 'cart_key']].copy()
                report_df = report_df.rename(columns={'item_id_clean': '編號', 'name': '品名', 'ordered_qty': '預估數量', 'actual_qty': '實際出餐'})
                
                # 顯示可編輯表格
                edited_report_df = st.data_editor(
                    report_df,
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "cart_key": None, # 隱藏系統用的 key，不給員工看
                        "編號": st.column_config.TextColumn("編號", disabled=True),
                        "品名": st.column_config.TextColumn("品名", disabled=True),
                        "預估數量": st.column_config.NumberColumn("預估數量", disabled=True),
                        # 讓「實際出餐」可以編輯
                        "實際出餐": st.column_config.NumberColumn("實際出餐 ✍️", min_value=0, step=1, format="%d")
                    }
                )
                
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("💾 批次儲存今日實際出餐", type="primary", use_container_width=True):
                    # 抓出有被修改或是填寫的資料
                    actual_updates = {}
                    for _, row in edited_report_df.iterrows():
                        actual_updates[row['cart_key']] = row['實際出餐']
                    
                    batch_update_record_qty(date_str, actual_updates)
                    st.success("✅ 實際生產量已全數批次更新成功！")
