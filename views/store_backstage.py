import streamlit as st
from views import order_vegetable
from views import order_goods
from views import inventory_manage
from views import daily_settle   # 🌟 導入獨立日結模組

def show():
    current_user = st.session_state.get("user_name", "後台管理者")
    st.markdown("### 🏪 潘大廚 - 門市後台管理系統")
    st.caption(f"登入身份：{current_user}｜直營門市營運採購後台")

    # 四大核心獨立模組
    tabs = st.tabs([
        "🥬 1. 叫菜系統", 
        "📦 2. 叫貨系統 (乾貨/包材)", 
        "📊 3. 庫存管理", 
        "💰 4. 門市日結與現金對帳"
    ])

    with tabs[0]:
        order_vegetable.show()

    with tabs[1]:
        order_goods.show()

    with tabs[2]:
        inventory_manage.show()

    with tabs[3]:
        daily_settle.show()      # 🌟 獨立運作
