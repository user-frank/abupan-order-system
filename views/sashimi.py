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
    
    # 🌟 CSS 黑魔法：強制手機版維持「雙排顯示」
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
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("### 🔪 生魚片部 - 專屬工作區")
    
    df, _ = load_sales_data()
    if df.empty:
        st.warning("⚠️ 無法讀取 ERP 商品資料。")
        return
        
    sashimi_df = df[df['cat'] == '生魚片'].copy()
    if sashimi_df.empty:
        st.info("💡 系統提示：目前 ERP 裡沒有標示為『生魚片』的商品，你可以點擊下方『系統設定』手動新增。")
        
    sashimi_df['item_id'] = sashimi_df['item_id'].astype(str)

    custom_items = load_custom_items(DEPT_NAME)
    if custom_items:
        custom_df = pd.DataFrame(custom_items)
        custom_df['cat'] = '生魚片'
        custom_df['wd_avg'] = 0.0 
        custom_df['price'] = 0  # 確保自訂商品有預設單價
        custom_df['item_id'] = custom_df['item_id'].astype(str) 
        sashimi_df = pd.concat([sashimi_df, custom_df], ignore_index=True)

    sashimi_df = sashimi_df.drop_duplicates(subset=['item_id'], keep='last')
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

        selected_date_label = st.selectbox("📌 選擇出餐日期", date_options, key="sashimi_plan_date")
        target_date_str = date_mapping[selected_date_label]
        
        st.divider()
        
        all_item_options = (sashimi_df['item_id'] + " - " + sashimi_df['name']).tolist()
        
        active_item_ids = load_menu_template(DEPT_NAME)
        if active_item_ids is None:
            active_item_ids = sashimi_df['item_id'].tolist()
        
        active_item_ids = [str(x) for x in active_item_ids]
        
        with st.expander("⚙️ 系統設定：自訂常態菜單 & 新增未建檔商品"):
            st.markdown("#### 1️⃣ 隱藏 / 顯示現有商品")
            with st.form("sashimi_menu_filter_form", border=False):
                with st.container(height=250):
                    new_selected_ids = []
                    for idx, opt in enumerate(all_item_options):
                        opt_id = opt.split(" - ")[0]
                        is_checked = str(opt_id) in active_item_ids
                        
                        if st.checkbox(opt, value=is_checked, key=f"chk_sashimi_menu_{opt_id}_{idx}"):
                            new_selected_ids.append(opt_id)
                            
                if st.form_submit_button("💾 儲存並更新畫面", use_container_width=True):
                    with st.spinner("正在寫入雲端..."):
                        success = save_menu_template(DEPT_NAME, new_selected_ids)
                    if success:
                        st.success("✅ 菜單已成功更新至雲端！")
                        st.rerun()

            st.divider()
            st.markdown("#### 2️⃣ 新增新產品")
            col_id, col_name, col_btn = st.columns([2, 4, 2])
            with col_id: new_c_id = st.text_input("自訂編號 (選填)", placeholder="例: N001", key="sashimi_new_c_id")
            with col_name: new_c_name = st.text_input("新商品名稱 (必填)", placeholder="例: 鮭魚特製拼盤", key="sashimi_new_c_name")
            with col_btn:
                st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
                if st.button("➕ 永久加入系統", type="primary", use_container_width=True, key="btn_sashimi_add_custom"):
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
                            
                            with st.spinner(f"正在將 {new_c_name} 寫入 ..."):
                                success1 = save_custom_items(DEPT_NAME, c_list)
                                
                                active_list = load_menu_template(DEPT_NAME) or []
                                if final_id not in active_list:
                                    active_list.append(final_id)
                                    success2 = save_menu_template(DEPT_NAME, active_list)
                                else:
                                    success2 = True
                                    
                            if success1 and success2:
                                st.success(f"✅ {new_c_name} 已成功！")
                                st.rerun()
        
        display_df = sashimi_df[sashimi_df['item_id'].isin(active_item_ids)].copy()
        
        st.markdown(f"#### 📊 出餐計畫表 (共 {len(display_df)} 項)")
        
        plan_qty_dict = {} 
        cols = st.columns(2) 
        
        for idx, (_, row) in enumerate(display_df.iterrows()):
            with cols[idx % 2]:
                with st.container(border=True):
                    clean_id = str(row['item_id']).split('_')[0]
                    # 🌟 加上 .get('price', 0) 完美防當機！
                    item_price = int(row.get('price', 0)) 
                    
                    st.markdown(f"<div style='font-size:14px; font-weight:bold; color:white; margin-bottom:2px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;' title='{row['name']}'>{row['name']} <span style='font-size:11px; color:#888; font-weight:normal;'>({clean_id})</span></div><div style='font-size:12px; color:#FFD93D; margin-bottom:5px;'>💰單價: ${item_price}</div>", unsafe_allow_html=True)
                    
                    plan_qty_dict[row['item_id']] = st.number_input(
                        "數量", min_value=0, step=1, value=0, 
                        key=f"sashimi_plan_{row['item_id']}", label_visibility="collapsed"
                    )

        if "sashimi_temp_items" not in st.session_state:
            st.session_state.sashimi_temp_items = []

        with st.expander("📝 客製化需求？手動輸入【單次臨時品項】"):
            col1, col2, col3 = st.columns([2, 4, 2])
            with col1: temp_id = st.text_input("編號 (選填)", key="sashimi_temp_id", placeholder="例如: 999")
            with col2: temp_name = st.text_input("品名 (必填)", key="sashimi_temp_name", placeholder="例如: 鮭魚去鱗特製版")
            with col3: temp_qty = st.number_input("數量", min_value=1, step=1, key="sashimi_temp_qty")
            
            if st.button("➕ 加入本次訂單", use_container_width=True, key="sashimi_btn_add_temp"):
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
            st.markdown("##### 🛒 本次臨時客製清單")
            for idx, item in enumerate(st.session_state.sashimi_temp_items):
                st.markdown(f"- {item['name']} ➜ **{item['qty']} 份**")
            if st.button("🗑️ 清除臨時清單", size="small", key="sashimi_btn_clear_temp"):
                st.session_state.sashimi_temp_items = []
                st.rerun()
            st.markdown("</div><br>", unsafe_allow_html=True)

        note = st.text_input("📝 備註事項 (人員排班或特殊交代)", placeholder="例如：切魚-阿君...", key="sashimi_plan_note")
        
        # ==========================================
        # 持久化的 LINE 成功訊息區塊
        # ==========================================
        if st.session_state.get('sashimi_plan_msg'):
            st.success(f"✅ {target_date_str} 的出餐計畫已成功存檔！")
            
            st.link_button("🚀 打開 LINE APP 發送 (手機專用)", url=st.session_state['sashimi_plan_url'], type="primary", use_container_width=True)
            st.info("💻 **電腦版操作：請點擊下方框框右上角的「複製圖示」，並貼到 LINE 群組。**")
            st.code(st.session_state['sashimi_plan_msg'], language="text")
            
            if st.button("關閉提示訊息", use_container_width=True, key="sashimi_close_plan_msg"):
                del st.session_state['sashimi_plan_msg']
                del st.session_state['sashimi_plan_url']
                st.rerun()
            st.divider()

        if st.button("💾 確認存檔並產生 LINE 指令", type="primary", use_container_width=True, key="sashimi_btn_save_plan"):
            valid_items = []
            for _, row in display_df.iterrows():
                qty = plan_qty_dict.get(row['item_id'], 0)
                if qty > 0:
                    item_price = int(row.get('price', 0))
                    valid_items.append({'item_id': str(row['item_id']), 'name': row['name'], 'qty': qty, 'price': item_price})
            
            if not valid_items and not st.session_state.sashimi_temp_items:
                st.warning("請至少輸入一項商品的預估數量，或是新增客製化商品！")
            else:
                cart_dict = {}
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                for item in valid_items:
                    cart_key = f"{item['item_id']}_{item['name']}"
                    cart_dict[cart_key] = {
                        'item_id': item['item_id'], 'name': item['name'], 'cat': '生魚片',
                        'qty': item['qty'], 'price': item['price'],
                        'operator': current_user, 'update_time': current_time 
                    }
                
                for temp_item in st.session_state.sashimi_temp_items:
                    cart_key = f"{temp_item['item_id']}_{temp_item['name']}"
                    cart_dict[cart_key] = {
                        'item_id': str(temp_item['item_id']), 'name': temp_item['name'], 'cat': '生魚片',
                        'qty': temp_item['qty'], 'price': 0, 
                        'operator': current_user, 'update_time': current_time
                    }
                
                with st.spinner("訂單存檔中..."):
                    save_ordered_data(target_date_str, cart_dict)
                
                msg = f"🔪 【阿布潘-生魚片部】 🐟\n🗓️ 出餐日期：{target_date_str}\n👨‍💻 填表人員：{current_user}\n──────────────────\n📋 【預估出餐明細】\n"
                
                total_plan_qty = 0
                for _, data in cart_dict.items():
                    msg += f"🔸 {data['name']} ➜ {data['qty']} 份\n"
                    total_plan_qty += data['qty']
                
                msg += f"(今日預估總份數 = {total_plan_qty} 份)\n"
                
                msg += "\n──────────────────\n📦 【預估備料需求】\n"
                bom_df = calculate_bom(cart_dict)
                if not bom_df.empty and '原物料名稱' in bom_df.columns:
                    for _, r in bom_df.iterrows(): msg += f"🔹 {r['原物料名稱']} ➜ {r['預估需求量']}\n"
                else: msg += "尚無對應原料設定。\n"
                if note: msg += f"\n──────────────────\n💡 【備註】：\n{note}\n"
                
                st.session_state.sashimi_temp_items = []
                st.session_state['sashimi_plan_msg'] = msg
                st.session_state['sashimi_plan_url'] = f"https://line.me/R/msg/text/?{urllib.parse.quote(msg)}"
                st.rerun()

    # ==========================================
    # 分頁 2：實際回報
    # ==========================================
    with tab_report:
        report_date = st.date_input("📌 選擇回報日期", value=today, key="sashimi_report_date")
        date_str = report_date.strftime("%Y-%m-%d")
        
        with st.spinner("讀取回報紀錄中..."):
            df_record = load_daily_record(date_str)
            
        sashimi_records = df_record[df_record['cat'] == '生魚片'].copy() if not df_record.empty else pd.DataFrame()
        
        if sashimi_records.empty:
            st.info(f"該日生魚片部尚無任何出餐紀錄。")
        else:
            st.markdown(f"#### 📝 {date_str} 實際出餐回報表")
            
            actual_updates = {} 
            report_qty_dict = {} 
            
            cols = st.columns(2)
            for idx, (_, row) in enumerate(sashimi_records.iterrows()):
                cart_key = row['cart_key']
                ordered_qty = int(row['ordered_qty'])
                original_qty = int(row['actual_qty'])
                item_price = int(row.get('price', 0)) # 🌟 安全抓取單價
                
                with cols[idx % 2]:
                    with st.container(border=True):
                        clean_id = str(row['item_id']).split('_')[0]
                        st.markdown(f"<div style='font-size:14px; font-weight:bold; color:white; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>{row['name']} <span style='font-size:11px; color:#888; font-weight:normal;'>({clean_id})</span></div><div style='color:#FFD93D; font-size:12px; margin-bottom:3px;'>💰單價: ${item_price} | 預估: <b>{ordered_qty}</b> 份</div>", unsafe_allow_html=True)
                        
                        new_qty = st.number_input(
                            "實際出餐", min_value=0, step=1, value=original_qty, 
                            key=f"sashimi_report_{cart_key}", label_visibility="collapsed"
                        )
                        
                        report_qty_dict[cart_key] = {
                            'name': row['name'],
                            'ordered': ordered_qty,
                            'actual': new_qty
                        }
                        
                        if str(original_qty) != str(new_qty):
                            actual_updates[cart_key] = new_qty
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            st.markdown("#### 📦 今日加減量狀態回報")
            status_option = st.radio(
                "請選擇今日出餐總結狀態：", 
                ["無增減 (如預估)", "今日有加量", "今日有減量", "皆有 (部分加/部分減)"], 
                horizontal=True,
                key="sashimi_report_status"
            )
            report_note = st.text_input("📝 實際回報備註 (特殊狀況說明)", placeholder="例如：提早賣完...", key="sashimi_report_note_input")
            
            if st.session_state.get('sashimi_report_msg'):
                st.success(f"✅ 實際生產量已更新！(回報人：{current_user})")
                st.link_button("🚀 打開 LINE APP 發送 (手機專用)", url=st.session_state['sashimi_report_url'], type="primary", use_container_width=True)
                st.info("💻 **電腦版操作：請點擊下方框框右上角的「複製圖示」，並貼到 LINE 群組。**")
                st.code(st.session_state['sashimi_report_msg'], language="text")
                if st.button("關閉提示訊息", key="sashimi_close_report_msg", use_container_width=True):
                    del st.session_state['sashimi_report_msg']
                    del st.session_state['sashimi_report_url']
                    st.rerun()
                st.divider()

            if st.button("💾 儲存回報並產生 LINE 指令", type="primary", use_container_width=True, key="sashimi_btn_save_report"):
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                if actual_updates:
                    with st.spinner("儲存回報中..."):
                        batch_update_record_qty(date_str, actual_updates, current_user, current_time)
                
                msg = f"🔪 【阿布潘-生魚片部】 🐟\n🗓️ 出餐日期：{date_str}\n👨‍💻 回報人員：{current_user}\n──────────────────\n📋 【本日實際出餐數量】\n"
                
                green_list = []
                red_list = []
                total_o_qty = 0
                total_a_qty = 0
                
                for key, data in report_qty_dict.items():
                    o_qty = data['ordered']
                    a_qty = data['actual']
                    
                    total_o_qty += o_qty
                    total_a_qty += a_qty
                    
                    if str(o_qty) == str(a_qty):
                        green_list.append(f"🟢{data['name']}\n　 預估出餐 {o_qty} 份 / 實際 {a_qty} 份\n")
                    else:
                        red_list.append(f"🔴{data['name']}\n　 預估出餐 {o_qty} 份 / 實際 {a_qty} 份\n")
                
                for green_msg in green_list:
                    msg += green_msg
                for red_msg in red_list:
                    msg += red_msg
                    
                msg += f"\n(今日總預估 = {total_o_qty} 份 / 總實際 = {total_a_qty} 份)\n"
                    
                msg += f"\n──────────────────\n📦 【今日加減量狀態】\n👉 {status_option}\n"
                
                if report_note:
                    msg += f"💡 【備註說明】：\n{report_note}\n"
                    
                st.session_state['sashimi_report_msg'] = msg
                st.session_state['sashimi_report_url'] = f"https://line.me/R/msg/text/?{urllib.parse.quote(msg)}"
                st.rerun()

        st.divider()
        with st.expander("➕ 補登未在預估單上的出餐品項 (下午臨時加出)"):
            all_sashimi_options = (sashimi_df['item_id'] + " - " + sashimi_df['name']).tolist()
            ad_hoc_opt = st.selectbox("選擇臨時加出的品項", all_sashimi_options, key="sashimi_adhoc_sel")
            ad_hoc_qty = st.number_input("實際出餐數量", min_value=1, step=1, key="sashimi_adhoc_qty")
            
            if st.button("➕ 立即補登至今日回報單", use_container_width=True, key="sashimi_btn_add_adhoc"):
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
