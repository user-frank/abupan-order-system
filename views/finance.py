import streamlit as st
import pandas as pd
from record_engine import get_gspread_client, SHEET_NAME

@st.cache_data(ttl=30, show_spinner=False)
def load_finance_settlement_db():
    client = get_gspread_client()
    if not client: return pd.DataFrame()
    try:
        sp = client.open(SHEET_NAME)
        sheet = sp.worksheet("門市日結對帳表")
        records = sheet.get_all_records()
        return pd.DataFrame(records) if records else pd.DataFrame()
    except:
        return pd.DataFrame()

def show():
    current_user = st.session_state.get("user_name", "財務經理")
    st.markdown("### 💰 潘大廚 - 總部財務會計稽核台")
    st.caption(f"登入身份：{current_user}｜全直營門市營業額與現金溢短稽查")

    tabs = st.tabs(["💵 1. 門市日結審核與溢短監控", "📑 2. 廠商採購對帳 (預留)", "📊 3. 損益與毛利分析 (預留)"])

    with tabs[0]:
        st.markdown("#### 💵 各門市每日現金溢短稽核清單")
        df_settle = load_finance_settlement_db()

        if df_settle.empty:
            st.info("💡 目前資料庫中尚無任何門市日結上傳紀錄。")
        else:
            col_map = {
                "settle_date": "日結日期",
                "store_name": "門市",
                "operator": "清點人",
                "pos_total_revenue": "POS營業額",
                "electronic_payment": "電子支付",
                "system_expected_cash": "應收現金",
                "actual_operating_cash": "實點現金",
                "cash_variance": "現金差額 (溢短)",
                "status": "稽查狀態",
                "note": "備註"
            }
            show_df = df_settle[[c for c in col_map.keys() if c in df_settle.columns]].rename(columns=col_map)
            show_df = show_df.iloc[::-1] # 最新排最上面

            st.dataframe(show_df.astype(str), use_container_width=True, hide_index=True)

            # 警示統計
            alert_count = len(df_settle[df_settle["status"].astype(str).str.contains("🚨")])
            if alert_count > 0:
                st.error(f"⚠️ 稽核警告：歷史紀錄中共有 {alert_count} 筆現金差額超過 ±100 元，請儘速核對錢櫃監控！")
            else:
                st.success("🟢 各門市歷史現金溢短均在合理標準範圍內。")

    with tabs[1]:
        st.info("📑 廠商採購對帳與合約單價設定，稍後建置。")

    with tabs[2]:
        st.info("📊 損益表與成本毛利報表模組，稍後建置。")
