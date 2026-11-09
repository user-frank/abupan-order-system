import streamlit as st
import time

def show_splash_screen():
    # 🌟 潘大廚專屬品牌開場動畫 (森綠質感 + 稻穗光暈)
    splash_html = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@500;700;900&display=swap');

    #splash-screen {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background: radial-gradient(circle at center, #132219 0%, #080D0A 100%);
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        z-index: 999999;
        animation: fadeOut 0.6s ease-in-out 1.8s forwards;
    }

    /* 麥穗徽章外框容器 */
    .badge-icon {
        font-size: 3.2rem;
        margin-bottom: 8px;
        filter: drop-shadow(0px 0px 14px rgba(46, 175, 96, 0.6));
        animation: slideUp 0.8s ease-out forwards;
    }

    /* 品牌主標題 */
    .splash-title {
        font-family: 'Noto Sans TC', sans-serif;
        font-size: 2.8rem;
        font-weight: 900;
        letter-spacing: 5px;
        margin-bottom: 8px;
        animation: slideUp 0.8s ease-out 0.1s forwards;
    }

    /* 潘大廚白金發光立體字 */
    .chef-text {
        background: linear-gradient(135deg, #FFFFFF 0%, #E8F5E9 40%, #A5D6A7 80%, #2E7D32 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        filter: drop-shadow(0px 2px 10px rgba(76, 175, 80, 0.4));
    }

    /* 品牌標語 Slogan */
    .splash-subtitle {
        color: #C8E6C9;
        font-family: 'Noto Sans TC', sans-serif;
        font-size: 1.15rem;
        font-weight: 500;
        letter-spacing: 4px;
        animation: slideUp 0.8s ease-out 0.25s forwards;
        opacity: 0;
        border-top: 1px solid rgba(76, 175, 80, 0.3);
        padding-top: 10px;
        margin-top: 6px;
    }

    .splash-store {
        color: #81C784;
        font-size: 0.85rem;
        letter-spacing: 2px;
        margin-top: 6px;
        opacity: 0;
        animation: fadeIn 0.6s ease-out 0.4s forwards;
    }

    /* 森林綠轉圈載入動畫 */
    .spinner {
        margin-top: 30px;
        width: 38px;
        height: 38px;
        border: 3px solid rgba(76, 175, 80, 0.15);
        border-top: 3px solid #2EAF60;
        border-radius: 50%;
        opacity: 0;
        animation: fadeIn 0.5s ease-out 0.5s forwards, spin 1s linear infinite;
    }

    @keyframes slideUp {
        0% { transform: translateY(22px); opacity: 0; }
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

    <div id="splash-screen">
        <div class="badge-icon">🌾</div>
        <div class="splash-title">
            <span class="chef-text">潘大廚</span>
        </div>
        <div class="splash-subtitle">一日三餐，就吃潘大廚</div>
        <div class="splash-store">智慧餐飲營運管理平台</div>
        <div class="spinner"></div>
    </div>
    """

    splash_placeholder = st.empty()
    splash_placeholder.markdown(splash_html, unsafe_allow_html=True)

    time.sleep(2.4)

    splash_placeholder.empty()
