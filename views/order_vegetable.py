import streamlit as st
import pandas as pd
import datetime
import urllib.parse
from record_engine import get_gspread_client, SHEET_NAME

# ==========================================
# ☁️ Google Sheets 叫菜資料庫專用引擎
# ==========================================
def get_veg_db():
    """讀取廠商與菜品主檔 (只增不減)"""
    client = get_gspread_client()
    if not client: return pd.DataFrame(columns=["vendor", "item_name", "unit"])
    try:
        sp = client.open(SHEET_NAME)
        try:
            sheet = sp.worksheet("叫菜廠商菜品庫")
        except:
            sheet = sp.add_worksheet(title="叫菜廠商菜品庫", rows="1000", cols="5")
            sheet.append_row(["vendor", "item_name", "unit"])
        records = sheet.get_all_records()
        return pd.DataFrame(records) if records else pd.DataFrame(columns=["vendor", "item_name", "unit"])
    except Exception as e:
        st.error(f"連線菜品庫失敗: {e}")
        return pd.DataFrame(columns=["vendor", "item_name", "unit"])

def add_veg_item_to_cloud(vendor, item_name, unit):
    """新增廠商與菜品至雲端 (人員無刪除權限)"""
    client = get_gspread_client()
    if not client: return False
    try:
        sp = client.open(SHEET_NAME)
        sheet = sp.worksheet("叫菜廠商菜品庫")
        sheet.append_row([str(vendor).strip(), str(item_name).strip(), str(unit).strip()])
        return True
    except Exception as e:
        st.error(f"新增菜品至雲端失敗: {e}")
        return False

def save_veg_order_to_cloud(order_record):
    """保存下單歷史紀錄"""
    client = get_gspread_client()
    if not client: return False
    try:
        sp = client.open(SHEET_NAME)
        try:
            sheet = sp.worksheet("叫菜歷史訂單")
        except:
            sheet = sp.add_worksheet(title="叫菜歷史訂單", rows="1000", cols="8")
            sheet.append_row(["order_time", "operator", "vendor", "delivery_date", "items_summary", "note"])
        
        sheet.append_row([
            order_record["order_time"],
            order_record["operator"],
            order_record["vendor"],
            order_record["delivery_date"],
            order_record["items_summary"],
            order_record["note"]
        ])
        return True
    except Exception as e:
        st.error(f"訂單記錄寫入失敗: {e}")
        return False

# ==========================================
# 🥬 叫菜系統前端介面
# ==========================================
def show():
    current_user = st.session_state.get("user_name", "門市後台")
    st.markdown("#### 🥬 潘大廚 - 門市每日叫菜作業")
    
    # 讀取雲端已建立的廠商與菜品
    df_veg = get_veg_db()
    existing_vendors = df_veg["vendor"].dropna().unique().tolist() if not df_veg.empty else []

    # ------------------------------------------
    # 區塊 1：廠商選擇與新廠商建立
    # ------------------------------------------
    col_v1, col_v2 = st.columns([3, 2])
    with col_v1:
        vendor_options = ["＋【新增廠商】"] + existing_vendors if existing_vendors else ["＋【新增廠商】"]
        selected_vendor = st.selectbox("🏬 選擇菜商 (廠商名稱)", vendor_options)
    
    # 如果選擇新增廠商，或是第一次使用
    new_vendor_name = ""
    if selected_vendor == "＋【新增廠商】":
        with col_v2:
            new_vendor_name = st.text_input("✍️ 輸入新菜商名稱", placeholder="例：阿發蔬菜行")

    current_vendor = new_vendor_name.strip() if selected_vendor == "＋【新增廠商】" else selected_vendor

    # ------------------------------------------
    # 區塊 2：建立該廠商的新菜品 (人員只增不減)
    # ------------------------------------------
    with st.expander(f"➕ 為【{current_vendor if current_vendor else '廠商'}】新增常態菜品與計價單位"):
        col_c1, col_c2, col_c3 = st.columns([3, 2, 2])
        with col_c1:
            add_item_name = st.text_input("菜品名稱", placeholder="例如：高麗菜(初秋)")
        with col_c2:
            add_unit = st.text_input("單位", placeholder="例如：斤 / 顆 / 箱")
        with col_c3:
            st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
            if st.button("💾 存入菜品庫", use_container_width=True):
                if not current_vendor:
                    st.error("請先輸入或選擇廠商名稱！")
                elif not add_item_name.strip() or not add_unit.strip():
                    st.error("菜品名稱與單位皆不能為空！")
                else:
                    if add_veg_item_to_cloud(current_vendor, add_item_name, add_unit):
                        st.success(f"✅ 已成功將【{add_item_name}】加入【{current_vendor}】的菜品清單！")
                        st.rerun()

    # 取得目前所選廠商專屬的菜品列表
    vendor_items = []
    unit_map = {}
    if not df_veg.empty and current_vendor in df_veg["vendor"].values:
        v_df = df_veg[df_veg["vendor"] == current_vendor]
        vendor_items = v_df["item_name"].tolist()
        unit_map = dict(zip(v_df["item_name"], v_df["unit"]))

    st.divider()

    # ------------------------------------------
    # 區塊 3：15 格下單清單
    # ------------------------------------------
    st.markdown("##### 📋 叫菜清單 (預設 15 格採購單)")
    
    item_choice_list = ["(無)"] + vendor_items + ["✏️ 自訂臨時菜品"]

    orders_to_send = []

    # 建立 15 格欄位
    for i in range(15):
        c1, c2, c3, c4 = st.columns([1, 4, 3, 2])
        with c1:
            st.markdown(f"<p style='margin-top:10px; color:#888; text-align:center;'>#{i+1}</p>", unsafe_allow_html=True)
        with c2:
            item_sel = st.selectbox(f"品項 #{i+1}", item_choice_list, key=f"veg_item_{i}", label_visibility="collapsed")
        
        final_item_name = ""
        default_unit = ""
        
        if item_sel == "✏️ 自訂臨時菜品":
            with c3:
                final_item_name = st.text_input(f"自訂品名 #{i+1}", key=f"custom_name_{i}", placeholder="手打品名", label_visibility="collapsed")
            with c4:
                default_unit = st.text_input(f"自訂單位 #{i+1}", key=f"custom_unit_{i}", placeholder="單位", label_visibility="collapsed")
        elif item_sel != "(無)":
            final_item_name = item_sel
            default_unit = unit_map.get(item_sel, "斤")
            with c3:
                st.markdown(f"<p style='margin-top:8px; font-weight:bold; color:#00C853;'>{final_item_name}</p>", unsafe_allow_html=True)
            with c4:
                st.markdown(f"<p style='margin-top:8px; color:#aaa;'>單位: {default_unit}</p>", unsafe_allow_html=True)
        else:
            with c3:
                st.markdown("<p style='margin-top:8px; color:#444;'>-</p>", unsafe_allow_html=True)
            with c4:
                st.markdown("<p style='margin-top:8px; color:#444;'>-</p>", unsafe_allow_html=True)

        # 數量輸入
        qty = 0
        if final_item_name:
            col_q, _ = st.columns([2, 8])
            with col_q:
                qty = st.number_input(f"數量", min_value=0, step=1, key=f"veg_qty_{i}", label_visibility="collapsed")
            if qty > 0:
                orders_to_send.append({
                    "item": final_item_name,
                    "qty": qty,
                    "unit": default_unit
                })

    st.divider()

    # ------------------------------------------
    # 區塊 4：希望到貨日期與備註
    # ------------------------------------------
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        delivery_date = st.date_input("🗓️ 希望到貨日期", value=tomorrow)
        weekdays = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
        delivery_str = f"{delivery_date.strftime('%Y-%m-%d')} ({weekdays[delivery_date.weekday()]})"
    with col_d2:
        order_note = st.text_input("📝 備註需求 (例如：請於早晨 07:30 前送達後門)")

    # ------------------------------------------
    # 區塊 5：生成 LINE 訂單並一鍵發送
    # ------------------------------------------
    if st.button("🚀 產生叫菜訂單並發送 LINE", type="primary", use_container_width=True):
        if not current_vendor:
            st.error("請確認已填寫或選擇廠商名稱！")
        elif not orders_to_send:
            st.warning("⚠️ 您尚未在 15 格欄位中填寫任何叫菜數量！")
        else:
            # 組裝 LINE 文字
            line_msg = f"🥬 【潘大廚 - 門市叫菜單】\n"
            line_msg += f"🏬 廠商：{current_vendor}\n"
            line_msg += f"🗓️ 希望到貨日：{delivery_str}\n"
            line_msg += f"👨‍🍳 訂購人員：{current_user}\n"
            line_msg += f"──────────────────\n"
            line_msg += f"📋 【訂購明細】：\n"
            
            summary_list = []
            for idx, order in enumerate(orders_to_send, 1):
                item_line = f"{idx}. {order['item']} ➜ {order['qty']} {order['unit']}"
                line_msg += f"{item_line}\n"
                summary_list.append(f"{order['item']}*{order['qty']}{order['unit']}")
                
            line_msg += f"──────────────────\n"
            if order_note.strip():
                line_msg += f"💡 【備註】：{order_note.strip()}\n"
            line_msg += f"請廠商確認收到並回覆，感謝配合！"

            # 存入 Google Sheets 歷史訂單
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_veg_order_to_cloud({
                "order_time": now_str,
                "operator": current_user,
                "vendor": current_vendor,
                "delivery_date": delivery_str,
                "items_summary": ", ".join(summary_list),
                "note": order_note
            })

            # 產生 LINE 外部跳轉連結
            encoded_msg = urllib.parse.quote(line_msg)
            line_url = f"https://line.me/R/msg/text/?{encoded_msg}"

            st.session_state["veg_line_msg"] = line_msg
            st.session_state["veg_line_url"] = line_url
            st.rerun()

    # 顯示發送介面
    if st.session_state.get("veg_line_msg"):
        st.success("✅ 叫菜單已成功建檔並存入雲端試算表！")
        st.link_button("📲 打開手機 LINE 直接發送至廠商群組", url=st.session_state["veg_line_url"], type="primary", use_container_width=True)
        st.info("💻 電腦版可直接複製下方訊息貼至 LINE：")
        st.code(st.session_state["veg_line_msg"], language="text")
        if st.button("關閉此訂單提示", use_container_width=True):
            del st.session_state["veg_line_msg"]
            del st.session_state["veg_line_url"]
            st.rerun()
