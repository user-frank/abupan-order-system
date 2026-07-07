import streamlit as st
import pandas as pd
from datetime import datetime
import io
from PIL import Image, ImageOps # 🌟 影像壓縮神器

def compress_image(uploaded_file):
    """將高畫質手機照片壓縮到適合網頁快速讀取的大小"""
    # 讀取圖片
    img = Image.open(uploaded_file)
    # 自動校正手機拍照的方向 (避免照片橫躺)
    img = ImageOps.exif_transpose(img)
    
    # 限制最大長寬為 1024px，等比例縮小
    img.thumbnail((1024, 1024))
    
    # 將壓縮後的圖片轉回位元組 (Bytes)
    output = io.BytesIO()
    # 儲存為 JPEG 格式，品質 85% (人眼看不出差異，但檔案超小)
    img.save(output, format="JPEG", quality=85)
    return output.getvalue()

def show():
    current_user = st.session_state.get("user_name", "測試員")
    DEPT_NAME = "測試部"
    today_str = datetime.today().strftime("%Y-%m-%d")

    st.markdown("### 📸 現場紀實與照片回報測試")
    st.markdown("<p style='color:#888; font-size:14px;'>這是一個不干擾出餐系統的獨立相簿測試區，照片將會自動壓縮並分類。</p>", unsafe_allow_html=True)
    
    # 建立兩個分頁
    tab_upload, tab_view = st.tabs(["📤 1. 上傳照片", "🖼️ 2. 檢視今日相簿"])

    # 模擬資料庫 (存在記憶體中供測試)
    if "test_photo_db" not in st.session_state:
        st.session_state.test_photo_db = pd.DataFrame(columns=["date", "dept", "category", "uploader", "time", "image_data", "file_size"])

    # ==========================================
    # 分頁 1：上傳照片 (現場員工視角)
    # ==========================================
    with tab_upload:
        with st.container(border=True):
            # 🌟 1. 選擇分類 (可動態擴充)
            categories = ["分類_廢品紀錄", "分類_客訴處理", "分類_進貨驗收", "分類_環境清潔", "分類_其他"]
            selected_cat = st.selectbox("📌 請選擇照片分類：", categories)
            
            st.divider()
            
            # 🌟 2. 支援多檔案上傳
            uploaded_files = st.file_uploader(
                "📸 請點擊拍照或從相簿選擇 (支援多選)", 
                type=['png', 'jpg', 'jpeg'], 
                accept_multiple_files=True
            )
            
            if uploaded_files:
                st.info(f"已選取 {len(uploaded_files)} 張照片準備上傳。")
                
                if st.button("🚀 確認上傳至雲端", type="primary", use_container_width=True):
                    
                    new_records = []
                    # 顯示進度條，讓員工知道系統在努力壓縮
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    for i, file in enumerate(uploaded_files):
                        status_text.text(f"正在壓縮與上傳第 {i+1} 張照片...")
                        
                        original_size = file.size / 1024 # KB
                        
                        # 執行魔法壓縮！
                        compressed_bytes = compress_image(file)
                        compressed_size = len(compressed_bytes) / 1024 # KB
                        
                        size_info = f"原圖 {original_size:.0f}KB ➡️ 壓縮後 {compressed_size:.0f}KB"
                        
                        new_records.append({
                            "date": today_str,
                            "dept": DEPT_NAME,
                            "category": selected_cat,
                            "uploader": current_user,
                            "time": datetime.now().strftime("%H:%M:%S"),
                            "image_data": compressed_bytes, # 實戰時會改成雲端網址
                            "file_size": size_info
                        })
                        
                        progress_bar.progress((i + 1) / len(uploaded_files))
                    
                    # 存入模擬資料庫
                    if new_records:
                        new_df = pd.DataFrame(new_records)
                        st.session_state.test_photo_db = pd.concat([st.session_state.test_photo_db, new_df], ignore_index=True)
                        
                    status_text.text("✅ 所有照片上傳完畢！")
                    st.success(f"成功將 {len(uploaded_files)} 張照片存入【{selected_cat}】！")

    # ==========================================
    # 分頁 2：檢視相簿 (老闆/主管視角)
    # ==========================================
    with tab_view:
        db = st.session_state.test_photo_db
        
        if db.empty:
            st.info("今日尚無上傳任何照片。")
        else:
            # 🌟 讓老闆可以透過分類過濾照片
            view_cat = st.selectbox("🔍 篩選檢視分類：", ["顯示全部"] + categories)
            
            if view_cat != "顯示全部":
                view_db = db[db["category"] == view_cat]
            else:
                view_db = db
                
            st.markdown(f"**共找到 {len(view_db)} 張相片**")
            
            # 🌟 瀑布流照片牆 (電腦雙排/三排，手機單排大圖)
            cols = st.columns(2) # 這裡可以依照喜好切成 3 欄
            
            for idx, row in view_db.iterrows():
                with cols[idx % 2]:
                    with st.container(border=True):
                        # 顯示壓縮後的圖片
                        st.image(row["image_data"], use_container_width=True)
                        
                        # 顯示資訊卡
                        st.markdown(f"""
                        <div style='font-size:12px; color:#888;'>
                            🏷️ <b>分類：</b>{row['category']}<br>
                            👤 <b>上傳者：</b>{row['uploader']} ({row['time']})<br>
                            📦 <b>壓縮成效：</b>{row['file_size']}
                        </div>
                        """, unsafe_allow_html=True)
