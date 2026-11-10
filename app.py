import streamlit as st
from splash_screen import show_splash_screen 
from auth_engine import check_login, logout

# 1. 網頁基本設定 (必須是第一行)
st.set_page_config(page_title="潘大廚", page_icon="👨‍🍳", layout="wide")

# ==========================================
# 2. 全域 CSS 樣式與裝潢 (保留你原本的心血，完全不動)
# ==========================================
st.markdown("""
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="mobile-web-app-capable" content="yes">
<link rel="apple-touch-icon" href="https://cdn-icons-png.flaticon.com/512/1046/1046774.png">

<style>
/* 背景與全域文字 */
.stApp { background-color: #000000 !important; }
body, h1, h2, h3, h4, p, span, div, li, label, input, button { color: #FFFFFF !important; }

/* 暴力隱藏所有官方圖示與白條 */
header[data-testid="stHeader"], 
.stAppDeployButton, 
#MainMenu,
footer,
iframe[title="Managed Hosting Toolbar"],
div[data-testid="stStatusWidget"],
[data-testid="stDecoration"], 
div[class*="stStatusWidget"],
[data-testid="stConnectionStatus"],
div[style*="position: fixed"][style*="bottom"] {
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
    height: 0 !important;
    width: 0 !important;
    pointer-events: none !important;
}

/* 輸入框與按鈕特殊修復 */
input { color: #000000 !important; background-color: #FFFFFF !important; }
div.stButton > button { background-color: #f37021 !important; color: white !important; border: none !important; }

/* 原有 UI 微調 */
.block-container { padding-top: 2rem !important; }
div[data-testid="stImage"] img { height: 220px !important; object-fit: cover !important; border-radius: 8px; }
.sales-text { color: #FFD93D !important; font-weight: bold; }
.sales-text-alert { color: #FF6B6B !important; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. 開場動畫 (保留你原本的 Splash Screen)
# ==========================================
if 'has_seen_splash' not in st.session_state: 
    st.session_state.has_seen_splash = False
    
if not st.session_state.has_seen_splash:
    show_splash_screen()
    st.session_state.has_seen_splash = True
    try: 
        st.rerun()
    except AttributeError: 
        st.experimental_rerun()

# 初始化購物車 (保留以防萬一)
if 'cart' not in st.session_state: 
    st.session_state.cart = {} 

# ==========================================
# 4. 呼叫大門鎖 (身分驗證)
# ==========================================
is_logged_in, current_dept, current_user = check_login()

# ==========================================
# 5. 登入成功後的「房間轉接台」
# ==========================================
if is_logged_in:
    
    # --- 頂部導覽列 (取代原本的側邊欄) ---
    col1, col2 = st.columns([3, 1])
    with col1:
        # 顯示目前使用者身分
        st.markdown(f"<h4 style='margin-top: 10px; color: #1B7A3E !important;'>👤 {current_dept} - {current_user}</h4>", unsafe_allow_html=True)
    with col2:
        # 右上角登出按鈕
        if st.button("🚪 登出", use_container_width=True):
            logout()
    st.divider() # 畫一條分隔線
    
    # --- 根據部門轉接房間 ---
    # --- 根據 4 大身分轉接專屬房間 ---
    if current_dept == "👑 老闆":
        from views import panboss   # 👈 轉接到全新獨立檔 panboss.py
        panboss.show()

    elif current_dept == "👨‍🍳 營運主廚 (廚政與門市)":
        if current_user == "門市後台管理":
            from views import store_backstage
            store_backstage.show()
        else:
            from views import store_front # 前台獨立檔！
            store_front.show()

    elif current_dept == "💰 財務會計":
        from views import finance   # 👈 轉接到獨立 finance.py
        finance.show()

    elif current_dept == "🛠️ 系統管理員":
        from views import demo_photo
        demo_photo.show()

    else:
        st.error(f"❌ 找不到 {current_dept} 的專屬房間，請聯繫系統管理員。")
