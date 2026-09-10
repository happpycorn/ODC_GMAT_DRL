import sys
try:
    import gmatpy as gmat
    print("✅ 成功引入 gmatpy！")
    print("GMAT 模組實體位置:", gmat.__file__)
    
    # 印出 gmatpy 裡面實際載入的 C++ 函式與屬性 (前 20 個)
    print("可用的屬性與函式:", dir(gmat)[:20]) 
except ImportError as e:
    print("❌ 載入失敗！", e)