import streamlit as st
import datetime

def show():
    current_user = st.session_state.get("user_name", "門市前台")
    today = datetime.date.today()
    weekdays = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
    today_str = f"{today.strftime('%Y-%m-%d')} ({weekdays[today.weekday()]})"

    st.markdown("### 🍱 潘大廚 - 門市前台出餐與營運")
    st.caption(f"登入身份：{current_user}｜本日日期：{today_str}")

    # 前台三大核心功能
    tabs = st.tabs(["📋 1. 今日出餐計畫", "✅ 2. 現場出餐回報", "📢 3. 預排隔日出餐"])

    with tabs[0]:
        st.markdown("#### 📋 今日出餐預估表")
        st.info("💡 這裡將顯示廚房預計製作的餐點與便當份數。")

    with tabs[1]:
        st.markdown("#### ✅ 現場實際出餐與耗損回報")
        st.info("💡 供前台人員回報各餐期實際賣出數量與剩餘報廢。")

    with tabs[2]:
        st.markdown("#### 📢 預排隔日出餐")
        st.info("💡 提供隔日預排出餐。")
