# -*- coding: utf-8 -*-
import streamlit as st
import time

def show_splash_screen():
    """
    渲染皇家黑金高貴風格的開場動畫（防彈安全版）。
    已加入強制 UTF-8 宣告與安全外部資源，確保絕不當機。
    """
    
    splash_html = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@700&display=swap');

    header {visibility: hidden;}
    
    .splash-container {
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        height: 100vh;
        background-color: #000000;
        background-image: radial-gradient(circle at center, #1a1a1a 0%, #000000 70%);
        font-family: 'Noto Serif TC', serif;
        overflow: hidden;
        position: relative;
    }
    
    .bg-lobster-faint {
        position: absolute;
        width: 100%;
        height: 100%;
        background-image: url('https://images.unsplash.com/photo-1553659971-f01207815844?q=80&w=1000'); 
        background-size: cover;
        background-position: center;
        opacity: 0; 
        z-index: 1;
        filter: grayscale(100%) sepia(100%) hue-rotate(20deg) brightness(0.2) contrast(1.2);
        animation: bgFadeIn 4s ease-out 0.5s forwards;
    }

    .logo-container {
        position: relative;
        width: 150px;
        height: 150px;
        margin-bottom: 30px;
        z-index: 2;
        animation: popInAndGlow 1.5s ease-out forwards;
    }

    .logo-container img {
        width: 100%;
        height: 100%;
        object-fit: contain;
        filter: invert(70%) sepia(80%) saturate(400%) hue-rotate(5deg) brightness(1.2) drop-shadow(0 0 15px rgba(212, 175, 55, 0.8));
        animation: lobsterBreathing 3s ease-in-out infinite 1.5s;
    }
    
    .gold-text {
        background: linear-gradient(to right, #BF953F 0%, #FCF6BA 25%, #B38728 50%, #FBF5B7 75%, #BF953F 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-size: 200% auto;
        animation: shine 3s linear infinite;
        opacity: 0;
    }

    .title {
        font-size: 48px;
        font-weight: 700;
        margin-top: 10px;
        letter-spacing: 8px;
        z-index: 2;
        animation: shine 3s linear infinite, slideUp 1s ease-out 0.8s forwards;
    }
    
    .subtitle {
        font-size: 20px;
        margin-top: 20px;
        letter-spacing: 4px;
        color: #C5A059;
        opacity: 0;
        z-index: 2;
        animation: slideUp 1s ease-out 1.2s forwards;
    }

    @keyframes bgFadeIn {
        0% { opacity: 0; transform: scale(1.1); }
        100% { opacity: 0.15; transform: scale(1); }
    }

    @keyframes popInAndGlow {
        0% { transform: scale(0) rotate(-10deg); opacity: 0; filter: blur(10px); }
        100% { transform: scale(1) rotate(0deg); opacity: 1; filter: blur(0px); }
    }
    
    @keyframes lobsterBreathing {
        0%, 100% { transform: scale(1); filter: invert(70%) sepia(80%) saturate(400%) hue-rotate(5deg) brightness(1.2) drop-shadow(0 0 15px rgba(212, 175, 55, 0.8)); }
        50% { transform: scale(1.05); filter: invert(70%) sepia(80%) saturate(500%) hue-rotate(5deg) brightness(1.4) drop-shadow(0 0 25px rgba(212, 175, 55, 1)); }
    }

    @keyframes shine { to { background-position: 200% center; } }
    @keyframes slideUp { 0% { transform: translateY(30px); opacity: 0; } 100% { transform: translateY(0); opacity: 1; } }

    @media (max-width: 768px) {
        .logo-container { width: 110px; height: 110px; margin-bottom: 20px; }
        .title { font-size: 32px; letter-spacing: 4px; }
        .subtitle { font-size: 16px; letter-spacing: 2px; }
        .splash-container { height: 90vh; }
    }
    </style>
    
    <div class="splash-container">
        <div class="bg-lobster-faint"></div>
        <div class="logo-container">
            <img src="https://cdn-icons-png.flaticon.com/512/1996/1996068.png" alt="Lobster">
        </div>
        <div class="title gold-text">阿布潘水產</div>
        <div class="subtitle">智能出餐決策系統</div>
    </div>
    """
    
    placeholder = st.empty()
    with placeholder.container():
        st.markdown(splash_html, unsafe_allow_html=True)
    
    time.sleep(3.5)
    placeholder.empty()
