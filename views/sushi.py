import streamlit as st
import pandas as pd
import datetime
import urllib.parse
from data_engine import load_sales_data
from record_engine import save_ordered_data, load_daily_record, batch_update_record_qty
from bom_engine import calculate_bom

# 🌟 導入雲端設定引擎
from config_engine import load_menu_template, save_menu_template, load_custom_items, save_custom_items, load_subcategories, save_subcategories, load_inventory_tracking, save_inventory_tracking

def show():
    current_user = st.session_state.get("user_name", "未知操作員")
    DEPT_NAME = "壽司" 
    today = datetime.date.today() 
    
    st.markdown("""
    <style>
    @media (max-width: 640px) {
        [data-testid="stHorizontalBlock"] {
            flex-direction: row !important;
            flex-wrap: wrap !important;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="column"] {
            width: calc(50% - 0.5rem) !important;
            flex: 1 1 calc(50% - 0.5rem) !important;
            min-width: calc(50% - 0.5rem) !important;
        }
    }
    div.stButton > button:active {
        background-color: #FF3B3B !important;
        border-color: #FF3B3B !important;
        transform: scale(0.97);
    }
    div.stButton > button:disabled {
        background-color: #555555 !important;
        color: #cccccc !important;
        border: none !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("### 🍣 壽司部 - 專屬工作區")
    
    df, _ = load_sales_data()
    if df.empty:
        st.warning("⚠️ 無法讀取 ERP 商品資料。")
        return
        
    sushi_df = df[df['cat'].str.contains('壽司|熟食|拉沙|沙拉', na=False)].copy()
    if 'price' not in sushi_df.columns: sushi_df['price'] = 0
    sushi_df['price'] = pd.to_numeric(sushi_df['price'], errors='coerce').fillna(0).astype(int)
    
    sushi_df['item_id'] = sushi_df['item_id'].astype(str)
    sushi_df['name'] = sushi_df['name'].astype(str)

    custom_items = load_custom_items(DEPT_NAME)
    if custom_items:
        custom_df = pd.DataFrame(custom_items)
        custom_df['cat'] = '壽司'
        custom_df['wd_avg'] = 0.0 
        custom_df['price'] = 0  
        custom_df['item_id'] = custom_df['item_id'].astype(str) 
        custom_df['name'] = custom_df['name'].astype(str)
        sushi_df = pd.concat([sushi_df, custom_df], ignore_index=True)

    sushi_df = sushi_df.drop_duplicates(subset=['item_id'], keep='last')
    sushi_df = sushi_df.sort_values(by='item_id') 

    try:
        from record_engine import get_worksheet, _get_cloud_dataframe
        sheet = get_worksheet()
        if sheet:
            cloud_df = _get_cloud_dataframe(sheet)
            if not cloud_df.empty and 'price' in cloud_df.columns:
                valid_price_df = cloud_df[pd.to_numeric(cloud_df['price'], errors='coerce') > 0].copy()
                valid_price_df['clean_id'] = valid_price_df['item_id'].astype(str).str.split('_').str[0].str.replace(r'\.0$', '', regex=True)
                valid_price_df = valid_price_df.sort_values(by='date', ascending=True)
                latest_prices = valid_price_df.groupby('clean_id')['price'].last().to_dict()
                
                sushi_df['price'] = sushi_df.apply(
                    lambda row: latest_prices.get(str(row['item_id']), row.get('price', 0)), 
                    axis=1
                )
    except:
        pass
        
    def get_default_subcat(cat_name):
        if "熟食" in str(cat_name) or "拉沙" in str(cat_name) or "沙拉" in str(cat_name):
            return "熟食區"
        return "壽司區"
        
    sushi_df['default_subcat'] = sushi_df['cat'].apply(get_default_subcat)
    subcat_dict = load_subcategories(DEPT_NAME)
    sushi_df['subcat'] = sushi_df.apply(lambda row: subcat_dict.get(str(row['item_id']), row['default_subcat']), axis=1)

    tab_plan, tab_report, tab_stock = st.tabs(["📝 1. 預估出餐", "✅ 2. 實際回報", "📦 3. 原料庫存"])

    # ==========================================
    # 分頁 1：預估出餐
    # ==========================================
    with tab_plan:
        date_options = []
        date_mapping = {} 
        weekdays_tw = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"] 
        
        for i in range(0, 7):
            d = today + datetime.timedelta(days=i)
            wd = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][d.weekday()]
            if i == 0: day_text = "今天"
            elif i == 1: day_text = "明天"
            else: day_text = "預設"
            label = f"{wd} ({day_text}) - {d.strftime('%m/%d')}"
            date_options.append(label)
            date_mapping[label] = d.strftime("%Y-%m-%d")

        selected_date_label = st.selectbox("📌 選擇出餐日期", date_options, key="sushi_plan_date")
        target_date_str = date_mapping[selected_date_label]
        target_dt = datetime.datetime.strptime(target_date_str, "%Y-%m-%d")
        target_date_display = f"{target_date_str} ({weekdays_tw[target_dt.weekday()]})"
        
        st.divider()
        all_item_options = (sushi_df['item_id'] + " - " + sushi_df['name']).tolist()
        
        active_item_ids = load_menu_template(DEPT_NAME)
        if active_item_ids is None: active_item_ids = sushi_df['item_id'].tolist()
        active_item_ids = [str(x) for x in active_item_ids]
        
        with st.expander("⚙️ 系統設定：自訂常態菜單 & 分類設定"):
            st.markdown("#### 1️⃣ 隱藏 / 顯示現有商品")
            with st.form("sushi_menu_filter_form", border=False):
                with st.container(height=200):
                    new_selected_ids = []
                    for idx, opt in enumerate(all_item_options):
                        opt_id = str(opt).split(" - ")[0]
                        is_checked = opt_id in active_item_ids
                        if st.checkbox(str(opt), value=is_checked, key=f"chk_sushi_menu_{opt_id}_{idx}"):
                            new_selected_ids.append(opt_id)
                if st.form_submit_button("💾 儲存顯示設定", use_container_width=True):
                    with st.spinner("寫入中..."):
                        save_menu_template(DEPT_NAME, new_selected_ids)
                    st.success("✅ 菜單已更新！")
                    st.rerun()

            st.divider()
            st.markdown("#### 2️⃣ 商品分類設定 (壽司區 vs 熟食區)")
            display_subcat_df = sushi_df[sushi_df['item_id'].isin(active_item_ids)][['item_id', 'name', 'subcat']].copy()
            
            edited_subcat = st.data_editor(
                display_subcat_df, hide_index=True, use_container_width=True,
                column_config={
                    "item_id": st.column_config.TextColumn("編號", disabled=True),
                    "name": st.column_config.TextColumn("品名", disabled=True),
                    "subcat": st.column_config.SelectboxColumn("所屬類別 ✍️", options=["壽司區", "熟食區"], required=True)
                }
            )
            
            btn_subcat_ph = st.empty()
            if btn_subcat_ph.button("💾 儲存分類標籤", use_container_width=True, key="btn_save_subcat"):
                btn_subcat_ph.button("⏳ 處理中，請勿關閉視窗...", disabled=True, use_container_width=True, key="btn_save_subcat_load")
                new_subcat_dict = dict(zip(edited_subcat['item_id'].astype(str), edited_subcat['subcat']))
                final_subcat_dict = {**subcat_dict, **new_subcat_dict}
                save_subcategories(DEPT_NAME, final_subcat_dict)
                st.success("✅ 分類標籤已更新！")
                st.rerun()

            st.divider()
            st.markdown("#### 3️⃣ 新增「ERP 尚未建檔」的新產品")
            col_id, col_name, col_btn = st.columns([2, 4, 2])
            with col_id: new_c_id = st.text_input("自訂編號 (選填)", key="sushi_new_c_id")
            with col_name: new_c_name = st.text_input("商品名稱 (必填)", key="sushi_new_c_name")
            with col_btn:
                st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
                btn_add_c_ph = st.empty()
                if btn_add_c_ph.button("➕ 加入系統", type="primary", use_container_width=True, key="btn_add_custom"):
                    if not new_c_name.strip():
                        st.error("商品名稱不能為空！")
                    else:
                        btn_add_c_ph.button("⏳ 加入中...", disabled=True, use_container_width=True, key="btn_add_c_load")
                        final_id = new_c_id.strip() if new_c_id.strip() else f"NEW_{int(datetime.datetime.now().timestamp())}"
                        
                        existing_ids = sushi_df['item_id'].values
                        if final_id in existing_ids:
                            st.error(f"❌ 錯誤：編號 '{final_id}' 已存在！")
                        else:
                            c_list = load_custom_items(DEPT_NAME)
                            c_list.append({"item_id": final_id, "name": new_c_name})
                            save_custom_items(DEPT_NAME, c_list)
                            st.success("✅ 新增成功！")
                            st.rerun()
        
        display_df = sushi_df[sushi_df['item_id'].isin(active_item_ids)].copy()
        st.markdown(f"#### 📊 出餐計畫表 (共 {len(display_df)} 項)")
        plan_qty_dict = {} 
        
        for group_name in ["壽司區", "熟食區"]:
            group_df = display_df[display_df['subcat'] == group_name]
            if not group_df.empty:
                icon = "🍣" if group_name == "壽司區" else "🍤"
                st.markdown(f"<h5 style='color:#FFD93D; margin-top:15px;'>{icon} 【{group_name}】</h5>", unsafe_allow_html=True)
                st.markdown('<div class="grid-container">', unsafe_allow_html=True)
                
                for _, row in group_df.iterrows():
                    clean_id = str(row['item_id']).split('_')[0]
                    item_price = int(row.get('price', 0)) 
                    with st.container(border=True):
                        st.markdown(f"""
                        <div style='margin-bottom: 8px;'>
                            <div style='font-size:14px; font-weight:bold; color:white; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;' title='{row['name']}'>
                                {row['name']} <span style='font-size:11px; color:#888; font-weight:normal;'>({clean_id})</span>
                            </div>
                            <div style='font-size:12px; color:#FFD93D; margin-top:2px;'>💰單價: ${item_price}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        plan_qty_dict[row['item_id']] = st.number_input(
                            "數量", min_value=0, step=1, value=0, 
                            key=f"sushi_plan_{row['item_id']}", label_visibility="collapsed"
                        )
                st.markdown('</div>', unsafe_allow_html=True) 

        if "sushi_temp_items" not in st.session_state: st.session_state.sushi_temp_items = []
        with st.expander("📝 客製化需求？手動輸入【單次臨時品項】"):
            col1, col2, col3 = st.columns([2, 4, 2])
            with col1: temp_id = st.text_input("編號 (選填)", key="s_temp_id", placeholder="例如: 999")
            with col2: temp_name = st.text_input("品名 (必填)", key="s_temp_name", placeholder="例如: 綜合壽司去蝦")
            with col3: temp_qty = st.number_input("數量", min_value=1, step=1, key="s_temp_qty")
            if st.button("➕ 加入本次訂單", use_container_width=True, key="sushi_btn_add_temp"):
                if temp_name.strip() != "":
                    st.session_state.sushi_temp_items.append({
                        "item_id": temp_id if temp_id else f"臨時_{len(st.session_state.sushi_temp_items)+1}",
                        "name": f"【客製】{temp_name}", "qty": temp_qty, "subcat": "臨時客製區"
                    })
                    st.rerun()

        if st.session_state.sushi_temp_items:
            st.markdown("<div style='background-color: #332d22; padding: 10px; border-radius: 5px;'>", unsafe_allow_html=True)
            st.markdown("##### 🛒 本次臨時客製清單")
            for idx, item in enumerate(st.session_state.sushi_temp_items):
                st.markdown(f"- {item['name']} ➜ **{item['qty']} 份**")
            if st.button("🗑️ 清除臨時清單", key="sushi_btn_clear_temp"):
                st.session_state.sushi_temp_items = []
                st.rerun()
            st.markdown("</div><br>", unsafe_allow_html=True)

        note = st.text_input("📝 備註事項 (人員排班或特殊交代)", placeholder="例如：壽司台-阿豪...", key="sushi_plan_note")
        
        if st.session_state.get('sushi_plan_msg'):
            st.success(f"✅ {target_date_display} 的出餐計畫已成功存檔！")
            st.link_button("🚀 打開 LINE APP 發送", url=st.session_state['sushi_plan_url'], type="primary", use_container_width=True)
            st.info("💻 **電腦版請點擊右上角複製貼到 LINE：**")
            st.code(st.session_state['sushi_plan_msg'], language="text")
            if st.button("關閉提示", use_container_width=True, key="sushi_close_plan_msg"):
                del st.session_state['sushi_plan_msg']
                del st.session_state['sushi_plan_url']
                st.rerun()
            st.divider()

        btn_plan_ph = st.empty()
        if btn_plan_ph.button("💾 確認存檔並產生 LINE 指令", type="primary", use_container_width=True, key="sushi_btn_save_plan"):
            btn_plan_ph.button("⏳ 存檔中，請勿關閉視窗...", disabled=True, use_container_width=True, key="sushi_btn_save_plan_load")
            
            valid_items = []
            for _, row in display_df.iterrows():
                qty = plan_qty_dict.get(row['item_id'], 0)
                if qty > 0:
                    valid_items.append({'item_id': str(row['item_id']), 'name': row['name'], 'qty': qty, 'price': int(row.get('price', 0)), 'subcat': row['subcat']})
            
            if not valid_items and not st.session_state.sushi_temp_items:
                st.warning("請至少輸入一項商品的數量！")
                st.rerun()
            else:
                cart_dict = {}
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for item in valid_items:
                    cart_key = f"{item['item_id']}_{item['name']}"
                    cart_dict[cart_key] = {
                        'item_id': item['item_id'], 'name': item['name'], 'cat': '壽司',
                        'qty': item['qty'], 'price': item['price'], 'subcat': item['subcat'],
                        'operator': current_user, 'update_time': current_time 
                    }
                for t_item in st.session_state.sushi_temp_items:
                    cart_key = f"{t_item['item_id']}_{t_item['name']}"
                    cart_dict[cart_key] = {
                        'item_id': str(t_item['item_id']), 'name': t_item['name'], 'cat': '壽司',
                        'qty': t_item['qty'], 'price': 0, 'subcat': '臨時客製區',
                        'operator': current_user, 'update_time': current_time
                    }
                
                save_ordered_data(target_date_str, cart_dict)
                
                msg = f"🍣 【阿布潘-壽司部】 🍣\n🗓️ 日期：{target_date_display}\n👨‍💻 人員：{current_user}\n──────────────────\n📋 【預估出餐明細】\n"
                total_plan_qty = 0
                for g_name in ["壽司區", "熟食區", "臨時客製區"]:
                    g_items = [d for k, d in cart_dict.items() if d.get('subcat', '壽司區') == g_name]
                    if g_items:
                        msg += f"\n📁 [{g_name}]\n"
                        for d in g_items:
                            msg += f"🔸 {d['name']} ➜ {d['qty']} 份\n"
                            total_plan_qty += d['qty']
                
                msg += f"\n(今日預估總份數 = {total_plan_qty} 份)\n"
                if note: msg += f"\n──────────────────\n💡 【備註】：\n{note}\n"
                
                st.session_state.sushi_temp_items = []
                st.session_state['sushi_plan_msg'] = msg
                st.session_state['sushi_plan_url'] = f"https://line.me/R/msg/text/?{urllib.parse.quote(msg)}"
                st.rerun()

    # ==========================================
    # 分頁 2：實際回報
    # ==========================================
    with tab_report:
        report_date = st.date_input("📌 選擇回報日期", value=today, key="sushi_report_date")
        date_str = report_date.strftime("%Y-%m-%d")
        report_weekday = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"][report_date.weekday()]
        report_date_display = f"{date_str} ({report_weekday})"
        
        with st.spinner("讀取紀錄中..."):
            df_record = load_daily_record(date_str)
            
        sushi_records = df_record[df_record['cat'] == '壽司'].copy() if not df_record.empty else pd.DataFrame()
        
        if sushi_records.empty:
            st.info(f"該日壽司部尚無任何出餐紀錄。")
        else:
            st.markdown(f"#### 📝 {report_date_display} 實際出餐回報表")
            sushi_records['subcat'] = sushi_records['item_id'].astype(str).map(lambda x: subcat_dict.get(x.split('_')[0], "壽司區"))
            
            actual_updates = {} 
            report_qty_dict = {} 
            
            for group_name in ["壽司區", "熟食區", "臨時客製區"]:
                group_records = sushi_records[sushi_records['subcat'] == group_name]
                if not group_records.empty:
                    icon = "🍣" if group_name == "壽司區" else "🍤" if group_name == "熟食區" else "🛒"
                    st.markdown(f"<h5 style='color:#FFD93D; margin-top:15px;'>{icon} 【{group_name}】</h5>", unsafe_allow_html=True)
                    st.markdown('<div class="grid-container">', unsafe_allow_html=True)
                    
                    for _, row in group_records.iterrows():
                        cart_key = row['cart_key']
                        ordered_qty = int(row['ordered_qty'])
                        original_qty = int(row['actual_qty'])
                        item_price = int(row.get('price', 0)) 
                        
                        with st.container(border=True):
                            clean_id = str(row['item_id']).split('_')[0]
                            st.markdown(f"""
                            <div style='margin-bottom: 8px;'>
                                <div style='font-size:14px; font-weight:bold; color:white; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;' title='{row['name']}'>
                                    {row['name']} <span style='font-size:11px; color:#888; font-weight:normal;'>({clean_id})</span>
                                </div>
                                <div style='font-size:12px; color:#FFD93D; margin-top:2px;'>💰單價: ${item_price} | 預估: <b>{ordered_qty}</b> 份</div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            new_qty = st.number_input(
                                "實際出餐", min_value=0, step=1, value=original_qty, 
                                key=f"sushi_report_{cart_key}", label_visibility="collapsed"
                            )
                            
                            report_qty_dict[cart_key] = {
                                'name': row['name'], 'ordered': ordered_qty, 'actual': new_qty, 'subcat': group_name
                            }
                            
                            if str(original_qty) != str(new_qty):
                                actual_updates[cart_key] = new_qty
                                
                    st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("#### 📦 今日加減量狀態回報")
            status_option = st.radio("狀態：", ["無增減 (如預估)", "今日有加量", "今日有減量", "皆有 (部分加/部分減)"], horizontal=True, key="sushi_report_status")
            report_note = st.text_input("📝 實際回報備註", key="sushi_report_note_input")
            
            if st.session_state.get('sushi_report_msg'):
                st.success(f"✅ 實際生產量已更新！(回報人：{current_user})")
                st.link_button("🚀 打開 LINE APP 發送", url=st.session_state['sushi_report_url'], type="primary", use_container_width=True)
                st.info("💻 **電腦版請點擊右上角複製貼到 LINE：**")
                st.code(st.session_state['sushi_report_msg'], language="text")
                if st.button("關閉提示", key="sushi_close_report_msg", use_container_width=True):
                    del st.session_state['sushi_report_msg']
                    del st.session_state['sushi_report_url']
                    st.rerun()
                st.divider()

            btn_rep_ph = st.empty()
            if btn_rep_ph.button("💾 儲存回報並產生 LINE 指令", type="primary", use_container_width=True, key="sushi_btn_save_report"):
                btn_rep_ph.button("⏳ 回報寫入中，請稍候...", disabled=True, use_container_width=True, key="sushi_btn_save_report_load")
                
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if actual_updates:
                    batch_update_record_qty(date_str, actual_updates, current_user, current_time)
                
                msg = f"🍣 【阿布潘-壽司部】 🍣\n🗓️ 日期：{report_date_display}\n👨‍💻 回報人員：{current_user}\n──────────────────\n📋 【本日實際出餐數量】\n"
                total_o_qty = 0
                total_a_qty = 0
                
                for g_name in ["壽司區", "熟食區", "臨時客製區"]:
                    g_items = {k: d for k, d in report_qty_dict.items() if d['subcat'] == g_name}
                    if g_items:
                        msg += f"\n📁 [{g_name}]\n"
                        green_list = []
                        red_list = []
                        for key, data in g_items.items():
                            o_qty = data['ordered']
                            a_qty = data['actual']
                            total_o_qty += o_qty
                            total_a_qty += a_qty
                            if str(o_qty) == str(a_qty): green_list.append(f"🟢{data['name']}\n　 預估 {o_qty} / 實際 {a_qty}\n")
                            else: red_list.append(f"🔴{data['name']}\n　 預估 {o_qty} / 實際 {a_qty}\n")
                        for green_msg in green_list: msg += green_msg
                        for red_msg in red_list: msg += red_msg
                    
                msg += f"\n(今日總預估 = {total_o_qty} 份 / 總實際 = {total_a_qty} 份)\n"
                msg += f"\n──────────────────\n📦 【今日加減量狀態】\n👉 {status_option}\n"
                if report_note: msg += f"💡 【備註說明】：\n{report_note}\n"
                    
                st.session_state['sushi_report_msg'] = msg
                st.session_state['sushi_report_url'] = f"https://line.me/R/msg/text/?{urllib.parse.quote(msg)}"
                st.rerun()

        st.divider()
        with st.expander("➕ 補登未在預估單上的出餐品項 (下午臨時加出)"):
            all_sushi_options = (sushi_df['item_id'] + " - " + sushi_df['name']).tolist()
            ad_hoc_opt = st.selectbox("選擇臨時加出的品項", all_sushi_options, key="sushi_adhoc_sel")
            ad_hoc_qty = st.number_input("實際出餐數量", min_value=1, step=1, key="sushi_adhoc_qty")
            
            btn_adhoc_ph = st.empty()
            if btn_adhoc_ph.button("➕ 立即補登至今日回報單", use_container_width=True, key="sushi_btn_add_adhoc"):
                btn_adhoc_ph.button("⏳ 補登資料寫入中...", disabled=True, use_container_width=True, key="sushi_btn_add_adhoc_load")
                
                ad_id = ad_hoc_opt.split(" - ")[0]
                ad_name = ad_hoc_opt.split(" - ")[1]
                ad_cart_key = f"{ad_id}_{ad_name}"
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                adhoc_dict = {
                    ad_cart_key: {
                        'item_id': ad_id, 'name': ad_name, 'cat': '壽司',
                        'qty': 0, 'actual_qty': ad_hoc_qty, 
                        'operator': current_user, 'update_time': current_time,
                        'report_operator': current_user, 'report_time': current_time
                    }
                }
                save_ordered_data(date_str, adhoc_dict)
                st.success(f"✅ {ad_name} 補登成功！")
                st.rerun()

    # ==========================================
    # 🌟 分頁 3：原料庫存與待銷品追蹤 (全新雙區塊)
    # ==========================================
    with tab_stock:
        st.markdown("#### 📦 部門庫存與待銷追蹤")
        st.markdown("<p style='font-size:13px; color:#888;'>此清單庫存由 ERP 系統定時自動更新。您可以將原料分為「核心原料」或「待銷品」以利現場管理。</p>", unsafe_allow_html=True)
        
        stock_list = load_inventory_tracking(DEPT_NAME)
        
        if not stock_list:
            st.info("目前尚未設定任何需要追蹤的原料。")
        else:
            # 🌟 動態分區顯示邏輯
            for s_type, s_icon in [("核心原料", "📦"), ("待銷品", "🚨")]:
                filtered_stock = [x for x in stock_list if x.get('stock_cat', '核心原料') == s_type]
                
                if filtered_stock:
                    st.markdown(f"<h5 style='color:#FFD93D; margin-top:15px;'>{s_icon} 【{s_type}】</h5>", unsafe_allow_html=True)
                    st.markdown('<div class="grid-container">', unsafe_allow_html=True)
                    
                    for row in filtered_stock:
                        unit_str = row.get('unit', '')
                        with st.container(border=True):
                            st.markdown(f"""
                            <div style='margin-bottom: 8px;'>
                                <div style='font-size:15px; font-weight:bold; color:white; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;' title='{row['name']}'>
                                    {row['name']} <span style='font-size:12px; color:#888; font-weight:normal;'>({row['item_id']})</span>
                                </div>
                                <div style='font-size:22px; color:#4CAF50; font-weight:bold; margin-top:5px;'>
                                    {row['qty']} <span style='font-size:14px; color:#ccc; font-weight:normal;'>{unit_str}</span>
                                </div>
                                <div style='font-size:11px; color:#888;'>最後更新: {row['time']}</div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            if st.button("🗑️ 移除追蹤", key=f"del_stock_{row['item_id']}", use_container_width=True):
                                new_list = [x for x in stock_list if x['item_id'] != row['item_id']]
                                save_inventory_tracking(DEPT_NAME, new_list)
                                st.rerun()
                                
                    st.markdown('</div>', unsafe_allow_html=True)

        st.divider()
        with st.expander("➕ 新增要追蹤的 ERP 原料"):
            col_id, col_name = st.columns(2)
            with col_id: new_s_id = st.text_input("ERP 原料編號 (必填)", key="stock_new_id")
            with col_name: new_s_name = st.text_input("原料名稱 (必填)", key="stock_new_name")
            
            # 🌟 新增分類選擇鈕
            new_s_cat = st.radio("📌 設定追蹤類別：", ["核心原料", "待銷品"], horizontal=True, key="stock_new_cat")
            
            btn_stock_ph = st.empty()
            if btn_stock_ph.button("➕ 加入追蹤", type="primary", use_container_width=True, key="btn_add_stock"):
                btn_stock_ph.button("⏳ 加入中...", disabled=True, use_container_width=True, key="btn_add_stock_load")
                if not new_s_id.strip() or not new_s_name.strip():
                    st.error("編號與名稱皆不能為空！")
                elif any(x['item_id'] == new_s_id.strip() for x in stock_list):
                    st.warning("此原料已經在追蹤清單中了！")
                else:
                    stock_list.append({
                        "item_id": new_s_id.strip(),
                        "name": new_s_name.strip(),
                        "qty": "等待 ERP 同步...",
                        "unit": "",
                        "time": "尚未更新",
                        "stock_cat": new_s_cat # 🌟 寫入分類
                    })
                    save_inventory_tracking(DEPT_NAME, stock_list)
                    st.success(f"✅ 加入成功！下次 ERP 同步時將抓取 {new_s_cat} 庫存。")
                    st.rerun()
