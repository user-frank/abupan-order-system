import streamlit as st
# 🌟 每個功能小細項都有獨立的 py 檔管理
from views import order_vegetable
from views import order_goods
from views import inventory_manage

def show():
    current_user = st.session_state.get("user_name", "後台管理者")
    st.markdown("### 🏪 潘大廚 - 門市後台管理系統")
    st.caption(f"登入身份：{current_user}｜直營門市營運採購後台")

    # 三大核心獨立模組
    tabs = st.tabs(["🥬 1. 叫菜系統", "📦 2. 叫貨系統 (乾貨/包材)", "📊 3. 庫存管理"])

    with tabs[0]:
        order_vegetable.show()

    with tabs[1]:
        order_goods.show()

    with tabs[2]:
        inventory_manage.show()
