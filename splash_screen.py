import streamlit as st
import time

def show_splash_screen():
    # 🌟 「潘大廚」專屬尊榮品牌開場動畫
    splash_html = """
    <style>
    /* 引入 Google 現代黑體字型 */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@500;700;900&display=swap');
    
    /* 滿版黑色遮罩背景 */
    #splash-screen {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background-color: #0E1117; 
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        z-index: 999999; 
        animation: fadeOut 0.6s ease-in-out 2.0s forwards; 
    }

    /* 頂部小標題 (全新品牌) */
    .splash-brand-tag {
        color: #00A850; /* 潘大廚招牌綠 */
        font-family: 'Noto Sans TC', sans-serif;
        font-size: 0.95rem;
        letter-spacing: 4px;
        font-weight: 700;
        margin-bottom: 8px;
        opacity: 0;
        animation: slideUp 0.6s ease-out 0.1s forwards;
    }

    /* 主標題排版設定 */
    .splash-title {
        font-family: 'Noto Sans TC', sans-serif;
        font-size: 3.2rem;
        font-weight: 900;
        letter-spacing: 5px;
        margin-bottom: 8px;
        animation: slideUp 0.8s ease-out forwards;
    }

    /* 👑 核心：香檳金金屬質感特效 */
    .gold-text {
        background: linear-gradient(135deg, #D4AF37 0%, #FFF2CD 40%, #D4AF37 80%, #AA771C 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        filter: drop-shadow(0px 0px 12px rgba(212, 175, 55, 0.45));
    }

    /* 品牌精神 Slogan */
    .splash-slogan {
        color: #00C853; /* 醒目品牌鮮綠 */
        font-family: 'Noto Sans TC', sans-serif;
        font-size: 1.15rem;
        font-weight: 700;
        letter-spacing: 3px;
        margin-bottom: 12px;
        opacity: 0;
        animation: slideUp 0.8s ease-out 0.3s forwards;
    }

    /* 系統副標題 */
    .splash-subtitle {
        color: #A0A0A0; 
        font-family: 'Arial', sans-serif;
        font-size: 0.9rem;
        letter-spacing: 4px;
        opacity: 0; 
        animation: slideUp 0.8s ease-out 0.4s forwards;
    }
    
    /* 載入轉圈圈動畫 (尊榮金) */
    .spinner {
        margin-top: 30px;
        width: 38px;
        height: 38px;
        border: 3px solid rgba(212, 175, 55, 0.15);
        border-top: 3px solid #D4AF37; 
        border-radius: 50%;
        opacity: 0;
        animation: fadeIn 0.5s ease-out 0.5s forwards, spin 1s linear infinite;
    }

    /* 動畫軌跡 */
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

    <!-- 畫面內容區塊 -->
    <div id="splash-screen">
        <div class="splash-brand-tag">PAN DA CHU</div>
        <div class="splash-title">
            <span class="gold-text">潘大廚</span>
        </div>
        <div class="splash-slogan">一日三餐，就吃潘大廚</div>
        <div class="splash-subtitle">智慧餐飲管理平台</div>
        <div class="spinner"></div>
    </div>
    """
    
    splash_placeholder = st.empty()
    splash_placeholder.markdown(splash_html, unsafe_allow_html=True)
    
    time.sleep(2.6)
    
    splash_placeholder.empty()
