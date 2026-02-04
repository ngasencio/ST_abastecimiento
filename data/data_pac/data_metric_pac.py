import pandas as pd

def calculate_pac_performance(df):
    """Retorna métricas de cumplimiento PAC."""
    if "En_PAC_2026" not in df.columns:
        return 0, 0, 0
        
    total = len(df)
    if total == 0:
        return 0, 0, 0
        
    dentro = len(df[df["En_PAC_2026"] == "Sí"])
    fuera = total - dentro
    pct_cumplimiento = (dentro / total) * 100
    
    return pct_cumplimiento, dentro, fuera