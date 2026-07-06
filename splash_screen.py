import streamlit as st
import time

def show_splash_screen():
    # 🌟 使用純 CSS 打造「尊榮黑金」風格開場動畫
    splash_html = """
    <style>
    /* 引入 Google 現代黑體字型 */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@500;700&display=swap');
    
    /* 滿版黑色遮罩背景 (黑金的"黑") */
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
        animation: fadeOut 0.6s ease-in-out 1.8s forwards; 
    }

    /* 主標題排版設定 */
    .splash-title {
        font-family: 'Noto Sans TC', sans-serif;
        font-size: 2.6rem;
        font-weight: 700;
        letter-spacing: 3px;
        margin-bottom: 10px;
        animation: slideUp 0.8s ease-out forwards;
    }

    /* 👑 核心：黑金漸層文字特效 */
    .gold-text {
        /* 香檳金漸層：做出金屬反光的層次感 */
        background: linear-gradient(135deg, #D4AF37 0%, #FFF2CD 40%, #D4AF37 80%, #AA771C 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        /* 加上微微的金色光暈 */
        filter: drop-shadow(0px 0px 10px rgba(212, 175, 55, 0.4));
    }

    /* 副標題樣式 (還原成乾淨的銀灰色) */
    .splash-subtitle {
        color: #E0E0E0; 
        font-family: 'Arial', sans-serif;
        font-size: 1.1rem;
        font-weight: bold;
        letter-spacing: 6px;
        animation: slideUp 0.8s ease-out 0.2s forwards;
        opacity: 0; 
    }
    
    /* 載入轉圈圈動畫 (配合改成尊榮金) */
    .spinner {
        margin-top: 35px;
        width: 40px;
        height: 40px;
        border: 4px solid rgba(212, 175, 55, 0.1);
        border-top: 4px solid #D4AF37; 
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
        <div class="splash-title">
            🐟 <span class="gold-text">阿布潘水產</span>
        </div>
        <div class="splash-subtitle">智慧餐飲營運管理平台</div>
        <div class="spinner"></div>
    </div>
    """
    
    splash_placeholder = st.empty()
    splash_placeholder.markdown(splash_html, unsafe_allow_html=True)
    
    time.sleep(2.5)
    
    splash_placeholder.empty()
