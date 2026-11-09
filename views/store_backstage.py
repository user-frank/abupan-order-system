import streamlit as st
from views import order_vegetable

def show():
    current_user = st.session_state.get("user_name", "後台管理")
    st.markdown("### 🏪 潘大廚 - 門市後台管理系統")
    st.caption(f"登入身份：{current_user}｜")

    # 依照你的規劃設置三大模組分頁
    tabs = st.tabs(["🥬 叫菜系統", "📦 叫貨系統 (乾貨/包材)", "📊 庫存管理"])

    # 1. 叫菜系統 (單獨 py 管理)
    with tabs[0]:
        order_vegetable.show()

    # 2. 叫貨系統
    with tabs[1]:
        st.markdown("#### 📦 叫貨系統 (建置中)")
        st.info("💡 提供乾貨、調味料、包材叫貨，稍後完成。")

    # 3. 庫存管理
    with tabs[2]:
        st.markdown("#### 📊 門市庫存管理 (建置中)")
        st.info("💡 門市原物料盤點與安全庫存水位監控模組。")
