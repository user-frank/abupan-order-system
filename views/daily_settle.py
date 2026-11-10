import streamlit as st
import pandas as pd
import datetime
from record_engine import get_gspread_client, SHEET_NAME

# ==========================================
# ☁️ Google Sheets 門市日結資料庫引擎
# ==========================================
def save_daily_settlement_to_cloud(settle_data):
    """將日結對帳紀錄寫入 Google 試算表"""
    client = get_gspread_client()
    if not client: return False
    try:
        sp = client.open(SHEET_NAME)
        try:
            sheet = sp.worksheet("門市日結對帳表")
        except:
            sheet = sp.add_worksheet(title="門市日結對帳表", rows="1000", cols="12")
            sheet.append_row([
                "settle_date", "store_name", "operator", "pos_total_revenue", 
                "electronic_payment", "system_expected_cash", "reserve_cash", 
                "counted_cash", "actual_operating_cash", "cash_variance", "status", "note"
            ])
        
        sheet.append_row([
            settle_data["settle_date"],
            settle_data["store_name"],
            settle_data["operator"],
            settle_data["pos_total_revenue"],
            settle_data["electronic_payment"],
            settle_data["system_expected_cash"],
            settle_data["reserve_cash"],
            settle_data["counted_cash"],
            settle_data["actual_operating_cash"],
            settle_data["cash_variance"],
            settle_data["status"],
            settle_data["note"]
        ])
        return True
    except Exception as e:
        st.error(f"寫入日結紀錄失敗: {e}")
        return False

# ==========================================
# 💰 門市日結對帳前端介面
# ==========================================
def show():
    current_user = st.session_state.get("user_name", "門市人員")
    today = datetime.date.today()
    
    st.markdown("#### 💰 門市每日下班日結與現金清點")
    st.caption(f"操作同仁：{current_user} ｜ 嚴格執行日結防弊程序，差額超過 ±100 元將自動通報財務與總裁室")

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        settle_date = st.date_input("🗓️ 日結結算日期", value=today, key="settle_date_input")
        date_str = settle_date.strftime("%Y-%m-%d")
    with col_s2:
        store_name = st.selectbox("🏬 結算門市", ["潘大廚 - 直營一號店", "直營二號店(籌備中)"])

    st.divider()

    # ------------------------------------------
    # 區塊 1：系統自動帶入 (未來由 POS 自動轉接)
    # ------------------------------------------
    st.markdown("##### 🖥️ 【系統應有帳面金額】(由 POS 系統串接帶入)")
    col_p1, col_p2, col_p3 = st.columns(3)
    
    with col_p1:
        # 目前為預留值，後續直接串接 POS
        pos_total = st.number_input("當日 POS 總營業額 (元)", value=68500, step=100, help="未來由 POS 機 API 自動轉接帶入")
    with col_p2:
        electronic_pay = st.number_input("電子支付 / 信用卡總額 (元)", value=21300, step=100, help="LinePay、悠遊卡、外送平台等非現金總額")
    with col_p3:
        # 系統應有現金 = 總營業額 - 電子支付
        system_expected_cash = pos_total - electronic_pay
        st.metric(label="💡 系統應收營業現金", value=f"NT$ {system_expected_cash:,}")

    st.divider()

    # ------------------------------------------
    # 區塊 2：門市後台現場手動清點盤點
    # ------------------------------------------
    st.markdown("##### 💵 【現場實際現金清點】(現場同仁下班盤點)")
    col_c1, col_c2, col_c3 = st.columns(3)
    
    with col_c1:
        reserve_cash = st.number_input("抽屜預留零用金底金 (元)", value=5000, step=500, help="找零用固定備用金（固定不變）")
    with col_c2:
        counted_cash = st.number_input("錢櫃點收現鈔總額 (含底金) (元)", min_value=0, value=52200, step=10, help="包含底金清點的所有現金總數")
    with col_c3:
        # 實際營業實收現金 = 點收現鈔總額 - 底金
        actual_operating_cash = counted_cash - reserve_cash
        st.metric(label="💵 實際清點營業現金", value=f"NT$ {actual_operating_cash:,}")

    st.divider()

    # ------------------------------------------
    # 區塊 3：自動計算現金溢短 (Over/Short) 與防弊警示
    # ------------------------------------------
    cash_variance = actual_operating_cash - system_expected_cash
    
    st.markdown("##### ⚖️ 【現金對帳差異分析】")
    
    v_col1, v_col2 = st.columns([1, 2])
    with v_col1:
        # 格式化差異
        if cash_variance > 0:
            diff_label = f"+NT$ {cash_variance:,} (現金盤盈/溢)"
        elif cash_variance < 0:
            diff_label = f"-NT$ {abs(cash_variance):,} (現金短少/虧)"
        else:
            diff_label = "NT$ 0 (完全相符)"

        st.metric(label="現金溢短差額", value=diff_label)

    with v_col2:
        # 防弊核心：超過 ±100 元標示紅燈警示
        status = ""
        if abs(cash_variance) > 100:
            status = "🚨 異常警示"
            st.error(f"🚨【異常警告】現金誤差達 NT$ {cash_variance:,}，已超過允許標準 (±100元)！此筆紀錄將直接標記並提報財務部與潘董！")
        elif cash_variance != 0:
            status = "⚠️ 輕微誤差"
            st.warning(f"⚠️【注意】現金有些微誤差 (NT$ {cash_variance:,})，在允許容許值內，請再次覆核錢櫃。")
        else:
            status = "🟢 帳實相符"
            st.success("🟢【帳實完美相符】實點現金與系統數據完全一致！")

    settle_note = st.text_input("📝 日結備註事項 (若有長短溢短請在此說明原因，例如：某客少收5元)", placeholder="請填寫任何異常說明...")

    # ------------------------------------------
    # 區塊 4：送出審核存檔 (防連點保護)
    # ------------------------------------------
    btn_settle_ph = st.empty()
    if btn_settle_ph.button("🔒 確認日結無誤並上傳總部", type="primary", use_container_width=True, key="btn_submit_settle"):
        btn_settle_ph.button("⏳ 雲端核算存檔中，請勿關閉視窗...", disabled=True, use_container_width=True, key="btn_submit_settle_dis")
        
        record_payload = {
            "settle_date": date_str,
            "store_name": store_name,
            "operator": current_user,
            "pos_total_revenue": int(pos_total),
            "electronic_payment": int(electronic_pay),
            "system_expected_cash": int(system_expected_cash),
            "reserve_cash": int(reserve_cash),
            "counted_cash": int(counted_cash),
            "actual_operating_cash": int(actual_operating_cash),
            "cash_variance": int(cash_variance),
            "status": status,
            "note": settle_note.strip()
        }
        
        if save_daily_settlement_to_cloud(record_payload):
            st.success(f"✅ 【{store_name}】{date_str} 日結對帳單已成功存檔至中央雲端！")
            st.rerun()
