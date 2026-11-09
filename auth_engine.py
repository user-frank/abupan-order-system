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
    """負責顯示【潘大廚】專屬旗艦風格登入畫面，並回傳登入狀態"""
    
    # 初始化 Session State
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
        st.session_state["department"] = ""
        st.session_state["user_name"] = ""

    # 如果已經登入，直接放行
    if st.session_state["logged_in"]:
        return True, st.session_state["department"], st.session_state["user_name"]

    # ==========================================
    # 🌟 潘大廚 門市旗艦視覺 CSS
    # ==========================================
    st.markdown("""
    <style>
    /* 引入思源黑體與現代感字型 */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@600;900&family=Noto+Sans+TC:wght@400;700&display=swap');

    /* 登入卡片主外框：帶微光墨綠與木質暖金邊框 */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: rgba(0, 168, 80, 0.35) !important;
        background: linear-gradient(180deg, rgba(20, 30, 24, 0.85) 0%, rgba(12, 16, 14, 0.95) 100%) !important;
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.8), 0 0 25px rgba(0, 168, 80, 0.15);
        border-radius: 16px !important;
        padding: 1.5rem !important;
    }

    /* 潘大廚招牌綠按鈕 */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #00C853 0%, #00873E 100%) !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        font-size: 1.05rem !important;
        letter-spacing: 2px !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 15px rgba(0, 200, 83, 0.3) !important;
        transition: all 0.2s ease-in-out !important;
        padding-top: 0.6rem !important;
        padding-bottom: 0.6rem !important;
    }
    
    div.stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #00E676 0%, #00A850 100%) !important;
        box-shadow: 0 6px 20px rgba(0, 200, 83, 0.5) !important;
        transform: translateY(-1px);
    }

    div.stButton > button[kind="primary"]:active {
        transform: scale(0.98);
    }

    /* 輸入框高質感微調 */
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div {
        background-color: #1A1F1C !important;
        border-color: #2D3D32 !important;
        border-radius: 8px !important;
    }
    
    div[data-baseweb="input"] input {
        color: #FFFFFF !important;
        background-color: transparent !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # 頂部預留空隙
    st.markdown("<div style='height: 25px;'></div>", unsafe_allow_html=True)
    
    # 讓畫面置中 (手機寬螢幕自適應)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # ==========================================
        # 門市品牌招牌 Header
        # ==========================================
        st.markdown("""
        <div style="text-align: center; margin-bottom: 20px;">
            <!-- 招牌綠麥穗徽章意象 -->
            <div style="display: inline-flex; align-items: center; justify-content: center; width: 72px; height: 72px; background: #00A850; border-radius: 50%; box-shadow: 0 0 20px rgba(0, 168, 80, 0.4); border: 2px solid #D4AF37; margin-bottom: 12px;">
                <span style="font-family: 'Noto Serif TC', serif; font-size: 34px; font-weight: 900; color: #FFF; text-shadow: 0 2px 4px rgba(0,0,0,0.4);">潘</span>
            </div>
            
            <!-- 品牌字體與排版 -->
            <h1 style="font-family: 'Noto Serif TC', serif; font-size: 2.2rem; font-weight: 900; letter-spacing: 4px; margin: 0; color: #FFFFFF; text-shadow: 0 2px 10px rgba(0,0,0,0.5);">
                潘 大 廚
            </h1>
            
            <!-- 招牌標語與朱印 -->
            <div style="display: flex; align-items: center; justify-content: center; gap: 8px; margin-top: 6px;">
                <span style="font-size: 0.95rem; color: #00C853; font-weight: 700; letter-spacing: 3px;">
                    一日三餐，就吃潘大廚
                </span>
                <span style="display: inline-block; background-color: #C62828; color: #FFF; font-size: 10px; padding: 1px 4px; border-radius: 2px; font-family: serif; font-weight: bold; border: 1px solid rgba(255,255,255,0.3);">
                    直營
                </span>
            </div>
            
            <p style="font-size: 11px; color: #6E7C72; letter-spacing: 2px; margin-top: 4px;">
                PAN DA CHU ・ 智慧營運管理系統
            </p>
        </div>
        """, unsafe_allow_html=True)

        with st.container(border=True):
            dept_list = list(DEPT_CREDENTIALS.keys())
            
            st.markdown("<span style='font-size: 13px; color: #9EAB9F; font-weight: 500;'>📍 所屬營運部門</span>", unsafe_allow_html=True)
            selected_dept = st.selectbox("所屬部門", dept_list, label_visibility="collapsed")
            
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            
            st.markdown("<span style='font-size: 13px; color: #9EAB9F; font-weight: 500;'>🔑 個人登入密碼</span>", unsafe_allow_html=True)
            entered_pin = st.text_input("個人密碼", type="password", placeholder="請輸入 4~6 碼 PIN 碼", label_visibility="collapsed")
            
            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
            
            if st.button("進入營運大廳", use_container_width=True, type="primary"):
                if entered_pin in DEPT_CREDENTIALS[selected_dept]:
                    user_name = DEPT_CREDENTIALS[selected_dept][entered_pin]
                    st.session_state["logged_in"] = True
                    st.session_state["department"] = selected_dept
                    st.session_state["user_name"] = user_name
                    st.rerun()
                else:
                    st.error("❌ 密碼錯誤或權限未開通！")

        # 底部版權宣告小字
        st.markdown("<p style='text-align: center; color: #4B554E; font-size: 11px; margin-top: 15px;'>© 潘大廚 PAN DA CHU. All Rights Reserved.</p>", unsafe_allow_html=True)
                    
    return False, "", ""

def logout():
    """清除狀態並登出"""
    st.session_state["logged_in"] = False
    st.session_state["department"] = ""
    st.session_state["user_name"] = ""
    st.rerun()
