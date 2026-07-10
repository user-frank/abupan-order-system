import streamlit as st
import pandas as pd
from datetime import datetime
import io
import base64
import requests
import re 
from PIL import Image, ImageOps
from record_engine import get_gspread_client, SHEET_NAME

# 🌟 【終極防爆設定】：解除 Pillow 內建的安全限制，避免處理大圖時當機
Image.MAX_IMAGE_PIXELS = None

# ==========================================
# ⚙️ 設定區
# ==========================================
GAS_URL = "https://script.google.com/macros/s/AKfycbyTqQxSCLm_fC7P1uVjZkVqP2YpGzO8xWqWbU2n4J-X_z1Pj9sL-L8fM6Q_9K5vBw/exec"
FOLDER_ID = "1aBcDeFgHiJkLmNoPqRsTuVwXyZ123456" # 請確保這是你正確的資料夾 ID

# ==========================================
# 📸 影像處理與上傳引擎 (Segfault 防護版)
# ==========================================
def compress_image(uploaded_file):
    """將高畫質照片壓縮，並配備 Segfault 防護罩"""
    try:
        # 1. 安全讀取圖片
        img = Image.open(uploaded_file)
        
        # 2. 自動校正方向 (這步最容易當機，加上 try-except)
        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass # 如果轉正失敗就維持原狀，不勉強
        
        # 3. 🌟 【防 Segfault 核心】：絕對安全的色彩轉換
        # 不要用 img.convert("RGB")，改用更穩定的新建畫布法
        if img.mode in ("RGBA", "P", "LA"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            # 處理有 Alpha 通道的情況
            if img.mode in ('RGBA', 'LA'):
                background.paste(img, mask=img.split()[-1])
            else:
                background.paste(img)
            img = background
            
        # 4. 安全縮圖
        img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
        
        # 5. 安全輸出
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=85, optimize=True)
        return output.getvalue()
        
    except Exception as e:
        print(f"⚠️ 圖片壓縮失敗，改用原圖直出: {e}")
        # 🌟 如果真的壓縮失敗，不要當機！直接把原圖傳上去當作保底！
        uploaded_file.seek(0)
        return uploaded_file.read()

def upload_photo_to_drive(file_bytes, filename):
    try:
        b64_str = base64.b64encode(file_bytes).decode('utf-8')
        payload = {
            "folder_id": FOLDER_ID,
            "file_name": filename,
            "mime_type": "image/jpeg",
            "image_base64": b64_str
        }
        res = requests.post(GAS_URL, json=payload, timeout=30)
        data = res.json()
        if data.get("status") == "success":
            return f"https://drive.google.com/thumbnail?id={data['file_id']}&sz=w1000"
        else:
            st.error(f"上傳失敗：{data.get('message')}")
            return None
    except Exception as e:
        st.error(f"上傳通道發生異常：{e}")
        return None

def save_photo_record_to_sheet(records):
    client = get_gspread_client()
    if not client: return False
    try:
        spreadsheet = client.open(SHEET_NAME)
        try:
            sheet = spreadsheet.worksheet("photo_records")
        except:
            sheet = spreadsheet.add_worksheet(title="photo_records", rows="1000", cols="10")
            sheet.append_row(["date", "dept", "category", "uploader", "time", "photo_url"])
            
        rows_to_add = [[r["date"], r["dept"], r["category"], r["uploader"], r["time"], r["photo_url"]] for r in records]
        sheet.append_rows(rows_to_add)
        return True
    except Exception as e:
        st.error(f"寫入試算表失敗：{e}")
        return False

# ==========================================
# 🏢 網頁主介面
# ==========================================
def show():
    current_user = st.session_state.get("user_name", "測試員")
    DEPT_NAME = "測試部"
    today_str = datetime.today().strftime("%Y-%m-%d")

    # 🌟 鎖死外框，避免排版跑掉
    st.markdown("""
    <style>
    div[data-testid="stImage"] {
        height: 280px !important;
        overflow: hidden !important;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: #1E1E1E; 
    }
    div[data-testid="stImage"] img {
        height: 100% !important;
        width: 100% !important;
        object-fit: cover !important; 
    }
    div[data-testid="stFullScreenFrame"], 
    div[data-testid="stFullScreenFrame"] > div {
        height: 100vh !important;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    div[data-testid="stFullScreenFrame"] img {
        height: auto !important;
        max-height: 95vh !important;
        width: auto !important;
        max-width: 100vw !important;
        object-fit: contain !important; 
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("### 📸 現場紀實與照片回報測試")
    test_role = st.radio("👀 切換測試視角：", ["🧑‍🍳 現場員工 (只能看本月)", "👑 老闆 (可看全部)"], horizontal=True)

    tab_upload, tab_view = st.tabs(["📤 1. 上傳照片", "🖼️ 2. 檢視歷史相簿"])

    with tab_upload:
        with st.container(border=True):
            categories = ["分類_廢品紀錄", "分類_客訴處理", "分類_進貨驗收", "分類_環境清潔", "分類_其他"]
            selected_cat = st.selectbox("📌 請選擇照片分類：", categories)
            st.divider()
            uploaded_files = st.file_uploader(
                "📸 請點擊拍照或從相簿選擇 (支援多選)", 
                type=['png', 'jpg', 'jpeg'], 
                accept_multiple_files=True
            )
            if uploaded_files:
                if st.button("🚀 確認上傳至雲端", type="primary", use_container_width=True):
                    new_records = []
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    for i, file in enumerate(uploaded_files):
                        status_text.text(f"正在處理第 {i+1} 張照片...")
                        
                        # 🌟 使用安全版壓縮
                        compressed_bytes = compress_image(file)
                        filename = f"{today_str}_{DEPT_NAME}_{selected_cat}_{i}.jpg"
                        
                        status_text.text(f"正在將第 {i+1} 張照片送往雲端...")
                        drive_url = upload_photo_to_drive(compressed_bytes, filename)
                        
                        if drive_url:
                            new_records.append({
                                "date": today_str,
                                "dept": DEPT_NAME,
                                "category": selected_cat,
                                "uploader": current_user,
                                "time": datetime.now().strftime("%H:%M:%S"),
                                "photo_url": drive_url
                            })
                        progress_bar.progress((i + 1) / len(uploaded_files))
                    
                    if new_records:
                        status_text.text("正在寫入資料庫...")
                        if save_photo_record_to_sheet(new_records):
                            status_text.text("✅ 所有照片上傳完畢！")
                            st.success(f"成功將 {len(uploaded_files)} 張照片存入雲端資料庫！")
                        else:
                            status_text.text("❌ 資料庫寫入失敗。")

    with tab_view:
        client = get_gspread_client()
        db = pd.DataFrame()
        if client:
            try:
                sheet = client.open(SHEET_NAME).worksheet("photo_records")
                db = pd.DataFrame(sheet.get_all_records())
            except:
                pass
        
        if db.empty:
            st.info("資料庫中尚無任何照片紀錄。")
        else:
            st.markdown("#### 🔍 歷史影像調閱")
            
            if "老闆" in test_role:
                col1, col2 = st.columns(2)
                with col1: date_filter = st.date_input("🗓️ 選擇調閱日期：", value=datetime.today())
                with col2:
                    all_depts = ["顯示全部"] + list(db["dept"].astype(str).unique())
                    dept_filter = st.selectbox("🏢 選擇部門：", all_depts)
            else:
                min_date = datetime.today().replace(day=1)
                max_date = datetime.today()
                date_filter = st.date_input("🗓️ 選擇調閱日期 (限本月)：", value=max_date, min_value=min_date, max_value=max_date)
                dept_filter = DEPT_NAME 
            
            cat_filter = st.selectbox("📌 選擇分類：", ["顯示全部"] + categories)
            
            view_db = db[db["date"] == date_filter.strftime("%Y-%m-%d")]
            if dept_filter != "顯示全部": view_db = view_db[view_db["dept"] == dept_filter]
            if cat_filter != "顯示全部": view_db = view_db[view_db["category"] == cat_filter]
                
            st.markdown(f"**共找到 {len(view_db)} 張相片**")
            st.divider()
            
            if not view_db.empty:
                cols = st.columns(2) 
                for idx, row in view_db.iterrows():
                    with cols[idx % 2]:
                        with st.container(border=True):
                            display_url = str(row["photo_url"])
                            file_id_match = re.search(r'id=([a-zA-Z0-9_-]+)', display_url)
                            
                            if file_id_match:
                                file_id = file_id_match.group(1)
                                thumb_url = f"https://drive.google.com/thumbnail?id={file_id}&sz=w600-h450-c"
                                view_url = f"https://drive.google.com/file/d/{file_id}/view"
                                
                                img_html = f"""
                                <a href="{view_url}" target="_blank" title="點擊放大觀看高畫質原圖">
                                    <img src="{thumb_url}" style="width: 100%; border-radius: 8px; margin-bottom: 10px; border: 1px solid rgba(255,255,255,0.1); object-fit: cover;">
                                </a>
                                """
                                st.markdown(img_html, unsafe_allow_html=True)
                            else:
                                st.image(display_url, use_container_width=True) 
                            
                            st.markdown(f"""
                            <div style='font-size:13px; color:#ddd;'>
                                🏢 <b>部門：</b>{row['dept']}<br>
                                🏷️ <b>分類：</b>{row['category']}<br>
                                👤 <b>上傳者：</b>{row['uploader']} ({row['time']})
                            </div>
                            """, unsafe_allow_html=True)
