import streamlit as st

# 1. 測試用的部門與人員密碼清單
DEPT_CREDENTIALS = {
    "冰鮮": {
        "184920": "劉雅惠",
        "837105": "王允恩"
    },
    "活體": {
        "701113": "謝書毓",
        "401300": "李唯有"
    },
    "壽司": {
        "666666": "徐智威",
        "1234": "賴泳鋕",
        "0720": "張淑鈞"
    },
    "生魚片": {
        "850528": "曾建君",
        "001133": "李建達"
    },
    "庫克島": {
        "856201": "趙仁豪"
    },
    "測試部": {
        "0313": "管理員"
    },
    "總管理": {
        "8888": "BOSS"
    }
}

def check_login():
    """負責顯示潘大廚專屬品牌登入畫面，並回傳登入狀態"""
    
    # 初始化 Session State
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
        st.session_state["department"] = ""
        st.session_state["user_name"] = ""

    # 如果已經登入，直接放行
    if st.session_state["logged_in"]:
        return True, st.session_state["department"], st.session_state["user_name"]

    # 🌟 潘大廚專屬視覺注入 (深綠卡片、麥穗微光、品牌按鈕)
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@500;700;900&display=swap');

    /* 登入外層容器美化 */
    .login-container {
        background: linear-gradient(180deg, rgba(20, 38, 27, 0.85) 0%, rgba(10, 20, 14, 0.95) 100%);
        border: 1px solid rgba(46, 175, 96, 0.35);
        border-radius: 16px;
        padding: 24px 20px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.6), 0 0 20px rgba(46, 175, 96, 0.15);
    }

    /* 頂部麥穗 LOGO */
    .brand-badge {
        text-align: center;
        font-size: 2.8rem;
        line-height: 1;
        margin-bottom: 6px;
        filter: drop-shadow(0 0 12px rgba(46, 175, 96, 0.5));
    }

    /* 潘大廚主字體 */
    .brand-title {
        font-family: 'Noto Sans TC', sans-serif;
        text-align: center;
        font-size: 2.3rem;
        font-weight: 900;
        letter-spacing: 4px;
        margin: 0;
        background: linear-gradient(135deg, #FFFFFF 0%, #E8F5E9 40%, #A5D6A7 80%, #2E7D32 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    /* Slogan 標語 */
    .brand-slogan {
        text-align: center;
        color: #C8E6C9;
        font-size: 1rem;
        font-weight: 700;
        letter-spacing: 3px;
        margin-top: 4px;
        margin-bottom: 4px;
    }

    /* 直營門市副標記 */
    .brand-sub {
        text-align: center;
        font-size: 0.8rem;
        color: #81C784;
        letter-spacing: 2px;
        margin-bottom: 20px;
    }

    /* 潘大廚綠色按鈕覆寫 */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #2EAF60 0%, #1B7A3E 100%) !important;
        color: #FFFFFF !important;
        font-size: 1.05rem !important;
        font-weight: 700 !important;
        letter-spacing: 2px !important;
        border: 1px solid #4CAF50 !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 15px rgba(46, 175, 96, 0.3) !important;
        transition: all 0.2s ease-in-out !important;
    }

    div.stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #38C76F 0%, #22944C 100%) !important;
        box-shadow: 0 6px 20px rgba(46, 175, 96, 0.5) !important;
        transform: translateY(-1px);
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # 畫面水平置中
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div class="brand-badge">🌾</div>
        <h1 class="brand-title">潘大廚</h1>
        <div class="brand-slogan">一日三餐，就吃潘大廚</div>
        <div class="brand-sub">直營一號店 ｜ 智慧營運管理系統</div>
        """, unsafe_allow_html=True)

        with st.container():
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            
            dept_list = list(DEPT_CREDENTIALS.keys())
            selected_dept = st.selectbox("📌 選擇所屬單位", dept_list)
            entered_pin = st.text_input("🔑 輸入個人密碼", type="password", placeholder="請輸入 4~6 位 PIN 碼")
            
            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            
            if st.button("🚀 登入系統", use_container_width=True, type="primary"):
                if entered_pin in DEPT_CREDENTIALS[selected_dept]:
                    user_name = DEPT_CREDENTIALS[selected_dept][entered_pin]
                    st.session_state["logged_in"] = True
                    st.session_state["department"] = selected_dept
                    st.session_state["user_name"] = user_name
                    st.rerun()
                else:
                    st.error("❌ 密碼錯誤或查無此人員！")
                    
            st.markdown('</div>', unsafe_allow_html=True)
                    
    return False, "", ""

def logout():
    """清除狀態並登出"""
    st.session_state["logged_in"] = False
    st.session_state["department"] = ""
    st.session_state["user_name"] = ""
    st.rerun()
