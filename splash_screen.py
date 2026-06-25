import streamlit as st
import time

def show_splash_screen():
    # 🌟 使用純 CSS 打造現代化、平滑的開場動畫
    splash_html = """
    <style>
    /* 引入 Google 現代黑體字型 */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@500;700&display=swap');
    
    /* 滿版黑色遮罩背景 */
    #splash-screen {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background-color: #0E1117; /* 搭配 Streamlit 的深色背景 */
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        z-index: 999999; /* 確保它疊在最上層 */
        animation: fadeOut 0.6s ease-in-out 1.5s forwards; /* 停留 1.8 秒後平滑淡出 */
    }

    /* 主標題樣式 (阿布潘員工系統) */
    .splash-title {
        color: #ffffff;
        font-family: 'Noto Sans TC', sans-serif;
        font-size: 2.5rem;
        font-weight: 700;
        letter-spacing: 2px;
        margin-bottom: 10px;
        animation: slideUp 0.8s ease-out forwards;
    }

    /* 副標題樣式 (INTELLIGENT SYSTEM) */
    .splash-subtitle {
        color: #f37021; /* 阿布潘專屬橘色 */
        font-family: 'Arial', sans-serif;
        font-size: 1.1rem;
        font-weight: bold;
        letter-spacing: 6px;
        animation: slideUp 0.8s ease-out 0.2s forwards;
        opacity: 0; /* 一開始先隱藏，製造層次感 */
    }
    
    /* 載入轉圈圈動畫 */
    .spinner {
        margin-top: 35px;
        width: 40px;
        height: 40px;
        border: 4px solid rgba(255, 255, 255, 0.1);
        border-top: 4px solid #f37021;
        border-radius: 50%;
        opacity: 0;
        /* 結合浮現與無限旋轉 */
        animation: fadeIn 0.5s ease-out 0.5s forwards, spin 1s linear infinite;
    }

    /* 定義各種動畫軌跡 */
    @keyframes slideUp {
        0% { transform: translateY(20px); opacity: 0; }
        100% { transform: translateY(0); opacity: 1; }
    }
    
    @keyframes fadeIn {
        0% { opacity: 0; }
        100% { opacity: 1; }
    }

    @keyframes fadeOut {
        0% { opacity: 1; visibility: visible; }
        100% { opacity: 0; visibility: hidden; display: none; }
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    </style>

    <!-- 這是畫面上實際顯示的內容區塊 -->
    <div id="splash-screen">
        <div class="splash-title">🐟 阿布潘員工系統</div>
        <div class="splash-subtitle">INTELLIGENT SYSTEM</div>
        <div class="spinner"></div>
    </div>
    """
    
    # 1. 建立一個佔位符，並將 HTML 畫面注入
    splash_placeholder = st.empty()
    splash_placeholder.markdown(splash_html, unsafe_allow_html=True)
    
    # 2. 讓 Python 後台暫停 2.5 秒，確保前端的 CSS 動畫有足夠時間播完並淡出
    time.sleep(2.5)
    
    # 3. 徹底清除佔位符，露出底下的總機登入大廳
    splash_placeholder.empty()
