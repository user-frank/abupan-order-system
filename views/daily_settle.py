import streamlit as st
import pandas as pd
import datetime
from record_engine import get_gspread_client, SHEET_NAME

# ==========================================
# ☁️ Google Sheets 門市日結資料庫引擎 (盲盤版)
# ==========================================
def save_blind_settlement_to_cloud(settle_data):
    """將門市盲盤實點紀錄寫入 Google 試算表"""
    client = get_gspread_client()
    if not client: return False
    try:
        sp = client.open(SHEET_NAME)
        try:
            sheet = sp.worksheet("門市日結對帳表")
        except:
            sheet = sp.add_worksheet(title="門市日結對帳表", rows="1000", cols="12")
            sheet.append_row([
                "settle_date", "store_name", "operator", "submit_time",
                "reserve_cash", "counted_cash", "actual_operating_cash", 
                "pos_total_revenue", "electronic_payment", "system_expected_cash",
                "cash_variance", "status", "note"
            ])
        
        # 門市人員填寫實點數據，POS相關欄位預留待POS轉接或財務帶入
        sheet.append_row([
            settle_data["settle_date"],
            settle_data["store_name"],
            settle_data["operator"],
            settle_data["submit_time"],
            settle_data["reserve_cash"],
            settle_data["counted_cash"],
            settle_data["actual_operating_cash"],
            settle_data.get("pos_total_revenue", 0),
            settle_data.get("electronic_payment", 0),
            settle_data.get("system_expected_cash", 0),
            settle_data.get("cash_variance", 0),
            settle_data.get("status", "待財務對帳"),
            settle_data["note"]
        ])
        return True
    except Exception as e:
        st.error(f"寫入日結紀錄失敗: {e}")
        return False

# ==========================================
# 💰 門市日結現場盲點介面 (純實點回報)
# ==========================================
def show():
    current_user = st.session_state.get("user_name", "門市人員")
    today = datetime.date.today()
    
    st.markdown("#### 💰 門市每日下班現金盤點清點")
    st.caption(f"操作同仁：{current_user} ｜ 每日打烊前確實清點錢櫃現金並如實回報")

    # 選擇日期與門市
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        settle_date = st.date_input("🗓️ 盤點日期", value=today, key="settle_date_input")
        date_str = settle_date.strftime("%Y-%m-%d")
    with col_s2:
        store_name = st.selectbox("🏬 盤點門市", ["潘大廚 - 直營一號店", "直營二號店(籌備中)"])

    st.divider()

    # ------------------------------------------
    # 區塊：現場實際現金清點 (盲點，不展示系統帳面)
    # ------------------------------------------
    st.markdown("##### 💵 【現場現金實點回報】")
    st.info("💡 請現場同仁仔細盤點錢櫃內所有現鈔與零錢，總部系統將於送出後自動核對。")

    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        reserve_cash = st.number_input(
            "抽屜預留零用金底金 (元)", 
            value=5000, 
            step=500, 
            help="找零用固定備用底金"
        )
    with col_c2:
        counted_cash = st.number_input(
            "錢櫃實點現鈔總額 (含底金) (元)", 
            min_value=0, 
            value=0, 
            step=10, 
            help="請將錢櫃裡所有鈔票與硬幣全部清點加總填入"
        )
    with col_c3:
        # 自動計算純營業現金
        actual_operating_cash = max(0, counted_cash - reserve_cash)
        st.markdown("<p style='font-size:12px; color:#888; margin-bottom:2px;'>實收營業現金 (扣除底金)</p>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style='
            background-color: #1A3826; 
            border: 1px solid #00C853; 
            color: #00FF66; 
            font-size: 20px; 
            font-weight: bold; 
            padding: 6px 12px; 
            border-radius: 6px; 
            text-align: center;
        '>NT$ {actual_operating_cash:,}</div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 門市人員專用備註 (零星開銷/特殊狀況)
    settle_note = st.text_input(
        "📝 今日現場支出或備註說明", 
        placeholder="例如：自零用金買冰塊 100 元、換燈泡 150 元、某外送單少收 5 元...等"
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ------------------------------------------
    # 區塊：防連擊上傳與成功反饋
    # ------------------------------------------
    btn_settle_ph = st.empty()
    if btn_settle_ph.button("🔒 確認金額無誤並上傳總部", type="primary", use_container_width=True, key="btn_submit_blind_settle"):
        btn_settle_ph.button("⏳ 數據加密傳輸中，請稍候...", disabled=True, use_container_width=True, key="btn_submit_blind_settle_dis")
        
        if counted_cash == 0:
            st.warning("⚠️ 請確認錢櫃現鈔總額是否已填寫！")
        else:
            submit_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            record_payload = {
                "settle_date": date_str,
                "store_name": store_name,
                "operator": current_user,
                "submit_time": submit_time_str,
                "reserve_cash": int(reserve_cash),
                "counted_cash": int(counted_cash),
                "actual_operating_cash": int(actual_operating_cash),
                "note": settle_note.strip()
            }
            
            if save_blind_settlement_to_cloud(record_payload):
                # 紀錄到 Session State，供介面展示完成狀態
                st.session_state["settle_success_info"] = {
                    "date": date_str,
                    "store": store_name,
                    "time": submit_time_str,
                    "operator": current_user,
                    "cash": actual_operating_cash
                }
                st.rerun()

    # 🌟 成功反饋卡片 (確認同仁知道今天已完成)
    if st.session_state.get("settle_success_info"):
        info = st.session_state["settle_success_info"]
        st.divider()
        st.markdown(f"""
        <div style='
            background-color: #0E2A1A; 
            border: 2px solid #00C853; 
            border-radius: 8px; 
            padding: 16px 20px; 
            margin-top: 10px;
        '>
            <div style='font-size: 18px; font-weight: bold; color: #00FF66; margin-bottom: 6px;'>
                ✅ 【今日現金盤點數據已成功傳輸至總部！】
            </div>
            <div style='font-size: 13px; color: #E0E0E0; line-height: 1.6;'>
                🏬 <b>結算門市：</b>{info['store']}<br>
                🗓️ <b>結算日期：</b>{info['date']}<br>
                💵 <b>回報營業現金：</b>NT$ {info['cash']:,} 元<br>
                👤 <b>盤點同仁：</b>{info['operator']} (傳輸時間：{info['time']})
            </div>
            <div style='margin-top: 10px; font-size: 12px; color: #88C599;'>
                💡 數據已封存送往財務，辛苦了，可以放心完成打烊作業！
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("關閉此完成提示", use_container_width=True):
            del st.session_state["settle_success_info"]
            st.rerun()
