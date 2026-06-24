import streamlit as st
import pandas as pd
import datetime
import urllib.parse
import json
import os
from data_engine import load_sales_data
from record_engine import save_ordered_data, load_daily_record, batch_update_record_qty
from bom_engine import calculate_bom

# --- 存放系統設定的檔案路徑 ---
TEMPLATE_FILE = "sashimi_menu_template.json" # 記住打勾了哪些商品
CUSTOM_ITEMS_FILE = "sashimi_custom_items.json" # 記住手動新增了哪些「新商品」

# ==========================================
# 輔助函數：讀取與儲存設定
# ==========================================
def load_menu_template():
    if os.path.exists(TEMPLATE_FILE):
        try:
            with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return None
    return None

def save_menu_template(item_ids):
    with open(TEMPLATE_FILE, "w", encoding="utf-8") as f:
        json.dump(item_ids, f, ensure_ascii=False)

def load_custom_items():
    if os.path.exists(CUSTOM_ITEMS_FILE):
        try:
            with open(CUSTOM_ITEMS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return []
    return []

def save_custom_items(items):
    with open(CUSTOM_ITEMS_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False)

# ==========================================
# 主畫面邏輯
# ==========================================
def show():
    current_user = st.session_state.get("user_name", "未知操作員")
    
    st.markdown("### 🔪 生魚片部 - 專屬工作區")
    st.markdown("<p style='color: #888; margin-top: -10px; font-size: 14px;'>請直接在表格的【預估數量】或【實際出餐】欄位中輸入數字。</p>", unsafe_allow_html=True)
    
    # 1. 讀取 ERP 正規資料
    df, _ = load_sales_data()
    if df.empty:
        st.warning("⚠️ 無法讀取 ERP 商品資料。")
        return
        
    sashimi_df = df[df['cat'] == '生魚片'].copy()

    # 2. 讀取「手動新增」的新產品，並無縫合併到清單中
    custom_items = load_custom_items()
    if custom_items:
        custom_df = pd.DataFrame(custom_items)
        custom_df['cat'] = '生魚片'
        custom_df['wd_avg'] = 0.0 # 新產品預設歷史均銷為 0
        # 將自訂商品與 ERP 商品合併
        sashimi_df = pd.concat([sashimi_df, custom_df], ignore_index=True)

    sashimi_df = sashimi_df.sort_values(by='item_id') 

    tab_plan, tab_report = st.tabs(["📝 1. 早班預估出餐", "✅ 2. 下午實際回報"])

    # ==========================================
    # 分頁 1：早班預估出餐
    # ==========================================
    with tab_plan:
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
        
        # ------------------------------------------
        # 🌟 系統設定中心 (白名單過濾 + 新增永久商品)
        # ------------------------------------------
        all_item_options = (sashimi_df['item_id'] + " - " + sashimi_df['name']).tolist()
        
        active_item_ids = load_menu_template()
        if active_item_ids is None:
            active_item_ids = sashimi_df['item_id'].tolist()
            
        current_default_options = sashimi_df[sashimi_df['item_id'].isin(active_item_ids)]['item_id'] + " - " + sashimi_df[sashimi_df['item_id'].isin(active_item_ids)]['name']
        current_default_options = current_default_options.tolist()
        
        with st.expander("⚙️ 系統設定：自訂常態菜單 & 新增未建檔商品"):
            st.markdown("#### 1️⃣ 隱藏 / 顯示現有商品")
            st.markdown("<span style='font-size:12px;color:#888;'>在此移除的品項只會從下方表格隱藏，讓畫面更乾淨。</span>", unsafe_allow_html=True)
            selected_options = st.multiselect(
                "選擇這個月常態出餐的商品：",
                options=all_item_options,
                default=current_default_options,
                label_visibility="collapsed"
            )
            if st.button("💾 更新顯示表格", use_container_width=True):
                new_active_ids = [opt.split(" - ")[0] for opt in selected_options]
                save_menu_template(new_active_ids)
                st.success("✅ 菜單已更新！")
                st.rerun()

            st.divider()
            
            # --- 核心新功能：永久加入新商品 ---
            st.markdown("#### 2️⃣ 新增「ERP 尚未建檔」的新產品")
            st.markdown("<span style='font-size:12px;color:#888;'>在此新增的商品會**永久**加入系統中，並出現在上方的選單裡。</span>", unsafe_allow_html=True)
            col_id, col_name, col_btn = st.columns([2, 4, 2])
            with col_id: new_c_id = st.text_input("自訂編號 (選填)", placeholder="例: N001")
            with col_name: new_c_name = st.text_input("新商品名稱 (必填)", placeholder="例: 炙燒特選黑鮪")
            with col_btn:
                st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
                if st.button("➕ 永久加入系統", type="primary", use_container_width=True):
                    if not new_c_name.strip():
                        st.error("商品名稱不能為空！")
                    else:
                        # 產生專屬 ID，避免跟 ERP 撞名
                        final_id = new_c_id.strip() if new_c_id.strip() else f"NEW_{int(datetime.datetime.now().timestamp())}"
                        
                        # 1. 存入新產品資料庫
                        c_list = load_custom_items()
                        c_list.append({"item_id": final_id, "name": new_c_name})
                        save_custom_items(c_list)
                        
                        # 2. 自動把它加入「目前顯示的白名單」中
                        active_list = load_menu_template() or []
                        if final_id not in active_list:
                            active_list.append(final_id)
                            save_menu_template(active_list)
                            
                        st.success(f"✅ {new_c_name} 已成功永久加入系統！")
                        st.rerun()
        # ------------------------------------------
        
        display_df = sashimi_df[sashimi_df['item_id'].isin(active_item_ids)].copy()
        
        editor_df = display_df[['item_id', 'name', 'wd_avg']].copy()
        editor_df['預估數量'] = 0
        editor_df = editor_df.rename(columns={'item_id': '編號', 'name': '品名', 'wd_avg': '參考'})
        
        st.markdown(f"#### 📊 出餐計畫表 (共 {len(editor_df)} 項)")
        edited_df = st.data_editor(
            editor_df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "編號": st.column_config.TextColumn("編號", disabled=True),
                "品名": st.column_config.TextColumn("品名", disabled=True),
                "參考": st.column_config.NumberColumn("參考", disabled=True),
                "預估數量": st.column_config.NumberColumn("預估數量 ✍️", min_value=0, step=1, format="%d")
            }
        )
        
        # 臨時單次特製商品 (保留給客製化需求，如"鮭魚不要蔥")
        if "sashimi_temp_items" not in st.session_state:
            st.session_state.sashimi_temp_items = []

        with st.expander("📝 遇到單次客製化需求？點此手動輸入【臨時品項】"):
            st.markdown("<span style='font-size:12px;color:#888;'>此處輸入的商品「只會出現在本次點單」，不會被永久記錄到系統菜單中。</span>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 4, 2])
            with col1: temp_id = st.text_input("編號 (選填)", key="s_temp_id", placeholder="例如: 999")
            with col2: temp_name = st.text_input("品名 (必填)", key="s_temp_name", placeholder="例如: 鮭魚去鱗特製版")
            with col3: temp_qty = st.number_input("數量", min_value=1, step=1, key="s_temp_qty")
            
            if st.button("➕ 加入本次訂單", use_container_width=True):
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
            if st.button("🗑️ 清除客製化清單", size="small"):
                st.session_state.sashimi_temp_items = []
                st.rerun()
            st.markdown("</div><br>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        note = st.text_input("📝 備註事項 (人員排班或特殊交代)", placeholder="例如：切魚-阿君、開魚-阿君...")
        
        if st.button("💾 確認存檔並產生 LINE 指令", type="primary", use_container_width=True):
            valid_items = edited_df[edited_df['預估數量'] > 0]
            
            if valid_items.empty and not st.session_state.sashimi_temp_items:
                st.warning("請至少輸入一項商品的預估數量，或是新增客製化商品！")
            else:
                cart_dict = {}
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                for _, row in valid_items.iterrows():
                    cart_key = f"{row['編號']}_{row['品名']}"
                    cart_dict[cart_key] = {
                        'item_id': row['編號'],
                        'name': row['品名'],
                        'cat': '生魚片',
                        'qty': row['預估數量'],
                        'operator': current_user,  
                        'update_time': current_time 
                    }
                
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
                    st.success(f"✅ 實際生產量已全數批次更新成功！(回報人：{current_user})")
