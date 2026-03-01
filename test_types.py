
import pandas as pd
import numpy as np

MESES_ORDER = {
    "enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,
    "julio":7,"agosto":8,"septiembre":9,"octubre":10,"noviembre":11,"diciembre":12,
}

def parse_f(f):
    try:
        p = str(f).strip().lower().split()
        return MESES_ORDER.get(p[0], 0), int(p[1]) if len(p) > 1 else 0
    except Exception:
        return 0, 0

# Mock data like the demo
rng = np.random.default_rng(7)
conceptos_n1 = ["21 GASTOS EN PERSONAL"]
establecimientos = ["DSSO"]
rows = []
for est in establecimientos:
    for year in [2024, 2025]:
        for mes, mnum in MESES_ORDER.items():
            rows.append({
                "Establecimiento": est,
                "Fecha": f"{mes} {year}",
                "Nivel": 1,
                "Concepto Presupuestario": conceptos_n1[0],
                "Devengado": 1000,
                "Ley de Presupuestos": 1100,
            })
df_raw = pd.DataFrame(rows)
df_raw["Nivel"] = pd.to_numeric(df_raw["Nivel"], errors="coerce")
df_raw["Devengado"] = pd.to_numeric(df_raw.get("Devengado", 0), errors="coerce").fillna(0)
df_raw["Ley de Presupuestos"] = pd.to_numeric(df_raw.get("Ley de Presupuestos", 0), errors="coerce").fillna(0)

df1 = df_raw[df_raw["Nivel"] == 1].copy()
df1[["mes_num","anio"]] = pd.DataFrame(df1["Fecha"].apply(parse_f).tolist(), index=df1.index)

print("Types of df1 columns:")
print(df1.dtypes)
print("\nFirst row of Fecha:", type(df1["Fecha"].iloc[0]))
print("First row of anio:", type(df1["anio"].iloc[0]))

fecha_orden = (df1.drop_duplicates("Fecha").sort_values(["anio","mes_num"])["Fecha"].tolist())
print("\nLast fecha_orden element:", fecha_orden[-1], type(fecha_orden[-1]))
