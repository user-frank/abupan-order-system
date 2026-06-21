import streamlit as st
import pandas as pd
import datetime
import urllib.parse
from splash_screen import show_splash_screen 
from data_engine import load_sales_data
from bom_engine import calculate_bom
from record_engine import save_ordered_data, load_daily_record, update_record_qty, delete_order_item, batch_update_record_qty

st.set_page_config(page_title="阿布潘智能出餐系統", page_icon="🐟", layout="wide")

st.markdown("""
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="mobile-web-app-capable" content="yes">
    <link rel="apple-touch-icon" href="https://cdn-icons-png.flaticon.com/512/1046/1046774.png">
    
    <style>
    /* 1. 強制背景變黑 */
    .stApp { background-color: #000000 !important; }
    
    /* 2. 【核心修正】強制文字顏色，確保黑底上清晰 */
    body, p, h1, h2, h3, h4, span, div, li, label, input, button {
        color: #FFFFFF !important; 
    }
    
    /* 3. 專門消滅 Streamlit 官方浮動圖示的 CSS (整合了你提供的精準選擇器) */
    div[data-testid="stStatusWidget"],
    iframe[title="Managed Hosting Toolbar"],
    .stAppDeployButton,
    header, 
    footer,
    #MainMenu {
        display: none !important;
        visibility: hidden !important;
    }
    
    /* 4. 特殊顏色保護：警示與提示色 */
    .sales-text-alert, .stError { color: #FF6B6B !important; }
    .sales-text { color: #FFD93D !important; }
    input { color: #000000 !important; background-color: #FFFFFF !important; }
    div.stButton > button { background-color: #f37021 !important; color: white !important; }
    
    /* 原有 UI 優化 */
    div[data-testid="stImage"] img { height: 220px !important; object-fit: cover !important; border-radius: 8px; }
    .item-id-tag { font-size: 12px; color: #AAAAAA !important; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

if 'has_seen_splash' not in st.session_state: st.session_state.has_seen_splash = False
if not st.session_state.has_seen_splash:
    show_splash_screen()
    st.session_state.has_seen_splash = True
    try: st.rerun()
    except AttributeError: st.experimental_rerun()

if 'cart' not in st.session_state: st.session_state.cart = {} 

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1046/1046774.png", width=80)
    st.title("系統控制台")
    if st.button("🔄 重新讀取最新數據", use_container_width=True, type="primary"):
        load_sales_data.clear() 
        st.session_state.cart = {} 
        st.rerun()

st.title("🐟 阿布潘水產 - 智能決策系統")
st.markdown("<p style='font-size: 14px; color: #888; margin-top: -15px;'>資料來源：正航 ERP 系統同步</p>", unsafe_allow_html=True)
st.divider()

df, error_logs = load_sales_data()

if error_logs:
    with st.expander("⚠️ 系統偵測到部分檔案異常！點擊查看", expanded=True):
        for log in error_logs: st.error(f"📁 **{log['file']}**\n❌ {log['reason']}")

today = datetime.date.today()
date_options = []
date_mapping = {} 
# 保留昨天您要求：讓日期從「今天」開始選的完美設定
for i in range(0, 7):
    d = today + datetime.timedelta(days=i)
    wd = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][d.weekday()]
    if i == 0: day_text = "今天"
    elif i == 1: day_text = "明天"
    else: day_text = "預設"
    label = f"{wd} ({day_text}) - {d.strftime('%m/%d')}"
    date_options.append(label)
    date_mapping[label] = d.strftime("%Y-%m-%d")

def render_product_card(row, key_prefix, is_alert=False):
    with st.container(border=True):
        st.image(row["img"], use_container_width=True)
        st.markdown(f"### {row['name']}")
        st.markdown(f"<div class='item-id-tag'>商品編號: {row['item_id']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='{'sales-text-alert' if is_alert else 'sales-text'}'>{'⚠️' if is_alert else '📊'} 平日歷史均銷: {row['wd_avg']} 份/日</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='{'sales-text-alert' if is_alert else 'sales-text'}'>{'⚠️' if is_alert else '📊'} 假日歷史均銷: {row['we_avg']} 份/日</div>", unsafe_allow_html=True)
        
        cart_key = f"{row['item_id']}_{row['name']}"
        current_item = st.session_state.cart.get(cart_key)
        unique_key = f"{key_prefix}_{row['item_id']}_{row.name}"
        
        if current_item:
            st.success(f"✅ 已排入 (數量: {current_item['qty']} 份)")
            col1, col2 = st.columns([3, 2])
            with col1: new_qty = st.number_input("修改 (0取消)", min_value=0, value=current_item['qty'], step=1, key=f"qty_{unique_key}")
            with col2:
                st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                if st.button("更新", key=f"update_{unique_key}", use_container_width=True):
                    if new_qty == 0: del st.session_state.cart[cart_key]
                    else: st.session_state.cart[cart_key]['qty'] = new_qty
                    st.rerun()
        else:
            col1, col2 = st.columns([3, 2])
            with col1: qty = st.number_input("設定數量", min_value=1, value=10, step=1, key=f"qty_{unique_key}")
            with col2:
                st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                if st.button("➕ 加入", key=f"add_{unique_key}", type="secondary" if is_alert else "primary", use_container_width=True):
                    st.session_state.cart[cart_key] = {'item_id': row['item_id'], 'name': row['name'], 'cat': row['cat'], 'qty': qty}
                    st.rerun()

def generate_line_message(target_date, note):
    msg = f"🐟 【阿布潘營運中心 - 出餐決策指令】 🐟\n🗓️ 目標日期：{target_date}\n──────────────────\n📋 【各部門出餐明細】\n"
    
    # 預先依照部門分類購物車
    dept_carts = {}
    for cart_key, data in st.session_state.cart.items():
        cat = data['cat']
        if cat not in dept_carts: dept_carts[cat] = {}
        dept_carts[cat][cart_key] = data

    # 1. 產生出餐明細 (分部門)
    for cat, d_cart in dept_carts.items():
        msg += f"\n📁 [{cat}]\n"
        for ck, data in d_cart.items():
            msg += f"🔸 {data['name']} (ID:{data['item_id']}) ➜ {data['qty']} 份\n"

    # 2. 產生預估備料需求 (【全新修改】分部門精算)
    msg += "\n──────────────────\n📦 【預估備料需求】\n"
    for cat, d_cart in dept_carts.items():
        msg += f"\n📁 [{cat}] 備料區\n"
        bom_df = calculate_bom(d_cart)
        if not bom_df.empty and '原物料名稱' in bom_df.columns:
            for _, row in bom_df.iterrows(): 
                msg += f"🔹 {row['原物料名稱']} ➜ {row['預估需求量']}\n"
        else: 
            msg += "尚無對應原料設定。\n"
            
    if note: msg += f"\n──────────────────\n💡 【老闆備註/指示】：\n{note}\n"
    return msg

if df.empty:
    st.warning("目前 `sales_data` 資料夾內沒有可成功讀取的數據。")
else:
    categories_list = df['cat'].unique()
    tab3, tab1, tab2, tab_cart, tab_record = st.tabs(["📂 全品項分類瀏覽", "🏆 各部門總排行", "⚠️ 本月銷售倒數排行", f"🛒 出餐表與總計", "📝 營運比對與回報"])

    with tab1:
        col1, _ = st.columns([1, 3])
        with col1: selected_cat_top = st.selectbox("📌 選擇部門 (總排行)", categories_list, key="cat_top")
        st.subheader(f"📈 【{selected_cat_top}】歷史總銷量前 10 名排行")
        top_df = df[df['cat'] == selected_cat_top].sort_values(by="total_sales", ascending=False).head(10)
        cols = st.columns(2)
        for i, (_, row) in enumerate(top_df.iterrows()):
            with cols[i % 2]: render_product_card(row, "top")

    with tab2:
        col1, _ = st.columns([1, 3])
        with col1: selected_cat_bot = st.selectbox("📌 選擇部門 (本月倒數)", categories_list, key="cat_bot")
        st.subheader(f"📉 【{selected_cat_bot}】本月銷售倒數 10 名排行")
        st.caption("※ 系統自動排除非當季（本月無銷量）商品。")
        bot_df = df[(df['cat'] == selected_cat_bot) & (df['cm_sales'] > 0)].sort_values(by="cm_sales", ascending=True).head(10)
        if bot_df.empty: st.info("該部門本月尚無任何有效銷售數據。")
        else:
            cols = st.columns(2)
            for i, (_, row) in enumerate(bot_df.iterrows()):
                with cols[i % 2]: render_product_card(row, "bot", is_alert=True)

    with tab3:
        col_filter1, col_filter2 = st.columns([1, 1])
        with col_filter1: selected_cat_all = st.selectbox("📌 選擇部門", categories_list, key="cat_all")
        with col_filter2: search_kw = st.text_input("🔍 快速搜尋品名或編號", placeholder="例: 鮭魚 或 80123")
        st.subheader(f"📂 【{selected_cat_all}】品項明細")
        view_mode = st.radio("👀 切換手機瀏覽模式", ["📱 圖文卡片 (適合檢視)", "📋 高效清單 (Excel風格)"], horizontal=True, label_visibility="collapsed")
        st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)
        
        all_df = df[df['cat'] == selected_cat_all]
        if search_kw: all_df = all_df[all_df['name'].str.contains(search_kw, case=False, na=False) | all_df['item_id'].str.contains(search_kw, case=False, na=False)]
        
        if all_df.empty: st.info("找不到符合的商品，請嘗試其他關鍵字。")
        else:
            if view_mode == "📱 圖文卡片 (適合檢視)":
                cols = st.columns(2)
                for i, (_, row) in enumerate(all_df.iterrows()):
                    with cols[i % 2]: render_product_card(row, "all")
            else:
                for i, (_, row) in enumerate(all_df.iterrows()):
                    with st.container(border=True):
                        col_info, col_input, col_btn = st.columns([5, 3, 2], vertical_alignment="center")
                        with col_info: st.markdown(f"**{row['name']}**<br><span style='font-size:12px;color:#888;'>ID: {row['item_id']}</span>", unsafe_allow_html=True)
                        
                        cart_key = f"{row['item_id']}_{row['name']}"
                        current_item = st.session_state.cart.get(cart_key)
                        unique_key = f"list_{row['item_id']}_{row.name}"
                        
                        with col_input:
                            qty_val = current_item['qty'] if current_item else 10
                            qty = st.number_input("數量", min_value=0, value=qty_val, step=1, key=f"qty_{unique_key}", label_visibility="collapsed")
                        with col_btn:
                            if current_item:
                                if st.button("更新", key=f"upd_{unique_key}", use_container_width=True):
                                    if qty == 0: del st.session_state.cart[cart_key]
                                    else: st.session_state.cart[cart_key]['qty'] = qty
                                    st.rerun()
                            else:
                                if st.button("加入", key=f"add_{unique_key}", type="primary", use_container_width=True):
                                    if qty > 0:
                                        st.session_state.cart[cart_key] = {'item_id': row['item_id'], 'name': row['name'], 'cat': row['cat'], 'qty': qty}
                                        st.rerun()

    with tab_cart:
        st.header("🛒 確認今日出餐與各部總計")
        
        if st.session_state.get('show_line_success', False):
            st.success(f"✅ 系統已將單據正式存入資料庫！")
            st.link_button("🚀 點擊這裡打開 LINE 發送至群組", url=st.session_state.line_url, type="primary", use_container_width=True)
            if st.button("返回繼續點單", use_container_width=True):
                st.session_state.show_line_success = False
                st.rerun()
            st.divider()

        if st.session_state.cart:
            st.subheader("🗓️ 1. 決定目標出餐日期")
            target_date_label = st.radio("出餐日期選項", date_options, horizontal=True, label_visibility="collapsed")
            real_date_str = date_mapping[target_date_label]
            st.divider()
            
            # 【全新重構】：將購物車按照部門打包，供後續顯示使用
            dept_carts = {}
            for cart_key, item_data in st.session_state.cart.items():
                cat = item_data['cat']
                if cat not in dept_carts: dept_carts[cat] = {}
                dept_carts[cat][cart_key] = item_data
            
            st.subheader(f"📊 2. 廚房備料總覽 (目標日：{real_date_str})")
            metric_cols = st.columns(len(dept_carts))
            for i, (cat, d_cart) in enumerate(dept_carts.items()):
                total_qty = sum(item['qty'] for item in d_cart.values())
                with metric_cols[i % len(metric_cols)]: st.metric(label=f"部門：{cat}", value=f"{total_qty} 份")
            st.divider()
            
            st.subheader("📋 3. 詳細出餐明細清單")
            for cat, d_cart in dept_carts.items():
                with st.container(border=True):
                    st.markdown(f"#### 📁 {cat} 部門明細")
                    for cart_key, item_data in d_cart.items():
                        st.markdown(f"* **{item_data['name']}** <span style='font-size:12px;color:#6c757d;'>(編號: {item_data['item_id']})</span> —— <span style='color:#f37021; font-size:18px; font-weight:bold;'>{item_data['qty']} 份</span>", unsafe_allow_html=True)
            st.divider()
            
            # 【全新加回與升級】：分部門預估備料需求
            st.subheader("📦 4. 預估備料需求")
            for cat, d_cart in dept_carts.items():
                with st.container(border=True):
                    st.markdown(f"#### 📁 [{cat}] 備料需求")
                    st.dataframe(calculate_bom(d_cart), use_container_width=True, hide_index=True)
            st.divider()
            
            note = st.text_input("📝 老闆交代備註事項", placeholder="例如：這週六有大戶要來，生魚片務必切厚一點！...")
            col_btn1, col_btn2 = st.columns([1, 3])
            with col_btn1:
                st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                if st.button("🗑️ 清空出餐表", use_container_width=True):
                    st.session_state.cart = {}
                    st.rerun()
            with col_btn2:
                st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                if st.button("💾 確認存檔並產生 LINE 指令", type="primary", use_container_width=True):
                    save_ordered_data(real_date_str, st.session_state.cart)
                    line_msg = generate_line_message(target_date_label, note)
                    st.session_state.line_url = f"https://line.me/R/msg/text/?{urllib.parse.quote(line_msg)}"
                    st.session_state.cart = {}
                    st.session_state.show_line_success = True
                    st.rerun()
        elif not st.session_state.get('show_line_success', False):
            st.info("👈 目前出餐表是空的，請前往其他分頁挑選並輸入數量。")

    with tab_record:
        st.header("📝 現場生產回報與營運比對")
        record_date = st.date_input("請選擇要查看或回報的日期", value=today)
        date_str = record_date.strftime("%Y-%m-%d")
        is_past = record_date < today
        
        if is_past: st.error("🔒 【歷史紀錄已鎖定】過去的出餐計畫嚴禁竄改，確保資料真實性。")
        else: st.info("✏️ 您正在檢視今日或未來的單據，請直接修改所有「實際生產」數量，並至最下方點擊【批次儲存】。")
            
        df_record = load_daily_record(date_str)
        if df_record.empty: st.warning(f"目前資料庫中尚未有 {date_str} 的出餐任務紀錄。")
        else:
            record_cats = ["全部 (老闆總覽)"] + list(df_record['cat'].unique())
            selected_record_cat = st.selectbox("📌 篩選部門", record_cats, key=f"rec_cat_{date_str}")
            
            if selected_record_cat != "全部 (老闆總覽)":
                df_record = df_record[df_record['cat'] == selected_record_cat]
                
            if df_record.empty:
                st.info(f"該部門在 {date_str} 沒有出餐紀錄。")
            else:
                # 【全新大腦】：拔除舊版電腦表頭，改用響應式卡片排版
                actual_updates = {}
                
                for i, row in df_record.iterrows():
                    cart_key = row.get('cart_key', f"{row['item_id']}_{row['name']}")
                    clean_item_id = str(row['item_id']).split('_')[0]
                    
                    # 每一筆出餐資料，現在變成一張獨立的高質感卡片
                    with st.container(border=True):
                        st.markdown(f"#### 🍣 {row['name']} <span style='font-size:14px;color:#888;font-weight:normal;'> (ID: {clean_item_id})</span>", unsafe_allow_html=True)
                        
                        # 卡片內部分為左右兩塊，在手機上即使折行也會非常整齊
                        col_info, col_action = st.columns([1, 1])
                        
                        with col_info:
                            st.markdown(f"📦 預定出餐： **{row['ordered_qty']}** 份")
                            st.markdown(f"📊 POS 銷售： <span style='color:#6c757d;'>等候匯入...</span>", unsafe_allow_html=True)
                            
                        with col_action:
                            if is_past:
                                st.markdown(f"✍️ 實際生產： **{row['actual_qty']}** 份")
                                st.markdown("🔒 已鎖定")
                            else:
                                unique_key = f"rec_{date_str}_{cart_key}"
                                # 把輸入框加上明確的標題，讓手機使用者一目了然
                                new_act = st.number_input("✍️ 實際生產數量", min_value=0, value=int(row['actual_qty']), step=1, key=f"act_{unique_key}")
                                actual_updates[cart_key] = new_act
                                
                                st.markdown("<div style='margin-top: 5px;'></div>", unsafe_allow_html=True)
                                if st.button("🗑️ 撤銷此單", key=f"del_{unique_key}", use_container_width=True):
                                    delete_order_item(date_str, cart_key)
                                    st.rerun()

                if not is_past:
                    st.divider()
                    if st.button("💾 批次儲存本頁所有實際生產量", type="primary", use_container_width=True):
                        batch_update_record_qty(date_str, actual_updates)
                        st.success("✅ 實際生產量已全數批次更新成功！")
