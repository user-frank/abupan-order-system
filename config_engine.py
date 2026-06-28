import pandas as pd
import streamlit as st
import gspread
from record_engine import get_gspread_client, SHEET_NAME

def _get_worksheet(ws_name, headers):
    client = get_gspread_client()
    if not client: 
        st.error("❌ 無法取得 Google Sheets 連線，請檢查憑證。")
        return None
    try:
        spreadsheet = client.open(SHEET_NAME)
        try:
            sheet = spreadsheet.worksheet(ws_name)
        except gspread.WorksheetNotFound:
            sheet = spreadsheet.add_worksheet(title=ws_name, rows="1000", cols="10")
            sheet.append_row(headers)
        return sheet
    except Exception as e:
        st.error(f"❌ 尋找或建立工作表失敗: {e}")
        return None

def _sync_sheet(sheet, df, default_headers):
    try:
        sheet.clear()
        if df.empty:
            data = [default_headers]
        else:
            df_safe = df.fillna("")
            headers = df_safe.columns.astype(str).values.tolist()
            body = df_safe.astype(str).values.tolist()
            data = [headers] + body
            
        try:
            sheet.update('A1', data)
        except:
            sheet.update(values=data)
        return True
    except Exception as e:
        st.error(f"❌ 寫入 Google Sheets 失敗: {str(e)}")
        st.stop() 
        return False

# ==========================================
# 1. 常態菜單 (白名單) 存取 
# ==========================================
@st.cache_data(ttl=3600, show_spinner=False)
def load_menu_template(dept_name):
    headers = ["部門", "item_id"]
    sheet = _get_worksheet("設定_常態菜單", headers)
    if not sheet: return None
    try:
        df = pd.DataFrame(sheet.get_all_records())
        if df.empty: return None
        items = df[df["部門"] == dept_name]["item_id"].astype(str).tolist()
        return items if items else None
    except:
        return None

def save_menu_template(dept_name, item_ids):
    headers = ["部門", "item_id"]
    sheet = _get_worksheet("設定_常態菜單", headers)
    if not sheet: return False
    try:
        df = pd.DataFrame(sheet.get_all_records())
        if not df.empty and "部門" in df.columns:
            df = df[df["部門"] != dept_name] 
        
        new_rows = [{"部門": dept_name, "item_id": str(i)} for i in item_ids]
        if new_rows:
            if df.empty: df = pd.DataFrame(new_rows)
            else: df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
            
        success = _sync_sheet(sheet, df, headers)
        if success: load_menu_template.clear() 
        return success
    except Exception as e:
        st.error(f"❌ 儲存常態菜單失敗: {e}")
        st.stop()
        return False

# ==========================================
# 2. 自訂商品 (新產品) 存取 
# ==========================================
@st.cache_data(ttl=3600, show_spinner=False)
def load_custom_items(dept_name):
    headers = ["部門", "item_id", "品名"]
    sheet = _get_worksheet("設定_自訂商品", headers)
    if not sheet: return []
    try:
        df = pd.DataFrame(sheet.get_all_records())
        if df.empty: return []
        dept_df = df[df["部門"] == dept_name]
        return [{"item_id": str(r["item_id"]), "name": str(r["品名"])} for _, r in dept_df.iterrows()]
    except:
        return []

def save_custom_items(dept_name, items):
    headers = ["部門", "item_id", "品名"]
    sheet = _get_worksheet("設定_自訂商品", headers)
    if not sheet: return False
    try:
        df = pd.DataFrame(sheet.get_all_records())
        if not df.empty and "部門" in df.columns:
            df = df[df["部門"] != dept_name]
            
        new_rows = [{"部門": dept_name, "item_id": str(i["item_id"]), "品名": str(i["name"])} for i in items]
        if new_rows:
            if df.empty: df = pd.DataFrame(new_rows)
            else: df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
            
        success = _sync_sheet(sheet, df, headers)
        if success: load_custom_items.clear()
        return success
    except Exception as e:
        st.error(f"❌ 儲存自訂商品過程發生錯誤: {e}")
        st.stop()
        return False

# ==========================================
# 3. 🌟 新增：子分類設定 (生魚片 vs 小品)
# ==========================================
@st.cache_data(ttl=3600, show_spinner=False)
def load_subcategories(dept_name):
    headers = ["部門", "item_id", "子分類"]
    sheet = _get_worksheet("設定_子分類", headers)
    if not sheet: return {}
    try:
        df = pd.DataFrame(sheet.get_all_records())
        if df.empty: return {}
        dept_df = df[df["部門"] == dept_name]
        # 回傳字典：{"80001": "生魚片區", "80009": "小品區"}
        return dict(zip(dept_df['item_id'].astype(str), dept_df['子分類'].astype(str)))
    except:
        return {}

def save_subcategories(dept_name, subcat_dict):
    headers = ["部門", "item_id", "子分類"]
    sheet = _get_worksheet("設定_子分類", headers)
    if not sheet: return False
    try:
        df = pd.DataFrame(sheet.get_all_records())
        if not df.empty and "部門" in df.columns:
            df = df[df["部門"] != dept_name]
            
        new_rows = [{"部門": dept_name, "item_id": str(k), "子分類": str(v)} for k, v in subcat_dict.items()]
        if new_rows:
            if df.empty: df = pd.DataFrame(new_rows)
            else: df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
            
        success = _sync_sheet(sheet, df, headers)
        if success: load_subcategories.clear()
        return success
    except Exception as e:
        st.error(f"❌ 儲存分類設定發生錯誤: {e}")
        st.stop()
        return False
