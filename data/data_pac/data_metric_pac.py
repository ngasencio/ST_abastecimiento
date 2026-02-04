import pandas as pd

def calculate_pac_performance(df_validado):
    total = len(df_validado)
    if total == 0:
        return 0, 0, 0
        
    dentro = len(df_validado[df_validado["En_PAC_2026"] == "Sí"])
    fuera = len(df_validado[df_validado["En_PAC_2026"] == "No"])
    pct = (dentro / total) * 100
    
    return pct, dentro, fuera