import streamlit as st

# 1. 測試用的部門與人員密碼清單
DEPT_CREDENTIALS = {
    "冰鮮": {
        "184920": "劉雅惠",
        "837105": "王允恩"
    },
    "活體": {
        "701113": "謝書毓",
        "592631": "李唯有"
    },
    "壽司": {
        "666666": "徐志威",
        "1234": "賴泳鋕",
        "937512": "張淑鈞"
    },
    "生魚片": {
        "850528": "曾建君",
        "001133": "李建達"
    },
    "庫克島": {
        "856201": "趙仁豪"
    },
    "總管理": {
        "888888": "BOSS" # 老闆的我也先隨機設一個好記的
    }
}

def check_login():
    """負責顯示登入畫面，並回傳登入狀態"""
    
    # 初始化 Session State
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
        st.session_state["department"] = ""
        st.session_state["user_name"] = ""

    # 如果已經登入，直接放行
    if st.session_state["logged_in"]:
        return True, st.session_state["department"], st.session_state["user_name"]

    # --- 如果還沒登入，顯示這段登入表單 ---
    st.markdown("<br><br>", unsafe_allow_html=True) # 往下推一點比較好看
    st.markdown("<h2 style='text-align: center;'>🐟 阿布潘員工系統</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>請選擇所屬部門並輸入個人密碼</p>", unsafe_allow_html=True)
    
    # 讓畫面置中
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            dept_list = list(DEPT_CREDENTIALS.keys())
            selected_dept = st.selectbox("📌 所屬部門", dept_list)
            entered_pin = st.text_input("🔑 個人密碼", type="password")
            
            if st.button("登入系統", use_container_width=True, type="primary"):
                if entered_pin in DEPT_CREDENTIALS[selected_dept]:
                    user_name = DEPT_CREDENTIALS[selected_dept][entered_pin]
                    # 密碼正確，存入狀態並重整
                    st.session_state["logged_in"] = True
                    st.session_state["department"] = selected_dept
                    st.session_state["user_name"] = user_name
                    st.rerun()
                else:
                    st.error("❌ 密碼錯誤或查無此人！")
                    
    # 阻擋通行
    return False, "", ""

def logout():
    """清除狀態並登出"""
    st.session_state["logged_in"] = False
    st.session_state["department"] = ""
    st.session_state["user_name"] = ""
    st.rerun()
