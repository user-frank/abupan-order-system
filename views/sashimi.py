import streamlit as st
import pandas as pd
import datetime
import urllib.parse
from data_engine import load_sales_data
from record_engine import save_ordered_data, load_daily_record, batch_update_record_qty
from bom_engine import calculate_bom

def show():
    # 1. 取得目前操作人員 (作為紀錄追蹤用)
    current_user = st.session_state.get("user_name", "未知操作員")
    
    # 2. 房間標題 (改用 H3，字體小一點點)
    st.markdown("### 🔪 生魚片部 - 專屬工作區")
    st.markdown("<p style='color: #888; margin-top: -10px; font-size: 14px;'>請直接在表格的【預估數量】或【實際出餐】欄位中輸入數字。</p>", unsafe_allow_html=True)
    
    df, _ = load_sales_data()
    if df.empty:
        st.warning("⚠️ 無法讀取商品資料，請確認 ERP 同步狀態。")
        return
        
    sashimi_df = df[df['cat'] == '生魚片'].copy()
    sashimi_df = sashimi_df.sort_values(by='item_id') 

    tab_plan, tab_report = st.tabs(["📝 1. 早班預估出餐", "✅ 2. 下午實際回報"])

    # ==========================================
    # 分頁 1：早班預估出餐
    # ==========================================
    with tab_plan:
        # 3. 恢復完美的 7 天日期選單
        today = datetime.date.today()
        date_options = []
        date_mapping = {} 
        for i in range(0, 7):
            d = today + datetime.timedelta(days=i)
            wd = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][d.weekday()]
            if i == 0: day_text = "今天"
            elif i == 1: day_text = "明天"
            else: day_text = "預設"
            label = f"{wd} ({day_text}) - {d.strftime('%m/%d')}"
            date_options.append(label)
            date_mapping[label] = d.strftime("%Y-%m-%d")

        selected_date_label = st.selectbox("📌 選擇出餐日期", date_options)
        target_date_str = date_mapping[selected_date_label]
        
        st.divider()
        
        editor_df = sashimi_df[['item_id', 'name', 'wd_avg']].copy()
        editor_df['預估數量'] = 0
        editor_df = editor_df.rename(columns={'item_id': '編號', 'name': '品名', 'wd_avg': '平日均銷(參考)'})
        
        st.markdown("#### 📊 出餐計畫表")
        edited_df = st.data_editor(
            editor_df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "編號": st.column_config.TextColumn("編號", disabled=True),
                "品名": st.column_config.TextColumn("品名", disabled=True),
                "平日均銷(參考)": st.column_config.NumberColumn("參考", disabled=True),
                "預估數量": st.column_config.NumberColumn("預估數量 ✍️", min_value=0, step=1, format="%d")
            }
        )
        
        # 4. 解決「表格上沒有的商品」：手動新增區塊
        if "sashimi_temp_items" not in st.session_state:
            st.session_state.sashimi_temp_items = []

        with st.expander("➕ 表格上沒有？點此手動新增臨時品項"):
            col1, col2, col3 = st.columns([2, 4, 2])
            with col1: temp_id = st.text_input("編號 (選填)", key="s_temp_id", placeholder="例如: 999")
            with col2: temp_name = st.text_input("品名 (必填)", key="s_temp_name", placeholder="例如: 鮭魚特製拼盤")
            with col3: temp_qty = st.number_input("數量", min_value=1, step=1, key="s_temp_qty")
            
            if st.button("➕ 加入臨時清單", use_container_width=True):
                if temp_name.strip() == "":
                    st.error("品名不能為空！")
                else:
                    st.session_state.sashimi_temp_items.append({
                        "item_id": temp_id if temp_id else f"臨時_{len(st.session_state.sashimi_temp_items)+1}",
                        "name": f"【臨時】{temp_name}",
                        "qty": temp_qty
                    })
                    st.rerun()

        # 顯示已加入的臨時品項
        if st.session_state.sashimi_temp_items:
            st.markdown("<div style='background-color: #332d22; padding: 10px; border-radius: 5px;'>", unsafe_allow_html=True)
            st.markdown("##### 🛒 臨時新增清單")
            for idx, item in enumerate(st.session_state.sashimi_temp_items):
                st.markdown(f"- {item['name']} ➜ **{item['qty']} 份**")
            if st.button("🗑️ 清除臨時清單", size="small"):
                st.session_state.sashimi_temp_items = []
                st.rerun()
            st.markdown("</div><br>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        note = st.text_input("📝 備註事項 (人員排班或特殊交代)", placeholder="例如：切魚-阿君、開魚-阿君...")
        
        if st.button("💾 確認存檔並產生 LINE 指令", type="primary", use_container_width=True):
            valid_items = edited_df[edited_df['預估數量'] > 0]
            
            if valid_items.empty and not st.session_state.sashimi_temp_items:
                st.warning("請至少輸入一項商品的預估數量，或是新增臨時商品！")
            else:
                cart_dict = {}
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # 寫入正規商品 (同時加入操作人與時間紀錄！)
                for _, row in valid_items.iterrows():
                    cart_key = f"{row['編號']}_{row['品名']}"
                    cart_dict[cart_key] = {
                        'item_id': row['編號'],
                        'name': row['品名'],
                        'cat': '生魚片',
                        'qty': row['預估數量'],
                        'operator': current_user,  # 追蹤是誰建檔的
                        'update_time': current_time # 追蹤建檔時間
                    }
                
                # 寫入臨時商品
                for temp_item in st.session_state.sashimi_temp_items:
                    cart_key = f"{temp_item['item_id']}_{temp_item['name']}"
                    cart_dict[cart_key] = {
                        'item_id': temp_item['item_id'],
                        'name': temp_item['name'],
                        'cat': '生魚片',
                        'qty': temp_item['qty'],
                        'operator': current_user,
                        'update_time': current_time
                    }
                
                save_ordered_data(target_date_str, cart_dict)
                
                # 產生 LINE 訊息
                msg = f"🐟 【阿布潘員工系統 - 生魚片部】 🐟\n🗓️ 出餐日期：{target_date_str}\n👨‍💻 填表人員：{current_user}\n──────────────────\n📋 【預估出餐明細】\n"
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
                
                # 清除臨時清單並準備發送
                st.session_state.sashimi_temp_items = []
                line_url = f"https://line.me/R/msg/text/?{urllib.parse.quote(msg)}"
                st.success(f"✅ {target_date_str} 的出餐計畫已存檔！(操作人：{current_user})")
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
            sashimi_records = df_record[df_record['cat'] == '生魚片'].copy()
            
            if sashimi_records.empty:
                st.info(f"該日生魚片部無出餐紀錄。")
            else:
                st.markdown(f"#### 📝 {date_str} 實際出餐回報表")
                st.markdown("<p style='color: #FF6B6B; font-size: 14px;'>※ 請在下午三點前，將【實際出餐】欄位填妥並按下底部的儲存。</p>", unsafe_allow_html=True)
                
                sashimi_records['item_id_clean'] = sashimi_records['item_id'].apply(lambda x: str(x).split('_')[0])
                report_df = sashimi_records[['item_id_clean', 'name', 'ordered_qty', 'actual_qty', 'cart_key']].copy()
                report_df = report_df.rename(columns={'item_id_clean': '編號', 'name': '品名', 'ordered_qty': '預估數量', 'actual_qty': '實際出餐'})
                
                edited_report_df = st.data_editor(
                    report_df,
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "cart_key": None, 
                        "編號": st.column_config.TextColumn("編號", disabled=True),
                        "品名": st.column_config.TextColumn("品名", disabled=True),
                        "預估數量": st.column_config.NumberColumn("預估數量", disabled=True),
                        "實際出餐": st.column_config.NumberColumn("實際出餐 ✍️", min_value=0, step=1, format="%d")
                    }
                )
                
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("💾 批次儲存今日實際出餐", type="primary", use_container_width=True):
                    actual_updates = {}
                    for _, row in edited_report_df.iterrows():
                        actual_updates[row['cart_key']] = row['實際出餐']
                    
                    batch_update_record_qty(date_str, actual_updates)
                    # 提示文字加上追蹤人，讓員工知道系統有在記錄
                    st.success(f"✅ 實際生產量已全數批次更新成功！(回報人：{current_user})")
