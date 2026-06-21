import pandas as pd
import os
import streamlit as st
import time  # 🛡️ 新增：防撞計時器

# ==========================================
# 圖片路徑與 Fallback 設定 
# ==========================================
IMAGE_BASE_DIR = "product_images"
DEFAULT_IMAGE = "https://images.unsplash.com/photo-1615141982883-c7ad0e69fd62?w=600&q=80"

def get_product_images_map():
    """
    【防彈版智慧料號抓圖引擎】：自動修復手誤、多餘空白、雙重副檔名與大小寫問題。
    """
    image_lookup = {}
    if not os.path.exists(IMAGE_BASE_DIR):
        return image_lookup

    for root, dirs, files in os.walk(IMAGE_BASE_DIR):
        for file in files:
            if file.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                item_id, _ = os.path.splitext(file)
                
                # 【防呆大絕招】：
                # 1. 轉大寫 (A1001 == a1001)
                # 2. 去除手誤多打的副檔名 (解決 80019.jpg.jpg 變成 80019.jpg 的問題)
                # 3. 去除前後空白
                clean_id = str(item_id).upper()
                clean_id = clean_id.replace('.JPG', '').replace('.PNG', '').replace('.JPEG', '').replace('.WEBP', '')
                clean_id = clean_id.strip()
                
                final_path = os.path.join(root, file).replace("\\", "/")
                image_lookup[clean_id] = final_path
                
    return image_lookup

def extract_target_data(df_blind):
    try:
        header_idx = -1
        for idx, row in df_blind.iterrows():
            # 老闆的精準版：強制轉字串防當機
            row_str = [str(val) for val in row.values]
            has_name = any('品名' in s or '商品名稱' in s for s in row_str)
            has_qty = any('數' in s or '量' in s or '合計' in s for s in row_str)
            has_id = any('編號' in s or '品號' in s for s in row_str)
            if has_name and has_qty and has_id:
                header_idx = idx
                break
        
        if header_idx == -1: 
            return None
            
        df = df_blind.iloc[header_idx+1:].copy()
        df.columns = df_blind.iloc[header_idx].astype(str).values
        df = df.loc[:, ~df.columns.duplicated()]
        
        cols = df.columns
        id_col = next((c for c in cols if '編號' in c or '品號' in c), None)
        d_col = next((c for c in cols if '日' in c or '期' in c), None)
        n_col = next((c for c in cols if '品名' in c or '商品名稱' in c), None)
        q_col = next((c for c in cols if '數' in c or '量' in c or '合計' in c), None)
        
        if not (d_col and n_col and q_col and id_col): 
            return None
            
        df = df[[d_col, id_col, n_col, q_col]].copy()
        df.columns = ['date', 'item_id', 'name', 'qty']
        
        df['date'] = df['date'].astype(str).str.strip().replace(r'^\s*$', pd.NA, regex=True).replace('nan', pd.NA).replace('None', pd.NA)
        df['date'] = df['date'].ffill()
        
        df['name'] = df['name'].astype(str).str.strip()
        df = df[(df['name'] != '') & (df['name'] != 'nan') & (df['name'] != 'None')]
        df = df[~df['name'].str.contains('計|總|小計|全部|\\(全部\\)', na=False)]
        
        # 清洗 ERP 料號，轉大寫並去除 .0
        df['item_id'] = df['item_id'].astype(str).str.upper().str.strip().str.replace(r'\.0$', '', regex=True)
        
        df['qty'] = pd.to_numeric(df['qty'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        
        numeric_dates = pd.to_numeric(df['date'], errors='coerce')
        excel_dates = pd.to_datetime(numeric_dates, unit='D', origin='1899-12-30', errors='coerce')
        string_dates = pd.to_datetime(df['date'], errors='coerce')
        df['date'] = excel_dates.fillna(string_dates)
        
        df = df.dropna(subset=['date'])
        return df if not df.empty else None
        
    except Exception as e:
        return None

# ==========================================
# 🛡️ 檔案讀取防撞避震器 (終極解鎖版)
# ==========================================
def safe_read_csv(file_path, enc, retries=3, delay=0.2):
    """強制使用 with open 確保 Windows 絕對釋放檔案鎖"""
    for attempt in range(retries):
        try:
            # 使用 with open 保證讀完立刻關閉檔案，絕不佔用
            with open(file_path, 'r', encoding=enc) as f:
                return pd.read_csv(f, header=None, engine='python', on_bad_lines='skip')
        except Exception as e:
            if attempt == retries - 1:
                raise e
            time.sleep(delay)

# ==========================================
# 核心解析引擎
# ==========================================
def smart_read_file(file_path, default_category, image_lookup):
    df_clean = None
    
    # 🚀 策略反轉：正航的 .xls 其實是偽裝的 CSV，我們先用 CSV 引擎暴力破解！
    for enc in ['utf-8-sig', 'cp950', 'big5', 'utf-8']:
        try:
            df_blind = safe_read_csv(file_path, enc)
            temp_df = extract_target_data(df_blind)
            if temp_df is not None:
                df_clean = temp_df
                break
        except Exception: 
            continue
            
    # 如果 CSV 引擎失敗，我們才用真正的 Excel 引擎去讀
    if df_clean is None:
        try:
            for attempt in range(3):
                try:
                    # 使用 with 確保檔案讀取後立刻關閉，絕不殘留佔用
                    with pd.ExcelFile(file_path) as xls:
                        for sheet in xls.sheet_names:
                            df_blind = pd.read_excel(xls, sheet_name=sheet, header=None)
                            temp_df = extract_target_data(df_blind)
                            if temp_df is not None:
                                if '明細' in sheet or df_clean is None: 
                                    df_clean = temp_df
                    break # 成功就跳出重試迴圈
                except Exception as e:
                    if attempt == 2:
                        raise e
                    time.sleep(0.2)
        except Exception: 
            pass
            
    if df_clean is None:
        raise ValueError("無法解析。")
        
    # === 以下維持您原本的完美計算邏輯不變 ===
    df_clean['is_weekend'] = df_clean['date'].dt.dayofweek >= 5
    
    total_wd_days = df_clean[~df_clean['is_weekend']]['date'].nunique()
    total_we_days = df_clean[df_clean['is_weekend']]['date'].nunique()
    
    wd_sales = df_clean[~df_clean['is_weekend']].groupby(['item_id', 'name'])['qty'].sum().reset_index()
    wd_sales['wd_avg'] = (wd_sales['qty'] / total_wd_days).round(1) if total_wd_days > 0 else 0
    
    we_sales = df_clean[df_clean['is_weekend']].groupby(['item_id', 'name'])['qty'].sum().reset_index()
    we_sales['we_avg'] = (we_sales['qty'] / total_we_days).round(1) if total_we_days > 0 else 0
    
    summary = pd.merge(wd_sales[['item_id', 'name', 'wd_avg']], we_sales[['item_id', 'name', 'we_avg']], on=['item_id', 'name'], how='outer').fillna(0)
    
    total_sales = df_clean.groupby(['item_id', 'name'])['qty'].sum().reset_index()
    summary = pd.merge(summary, total_sales, on=['item_id', 'name'], how='outer').fillna(0)
    summary.rename(columns={'qty': 'total_sales'}, inplace=True)
    
    max_date = df_clean['date'].max()
    cm_df = df_clean[(df_clean['date'].dt.year == max_date.year) & (df_clean['date'].dt.month == max_date.month)]
    cm_sales = cm_df.groupby(['item_id', 'name'])['qty'].sum().reset_index()
    cm_sales.rename(columns={'qty': 'cm_sales'}, inplace=True)
    
    summary = pd.merge(summary, cm_sales, on=['item_id', 'name'], how='left').fillna(0)
    summary['cat'] = default_category
    
    df_clean['item_id'] = df_clean['item_id'].astype(str).str.upper().str.strip()
    summary['img'] = summary['item_id'].apply(lambda x: image_lookup.get(str(x), DEFAULT_IMAGE))
    
    return summary

@st.cache_data(show_spinner=False)
def load_sales_data():
    folder_path = "sales_data"
    error_logs = []
    if not os.path.exists(folder_path): 
        os.makedirs(folder_path)
        
    image_lookup = get_product_images_map()
    
    # 🛡️ 增加防呆：排除 `~$` 開頭的 Excel 隱藏暫存檔
    target_files = [f for f in os.listdir(folder_path) if f.endswith(('.xls', '.xlsx', '.csv')) and not f.startswith('~$')]
    combined_list = []
    
    for file_name in target_files:
        full_path = os.path.join(folder_path, file_name)
        base_name = file_name.rsplit('.', 1)[0]
        category_name = base_name.split('_')[-1] if '_' in base_name else base_name
            
        try:
            df_excel = smart_read_file(full_path, category_name, image_lookup)
            if not df_excel.empty: 
                combined_list.append(df_excel)
        except Exception as e:
            error_logs.append({"file": file_name, "reason": str(e)})
            
    if combined_list:
        final_df = pd.concat(combined_list, ignore_index=True)
        agg_funcs = {'wd_avg':'mean', 'we_avg':'mean', 'total_sales':'sum', 'cm_sales':'sum'}
        final_df = final_df.groupby(['item_id', 'name', 'cat', 'img']).agg(agg_funcs).reset_index()
        final_df = final_df[final_df['total_sales'] > 0]
        return final_df.sort_values(by="total_sales", ascending=False), error_logs
        
    return pd.DataFrame(), error_logs
