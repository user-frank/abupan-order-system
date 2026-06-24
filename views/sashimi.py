import streamlit as st
import pandas as pd
import datetime
import urllib.parse
from data_engine import load_sales_data
from record_engine import save_ordered_data, load_daily_record, batch_update_record_qty
from bom_engine import calculate_bom

# 🌟 導入雲端設定引擎
from config_engine import load_menu_template, save_menu_template, load_custom_items, save_custom_items

def show():
    current_user = st.session_state.get("user_name", "未知操作員")
    DEPT_NAME = "生魚片" 
    
    today = datetime.date.today() 
    
    st.markdown("### 🔪 生魚片部 - 專屬工作區")
    
    df, _ = load_sales_data()
    if df.empty:
        st.warning("⚠️ 無法讀取 ERP 商品資料。")
        return
        
    sashimi_df = df[df['cat'] == '生魚片'].copy()
    sashimi_df['item_id'] = sashimi_df['item_id'].astype(str)

    custom_items = load_custom_items(DEPT_NAME)
    if custom_items:
        custom_df = pd.DataFrame(custom_items)
        custom_df['cat'] = '生魚片'
        custom_df['wd_avg'] = 0.0 
        custom_df['item_id'] = custom_df['item_id'].astype(str) 
        sashimi_df = pd.concat([sashimi_df, custom_df], ignore_index=True)

    sashimi_df = sashimi_df.sort_values(by='item_id') 

    tab_plan, tab_report = st.tabs(["📝 1. 預估出餐", "✅ 2. 實際回報"])

    # ==========================================
    # 分頁 1：預估出餐
    # ==========================================
    with tab_plan:
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

        selected_date_label = st.selectbox("📌 選擇出餐日期", date_options, key="plan_date")
        target_date_str = date_mapping[selected_date_label]
        
        st.divider()
        
        all_item_options = (sashimi_df['item_id'] + " - " + sashimi_df['name']).tolist()
        
        active_item_ids = load_menu_template(DEPT_NAME)
        if active_item_ids is None:
            active_item_ids = sashimi_df['item_id'].tolist()
        
        active_item_ids = [str(x) for x in active_item_ids]
            
        current_default_options = sashimi_df[sashimi_df['item_id'].isin(active_item_ids)]['item_id'] + " - " + sashimi_df[sashimi_df['item_id'].isin(active_item_ids)]['name']
        current_default_options = current_default_options.tolist()
        
        with st.expander("⚙️ 系統設定：自訂常態菜單 & 新增未建檔商品"):
            st.markdown("#### 1️⃣ 隱藏 / 顯示現有商品")
            selected_options = st.multiselect("選擇常態出餐商品：", options=all_item_options, default=current_default_options, label_visibility="collapsed", key="menu_filter")
            if st.button("💾 儲存並更新畫面", use_container_width=True, key="btn_save_menu"):
                new_active_ids = [opt.split(" - ")[0] for opt in selected_options]
                with st.spinner("正在寫入雲端..."):
                    success = save_menu_template(DEPT_NAME, new_active_ids)
                if success:
                    st.success("✅ 菜單已成功更新至雲端！")
                    st.rerun()

            st.divider()
            st.markdown("#### 2️⃣ 新增「ERP 尚未建檔」的新產品")
            col_id, col_name, col_btn = st.columns([2, 4, 2])
            with col_id: new_c_id = st.text_input("自訂編號 (選填)", placeholder="例: N001", key="new_c_id")
            with col_name: new_c_name = st.text_input("新商品名稱 (必填)", placeholder="例: 炙燒特選黑鮪", key="new_c_name")
            with col_btn:
                st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
                if st.button("➕ 永久加入系統", type="primary", use_container_width=True, key="btn_add_custom"):
                    if not new_c_name.strip():
                        st.error("商品名稱不能為空！")
                    else:
                        final_id = new_c_id.strip() if new_c_id.strip() else f"NEW_{int(datetime.datetime.now().timestamp())}"
                        
                        existing_ids = sashimi_df['item_id'].values
                        if final_id in existing_ids:
                            st.error(f"❌ 錯誤：編號 '{final_id}' 已存在於系統中，請更換一個編號！")
                        else:
                            c_list = load_custom_items(DEPT_NAME)
                            c_list.append({"item_id": final_id, "name": new_c_name})
                            
                            with st.spinner(f"正在將 {new_c_name} 寫入 Google 試算表..."):
                                success1 = save_custom_items(DEPT_NAME, c_list)
                                
                                active_list = load_menu_template(DEPT_NAME) or []
                                if final_id not in active_list:
                                    active_list.append(final_id)
                                    success2 = save_menu_template(DEPT_NAME, active_list)
                                else:
                                    success2 = True
                                    
                            if success1 and success2:
                                st.success(f"✅ {new_c_name} 已成功加入雲端！")
                                st.rerun()
        
        display_df = sashimi_df[sashimi_df['item_id'].isin(active_item_ids)].copy()
        
        # ==========================================
        # 🌟 方案 B：手機專屬大卡片輸入模式 (預估出餐)
        # ==========================================
        st.markdown(f"#### 📊 出餐計畫表 (共 {len(display_df)} 項)")
        st.markdown("<p style='color: #888; font-size: 13px;'>請透過右側 ➕➖ 按鈕或直接點擊數字輸入。</p>", unsafe_allow_html=True)
        
        plan_qty_dict = {} # 用來收集每個商品的輸入數量
        
        for _, row in display_df.iterrows():
            with st.container(border=True):
                # 利用 columns 完美切分左右，且垂直置中對齊
                col_info, col_input = st.columns([6, 4], vertical_alignment="center")
                with col_info:
                    st.markdown(f"<span style='font-size:16px; font-weight:bold; color:white;'>{row['name']}</span><br><span style='color:#888; font-size:12px;'>編號: {row['item_id']} | 參考均銷: {row['wd_avg']}</span>", unsafe_allow_html=True)
                with col_input:
                    # 給每個商品一個專屬的大輸入框
                    plan_qty_dict[row['item_id']] = st.number_input(
                        "數量", min_value=0, step=1, value=0, 
                        key=f"plan_{row['item_id']}", label_visibility="collapsed"
                    )

        if "sashimi_temp_items" not in st.session_state:
            st.session_state.sashimi_temp_items = []

        with st.expander("📝 遇到單次客製化需求？點此手動輸入【臨時品項】"):
            col1, col2, col3 = st.columns([2, 4, 2])
            with col1: temp_id = st.text_input("編號 (選填)", key="s_temp_id", placeholder="例如: 999")
            with col2: temp_name = st.text_input("品名 (必填)", key="s_temp_name", placeholder="例如: 鮭魚去鱗特製版")
            with col3: temp_qty = st.number_input("數量", min_value=1, step=1, key="s_temp_qty")
            
            if st.button("➕ 加入本次訂單", use_container_width=True, key="btn_add_temp"):
                if temp_name.strip() == "":
                    st.error("品名不能為空！")
                else:
                    st.session_state.sashimi_temp_items.append({
                        "item_id": temp_id if temp_id else f"臨時_{len(st.session_state.sashimi_temp_items)+1}",
                        "name": f"【客製】{temp_name}",
                        "qty": temp_qty
                    })
                    st.rerun()

        if st.session_state.sashimi_temp_items:
            st.markdown("<div style='background-color: #332d22; padding: 10px; border-radius: 5px;'>", unsafe_allow_html=True)
            st.markdown("##### 🛒 本次額外客製化清單")
            for idx, item in enumerate(st.session_state.sashimi_temp_items):
                st.markdown(f"- {item['name']} ➜ **{item['qty']} 份**")
            if st.button("🗑️ 清除客製化清單", size="small", key="btn_clear_temp"):
                st.session_state.sashimi_temp_items = []
                st.rerun()
            st.markdown("</div><br>", unsafe_allow_html=True)

        note = st.text_input("📝 備註事項 (人員排班或特殊交代)", placeholder="例如：切魚-阿君、開魚-阿君...", key="plan_note")
        
        if st.button("💾 確認存檔並產生 LINE 指令", type="primary", use_container_width=True, key="btn_save_plan"):
            
            # 從剛剛蒐集的字典中，抓出數量大於 0 的商品
            valid_items = []
            for _, row in display_df.iterrows():
                qty = plan_qty_dict.get(row['item_id'], 0)
                if qty > 0:
                    valid_items.append({'item_id': str(row['item_id']), 'name': row['name'], 'qty': qty})
            
            if not valid_items and not st.session_state.sashimi_temp_items:
                st.warning("請至少輸入一項商品的預估數量，或是新增客製化商品！")
            else:
                cart_dict = {}
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # 正規商品寫入
                for item in valid_items:
                    cart_key = f"{item['item_id']}_{item['name']}"
                    cart_dict[cart_key] = {
                        'item_id': item['item_id'], 'name': item['name'], 'cat': '生魚片',
                        'qty': item['qty'], 'operator': current_user, 'update_time': current_time 
                    }
                
                # 臨時商品寫入
                for temp_item in st.session_state.sashimi_temp_items:
                    cart_key = f"{temp_item['item_id']}_{temp_item['name']}"
                    cart_dict[cart_key] = {
                        'item_id': str(temp_item['item_id']), 'name': temp_item['name'], 'cat': '生魚片',
                        'qty': temp_item['qty'], 'operator': current_user, 'update_time': current_time
                    }
                
                with st.spinner("訂單存檔中..."):
                    save_ordered_data(target_date_str, cart_dict)
                
                msg = f"🐟 【阿布潘員工系統 - 生魚片部】 🐟\n🗓️ 出餐日期：{target_date_str}\n👨‍💻 填表人員：{current_user}\n──────────────────\n📋 【預估出餐明細】\n"
                for _, data in cart_dict.items():
                    msg += f"🔸 {data['name']} ➜ {data['qty']} 份\n"
                
                msg += "\n──────────────────\n📦 【預估備料需求】\n"
                bom_df = calculate_bom(cart_dict)
                if not bom_df.empty and '原物料名稱' in bom_df.columns:
                    for _, r in bom_df.iterrows(): msg += f"🔹 {r['原物料名稱']} ➜ {r['預估需求量']}\n"
                else: msg += "尚無對應原料設定。\n"
                if note: msg += f"\n──────────────────\n💡 【備註】：\n{note}\n"
                
                st.session_state.sashimi_temp_items = []
                line_url = f"https://line.me/R/msg/text/?{urllib.parse.quote(msg)}"
                st.success(f"✅ {target_date_str} 的出餐計畫已存檔！(操作人：{current_user})")
                st.link_button("🚀 點擊這裡打開 LINE 發送至群組", url=line_url, type="primary", use_container_width=True)

    # ==========================================
    # 分頁 2：實際回報
    # ==========================================
    with tab_report:
        report_date = st.date_input("📌 選擇回報日期", value=today, key="report_date")
        date_str = report_date.strftime("%Y-%m-%d")
        
        with st.spinner("讀取回報紀錄中..."):
            df_record = load_daily_record(date_str)
            
        sashimi_records = df_record[df_record['cat'] == '生魚片'].copy() if not df_record.empty else pd.DataFrame()
        
        if sashimi_records.empty:
            st.info(f"該日生魚片部尚無任何出餐紀錄。")
        else:
            st.markdown(f"#### 📝 {date_str} 實際出餐回報表")
            st.markdown("<p style='color: #FF6B6B; font-size: 14px;'>※ 請在下班前，將【實際出餐】欄位填妥並按下底部的儲存。</p>", unsafe_allow_html=True)
            
            # ==========================================
            # 🌟 方案 B：手機專屬大卡片輸入模式 (實際回報)
            # ==========================================
            actual_updates = {} # 蒐集被修改的資料
            
            for _, row in sashimi_records.iterrows():
                cart_key = row['cart_key']
                original_qty = int(row['actual_qty'])
                
                with st.container(border=True):
                    col_info, col_input = st.columns([6, 4], vertical_alignment="center")
                    with col_info:
                        clean_id = str(row['item_id']).split('_')[0]
                        st.markdown(f"<span style='font-size:16px; font-weight:bold; color:white;'>{row['name']}</span><br><span style='color:#888; font-size:13px;'>編號: {clean_id} | 預估: <span style='color:#FFD93D; font-weight:bold;'>{row['ordered_qty']} 份</span></span>", unsafe_allow_html=True)
                    with col_input:
                        # 將預設值設定為資料庫裡紀錄的數字
                        new_qty = st.number_input(
                            "實際出餐", min_value=0, step=1, value=original_qty, 
                            key=f"report_{cart_key}", label_visibility="collapsed"
                        )
                        # 【智慧差集判斷】：如果畫面的數字跟資料庫不一樣，就加入更新清單
                        if str(original_qty) != str(new_qty):
                            actual_updates[cart_key] = new_qty
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("💾 批次儲存今日實際出餐", type="primary", use_container_width=True, key="btn_save_report"):
                if not actual_updates:
                    st.warning("⚠️ 沒有偵測到任何數量的變更，無須存檔。")
                else:
                    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    with st.spinner("儲存回報中..."):
                        batch_update_record_qty(date_str, actual_updates, current_user, current_time)
                    st.success(f"✅ 實際生產量已全數批次更新成功！(回報人：{current_user})")
                    st.rerun()

        st.divider()
        with st.expander("➕ 補登未在預估單上的出餐品項 (下午臨時加出)"):
            st.markdown("<span style='font-size:12px;color:#888;'>如果下午有出餐，但早上的預估單裡面沒有這個品項，請在這裡補登。</span>", unsafe_allow_html=True)
            
            all_sashimi_options = (sashimi_df['item_id'] + " - " + sashimi_df['name']).tolist()
            ad_hoc_opt = st.selectbox("選擇臨時加出的品項", all_sashimi_options, key="adhoc_sel")
            ad_hoc_qty = st.number_input("實際出餐數量", min_value=1, step=1, key="adhoc_qty")
            
            if st.button("➕ 立即補登至今日回報單", use_container_width=True, key="btn_add_adhoc"):
                ad_id = ad_hoc_opt.split(" - ")[0]
                ad_name = ad_hoc_opt.split(" - ")[1]
                ad_cart_key = f"{ad_id}_{ad_name}"
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                adhoc_dict = {
                    ad_cart_key: {
                        'item_id': ad_id, 'name': ad_name, 'cat': '生魚片',
                        'qty': 0, 
                        'operator': current_user, 'update_time': current_time
                    }
                }
                with st.spinner("補登中..."):
                    save_ordered_data(date_str, adhoc_dict)
                    batch_update_record_qty(date_str, {ad_cart_key: ad_hoc_qty}, current_user, current_time)
                
                st.success(f"✅ {ad_name} 補登成功！")
                st.rerun()
