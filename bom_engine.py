import pandas as pd
import os

def calculate_bom(cart_items):
    """
    未來這裡將專門處理 BOM (Bill of Materials) 邏輯。
    全面採用「商品編號 (item_id)」作為唯一對應鍵，不怕品名打錯。
    """
    bom_file = "bom_data.xlsx" # 您未來準備要放進來的原料對應表
    
    if not cart_items:
        return pd.DataFrame()

    # 如果未來您放了真實的 BOM 表，這裡的邏輯就會啟動去讀取它
    if os.path.exists(bom_file):
        # TODO: 未來讀取 Excel 並與 cart_items 進行 join 計算
        pass

    # 目前沒有檔案，回傳乾淨的提示介面，不做任何假數據白工
    return pd.DataFrame({
        "系統狀態": ["等待匯入中"],
        "說明": ["請於資料夾放入『bom_data.xlsx』。系統將自動依據【商品編號】展開原料計算。"]
    })
