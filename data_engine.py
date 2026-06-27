import pandas as pd
import os
import streamlit as st
import time
from record_engine import get_worksheet, _get_cloud_dataframe

IMAGE_BASE_DIR = "product_images"
DEFAULT_IMAGE = "https://images.unsplash.com/photo-1615141982883-c7ad0e69fd62?w=600&q=80"

def get_product_images_map():
    image_lookup = {}
    if not os.path.exists(IMAGE_BASE_DIR): return image_lookup
    for root, dirs, files in os.walk(IMAGE_BASE_DIR):
        for file in files:
            if file.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                item_id, _ = os.path.splitext(file)
                clean_id = str(item_id).upper().replace('.JPG', '').replace('.PNG', '').replace('.JPEG', '').replace('.WEBP', '').strip()
                final_path = os.path.join(root, file).replace("\\", "/")
                image_lookup[clean_id] = final_path
    return image_lookup

def safe_read_csv(file_path, enc, retries=3, delay=0.2):
    for attempt in range(retries):
        try:
            with open(file_path, 'r', encoding=enc) as f:
                return pd.read_csv(f, header=None, engine='python', on_bad_lines='skip')
        except Exception as e:
            if attempt == retries - 1: raise e
            time.sleep(delay)

def extract_basic_data(df_blind):
    """極簡版解析引擎：只抓編號、品名、單價，徹底廢除沒用的歷史數量"""
    try:
        header_idx = -1
        for idx, row in df_blind.iterrows():
            row_str = [str(val) for val in row.values]
            if any('品名' in s or '商品名稱' in s for s in row_str) and any('編號' in s or '品號' in s for s in row_str):
                header_idx = idx
                break
        
        if header_idx == -1: return None
        
        df = df_blind.iloc[header_idx+1:].copy()
        df.columns = df_blind.iloc[header_idx].astype(str).values
        df = df.loc[:, ~df.columns.duplicated()]
        
        cols = df.columns
        id_col = next((c for c in cols if '編號' in c or '品號' in c), None)
        n_col = next((c for c in cols if '品名' in c or '商品名稱' in c), None)
        
        # 🌟 自動識別單價欄位
        p_col = next((c for c in cols if '單價' in c or '價格' in c or 'price' in c), None)
        
        if not (id_col and n_col): return None
        
        columns_to_keep = [id_col, n_col]
        if p_col: columns_to_keep.append(p_col)
            
        df = df[columns_to_keep].copy()
        new_cols = ['item_id', 'name']
        if p_col: new_cols.append('price')
        df.columns = new_cols
        
        df['name'] = df['name'].astype(str).str.strip()
        df = df[(df['name'] != '') & (df['name'] != 'nan') & (df['name'] != 'None')]
        df['item_id'] = df['item_id'].astype(str).str.upper().str.strip().str.replace(r'\.0$', '', regex=True)
        
        # 🌟 安全氣囊：如果有單價欄位就轉成數字，如果沒有就預設為 0
        if 'price' in df.columns:
            df['price'] = pd.to_numeric(df['price'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        else:
            df['price'] = 0
            
        df = df.drop_duplicates(subset=['item_id'], keep='last')
        return df if not df.empty else None
    except:
        return None

def smart_read_file(file_path, default_category):
    df_clean = None
    for enc in ['utf-8-sig', 'cp950', 'big5', 'utf-8']:
        try:
            df_blind = safe_read_csv(file_path, enc)
            temp_df = extract_basic_data(df_blind)
            if temp_df is not None:
                df_clean = temp_df
                break
        except: continue
        
    if df_clean is None:
        try:
            with pd.ExcelFile(file_path) as xls:
                for sheet in xls.sheet_names:
                    df_blind = pd.read_excel(xls, sheet_name=sheet, header=None)
                    temp_df = extract_basic_data(df_blind)
                    if temp_df is not None:
                        df_clean = temp_df
                        break
        except: pass
        
    if df_clean is None: raise ValueError("無法解析。")
    df_clean['cat'] = default_category
    return df_clean

@st.cache_data(ttl=600, show_spinner=False)
def load_sales_data():
    folder_path = "sales_data"
    image_lookup = get_product_images_map()
    combined_list = []
    
    if not os.path.exists(folder_path): os.makedirs(folder_path)
    target_files = [f for f in os.listdir(folder_path) if f.endswith(('.xls', '.xlsx', '.csv')) and not f.startswith('~$')]
    
    for file_name in target_files:
        full_path = os.path.join(folder_path, file_name)
        base_name = file_name.rsplit('.', 1)[0]
        category_name = base_name.split('_')[-1] if '_' in base_name else base_name
        
        try:
            df_excel = smart_read_file(full_path, category_name)
            if df_excel is not None and not df_excel.empty: 
                combined_list.append(df_excel)
        except: pass
            
    if combined_list:
        final_df = pd.concat(combined_list, ignore_index=True)
        final_df = final_df.drop_duplicates(subset=['item_id'], keep='last')
    else:
        final_df = pd.DataFrame(columns=['item_id', 'name', 'cat', 'price'])
        
    # 🌟 雲端自動學習定價：從 daily_records 抓取最新的銷售單價來覆寫舊價格！
    try:
        sheet = get_worksheet()
        if sheet:
            cloud_df = _get_cloud_dataframe(sheet)
            if not cloud_df.empty and 'price' in cloud_df.columns:
                valid_price_df = cloud_df[pd.to_numeric(cloud_df['price'], errors='coerce') > 0].copy()
                if not valid_price_df.empty:
                    valid_price_df = valid_price_df.sort_values(by='date', ascending=True)
                    latest_prices = valid_price_df.groupby('item_id')['price'].last().to_dict()
                    
                    final_df['price'] = final_df.apply(
                        lambda row: latest_prices.get(row['item_id'], row.get('price', 0)), 
                        axis=1
                    )
    except:
        pass
    
    final_df['img'] = final_df['item_id'].apply(lambda x: image_lookup.get(str(x), DEFAULT_IMAGE))
    # 維持向下相容，避免舊程式報錯
    final_df['wd_avg'] = 0 
    final_df['we_avg'] = 0 
    
    return final_df, []
