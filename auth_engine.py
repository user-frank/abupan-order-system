import streamlit as st

# 🌟 潘大廚 精準 4 大角色與指定人員 PIN 碼
DEPT_CREDENTIALS = {
    "👨‍🍳 營運主廚 (廚政與門市)": {
        "1234": "門市前台管理",
        "5678": "門市後台管理"
    },
    "💰 財務會計": {
        "6688": "經理"
    },
    "👑 老闆": {
        "8888": "潘哥"
    },
    "🛠️ 系統管理員": {
        "0313": "系統工程師"
    }
}

def check_login():
    """負責顯示登入畫面，並回傳登入狀態"""
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
        st.session_state["department"] = ""
        st.session_state["user_name"] = ""

    if st.session_state["logged_in"]:
        return True, st.session_state["department"], st.session_state["user_name"]

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("""
    <h2 style='text-align: center; font-weight: 900; letter-spacing: 2px;'>
        👨‍🍳 <span style='
            background: linear-gradient(135deg, #D4AF37 0%, #FFF2CD 40%, #D4AF37 80%, #AA771C 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            filter: drop-shadow(0px 2px 8px rgba(212, 175, 55, 0.4));
        '>潘大廚</span>
    </h2>
    """, unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #00C853; font-weight: bold; letter-spacing: 2px;'>一日三餐，就吃潘大廚</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            dept_list = list(DEPT_CREDENTIALS.keys())
            selected_dept = st.selectbox("📌 身份權限", dept_list)
            entered_pin = st.text_input("🔑 個人密碼", type="password")
            
            if st.button("登入系統", use_container_width=True, type="primary"):
                if entered_pin in DEPT_CREDENTIALS[selected_dept]:
                    user_name = DEPT_CREDENTIALS[selected_dept][entered_pin]
                    st.session_state["logged_in"] = True
                    st.session_state["department"] = selected_dept
                    st.session_state["user_name"] = user_name
                    st.rerun()
                else:
                    st.error("❌ 密碼錯誤或查無此權限！")
                    
    return False, "", ""

def logout():
    """清除狀態並登出"""
    st.session_state["logged_in"] = False
    st.session_state["department"] = ""
    st.session_state["user_name"] = ""
    st.rerun()
