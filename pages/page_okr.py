import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# Configuración de página (simulada para el componente)
st.set_page_config(page_title="Tablero OKR - PAC 2026", layout="wide")

# =============================================================================
# 1. GENERACIÓN DE DATOS (MOCK DATA)
# =============================================================================
# Simulamos datos para los 3 Objetivos definidos
data_okr = [
    {"ID": "O1", "Objetivo": "🛡️ Blindar la Planificación (Adherencia)", "KR": "1.1 % Gasto dentro del Plan", "Actual": 82.5, "Meta": 90.0, "Dueño": "Gerencia"},
    {"ID": "O1", "Objetivo": "🛡️ Blindar la Planificación (Adherencia)", "KR": "1.2 % Vinculación Correcta (Link)", "Actual": 96.0, "Meta": 95.0, "Dueño": "Ops"},
    {"ID": "O1", "Objetivo": "🛡️ Blindar la Planificación (Adherencia)", "KR": "1.3 Reducción Compras Urgentes", "Actual": 25.0, "Meta": 40.0, "Dueño": "Compras"}, # 25% de reducción lograda
    
    {"ID": "O2", "Objetivo": "🚀 Excelencia en Ejecución", "KR": "2.1 % Ejecución Presupuestaria", "Actual": 65.0, "Meta": 90.0, "Dueño": "Finanzas"},
    {"ID": "O2", "Objetivo": "🚀 Excelencia en Ejecución", "KR": "2.2 Lead Time Admin (Días)", "Actual": 7.0, "Meta": 5.0, "Dueño": "Ops"}, # Inverso: Menos es mejor
    {"ID": "O2", "Objetivo": "🚀 Excelencia en Ejecución", "KR": "2.3 Líneas 'Zombie' Eliminadas", "Actual": 80.0, "Meta": 100.0, "Dueño": "Compras"},

    {"ID": "O3", "Objetivo": "💰 Maximización de Valor", "KR": "3.1 % Ahorro vs Presupuesto", "Actual": 5.2, "Meta": 8.0, "Dueño": "Sourcing"},
    {"ID": "O3", "Objetivo": "💰 Maximización de Valor", "KR": "3.2 % Consolidación Proveedores", "Actual": 70.0, "Meta": 80.0, "Dueño": "Sourcing"},
]

df_okr = pd.DataFrame(data_okr)

# Cálculo de progreso normalizado (0-1) para las barras
def calcular_progreso(row):
    if "Lead Time" in row['KR']: # Métrica inversa
        # Si actual es 7 y meta es 5, estamos mal. Si actual es 4, estamos al 100%
        # Simplificación para visualización:
        return max(0, min(1, row['Meta'] / row['Actual']))
    else:
        return max(0, min(1, row['Actual'] / row['Meta']))

df_okr["Progreso_Visual"] = df_okr.apply(calcular_progreso, axis=1)
df_okr["Estado"] = df_okr["Progreso_Visual"].apply(lambda x: "🟢 On Track" if x >= 0.8 else ("🟡 Riesgo" if x >= 0.6 else "🔴 Crítico"))

# =============================================================================
# 2. DASHBOARD HEADER & METRICS
# =============================================================================
st.markdown("## 🎯 Tablero de Control OKR: Plan Anual de Compras")
st.markdown("Seguimiento estratégico de Adherencia, Ejecución y Valor.")

# Métricas Globales (Big Numbers)
m1, m2, m3, m4 = st.columns(4)
m1.metric("Adherencia al PAC", "82.5%", "1.2%", help="Gasto total ejecutado dentro del plan")
m2.metric("Ejecución Presupuestaria", "$ 4.2M", "-$800k vs Plan", help="Monto ejecutado vs Planificado a la fecha")
m3.metric("Compras Fuera de Plan", "17.5%", "🔴 +7.5%", help="Objetivo: <10%")
m4.metric("Ahorro Gestionado", "5.2%", "🟡 -2.8%", help="Ahorro sobre presupuesto base")

st.divider()

# =============================================================================
# 3. VISUALIZACIÓN DE OKRs (Tabla Interactiva)
# =============================================================================
col_table, col_chart = st.columns([3, 2])

with col_table:
    st.markdown("### 📋 Detalle de Key Results")
    
    st.dataframe(
        df_okr,
        use_container_width=True,
        hide_index=True,
        column_order=["Objetivo", "KR", "Actual", "Meta", "Progreso_Visual", "Estado"],
        column_config={
            "Objetivo": st.column_config.TextColumn("Objetivo Estratégico", width="medium"),
            "KR": st.column_config.TextColumn("Resultado Clave (KR)", width="medium"),
            "Actual": st.column_config.NumberColumn("Real", format="%.1f"),
            "Meta": st.column_config.NumberColumn("Target", format="%.1f"),
            "Progreso_Visual": st.column_config.ProgressColumn(
                "Avance %",
                format="%.0f%%",
                min_value=0,
                max_value=1,
            ),
            "Estado": st.column_config.TextColumn("Status")
        }
    )

with col_chart:
    st.markdown("### 📊 Adherencia por Categoría (Pareto)")
    # Datos simulados para gráfico
    data_cat = pd.DataFrame({
        "Categoría": ["TI & Software", "Servicios G.", "MRO", "Logística", "Consultoría"],
        "Monto Plan": [100, 80, 60, 40, 20],
        "Monto Fuera Plan": [5, 20, 2, 10, 1]
    })
    
    fig = px.bar(data_cat, x="Categoría", y=["Monto Plan", "Monto Fuera Plan"],
                 title="Planificado vs Fuera de Plan",
                 color_discrete_map={"Monto Plan": "#2ECC71", "Monto Fuera Plan": "#E74C3C"},
                 barmode="group")
    
    fig.update_layout(height=350, margin=dict(t=30, b=0, l=0, r=0))
    st.plotly_chart(fig, use_container_width=True, key="okr_pareto_chart")

# =============================================================================
# 4. ANÁLISIS DE DESVIACIONES (Deep Dive)
# =============================================================================
with st.expander("🔍 Ver Análisis de Desviaciones (Causa Raíz)", expanded=True):
    st.warning("⚠️ Se detectan **12 Órdenes de Compra** críticas fuera de plan esta semana.")
    
    # Simulación de tabla de desviaciones
    df_desviacion = pd.DataFrame({
        "ID OC": ["OC-901", "OC-902", "OC-905"],
        "Descripción": ["Licencias Extra", "Reparación Urgente", "Catering Evento"],
        "Monto": [15000, 4500, 2000],
        "Área": ["Tecnología", "Mantenimiento", "Marketing"],
        "Justificación": ["No presupuestado", "Falla crítica", "Urgencia"],
        "Acción Correctiva": ["Regularizar PAC 2025", "Crear Contrato Marco", "Rechazar futura"]
    })
    
    st.dataframe(
        df_desviacion,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Monto": st.column_config.NumberColumn(format="$ %,.0f")
        }
    )

# Configuración de página (simulada para el componente)
st.set_page_config(page_title="Tablero OKR - PAC 2026", layout="wide")

# =============================================================================
# 1. GENERACIÓN DE DATOS (MOCK DATA)
# =============================================================================
# Simulamos datos para los 3 Objetivos definidos
data_okr = [
    {"ID": "O1", "Objetivo": "🛡️ Blindar la Planificación (Adherencia)", "KR": "1.1 % Gasto dentro del Plan", "Actual": 82.5, "Meta": 90.0, "Dueño": "Gerencia"},
    {"ID": "O1", "Objetivo": "🛡️ Blindar la Planificación (Adherencia)", "KR": "1.2 % Vinculación Correcta (Link)", "Actual": 96.0, "Meta": 95.0, "Dueño": "Ops"},
    {"ID": "O1", "Objetivo": "🛡️ Blindar la Planificación (Adherencia)", "KR": "1.3 Reducción Compras Urgentes", "Actual": 25.0, "Meta": 40.0, "Dueño": "Compras"}, # 25% de reducción lograda
    
    {"ID": "O2", "Objetivo": "🚀 Excelencia en Ejecución", "KR": "2.1 % Ejecución Presupuestaria", "Actual": 65.0, "Meta": 90.0, "Dueño": "Finanzas"},
    {"ID": "O2", "Objetivo": "🚀 Excelencia en Ejecución", "KR": "2.2 Lead Time Admin (Días)", "Actual": 7.0, "Meta": 5.0, "Dueño": "Ops"}, # Inverso: Menos es mejor
    {"ID": "O2", "Objetivo": "🚀 Excelencia en Ejecución", "KR": "2.3 Líneas 'Zombie' Eliminadas", "Actual": 80.0, "Meta": 100.0, "Dueño": "Compras"},

    {"ID": "O3", "Objetivo": "💰 Maximización de Valor", "KR": "3.1 % Ahorro vs Presupuesto", "Actual": 5.2, "Meta": 8.0, "Dueño": "Sourcing"},
    {"ID": "O3", "Objetivo": "💰 Maximización de Valor", "KR": "3.2 % Consolidación Proveedores", "Actual": 70.0, "Meta": 80.0, "Dueño": "Sourcing"},
]

df_okr = pd.DataFrame(data_okr)

# Cálculo de progreso normalizado (0-1) para las barras
def calcular_progreso(row):
    if "Lead Time" in row['KR']: # Métrica inversa
        # Si actual es 7 y meta es 5, estamos mal. Si actual es 4, estamos al 100%
        # Simplificación para visualización:
        return max(0, min(1, row['Meta'] / row['Actual']))
    else:
        return max(0, min(1, row['Actual'] / row['Meta']))

df_okr["Progreso_Visual"] = df_okr.apply(calcular_progreso, axis=1)
df_okr["Estado"] = df_okr["Progreso_Visual"].apply(lambda x: "🟢 On Track" if x >= 0.8 else ("🟡 Riesgo" if x >= 0.6 else "🔴 Crítico"))

# =============================================================================
# 2. DASHBOARD HEADER & METRICS
# =============================================================================
st.markdown("## 🎯 Tablero de Control OKR: Plan Anual de Compras")
st.markdown("Seguimiento estratégico de Adherencia, Ejecución y Valor.")

# Métricas Globales (Big Numbers)
m1, m2, m3, m4 = st.columns(4)
m1.metric("Adherencia al PAC", "82.5%", "1.2%", help="Gasto total ejecutado dentro del plan")
m2.metric("Ejecución Presupuestaria", "$ 4.2M", "-$800k vs Plan", help="Monto ejecutado vs Planificado a la fecha")
m3.metric("Compras Fuera de Plan", "17.5%", "🔴 +7.5%", help="Objetivo: <10%")
m4.metric("Ahorro Gestionado", "5.2%", "🟡 -2.8%", help="Ahorro sobre presupuesto base")

st.divider()

# =============================================================================
# 3. VISUALIZACIÓN DE OKRs (Tabla Interactiva)
# =============================================================================
col_table, col_chart = st.columns([3, 2])

with col_table:
    st.markdown("### 📋 Detalle de Key Results")
    
    st.dataframe(
        df_okr,
        use_container_width=True,
        hide_index=True,
        column_order=["Objetivo", "KR", "Actual", "Meta", "Progreso_Visual", "Estado"],
        column_config={
            "Objetivo": st.column_config.TextColumn("Objetivo Estratégico", width="medium"),
            "KR": st.column_config.TextColumn("Resultado Clave (KR)", width="medium"),
            "Actual": st.column_config.NumberColumn("Real", format="%.1f"),
            "Meta": st.column_config.NumberColumn("Target", format="%.1f"),
            "Progreso_Visual": st.column_config.ProgressColumn(
                "Avance %",
                format="%.0f%%",
                min_value=0,
                max_value=1,
            ),
            "Estado": st.column_config.TextColumn("Status")
        }
    )

with col_chart:
    st.markdown("### 📊 Adherencia por Categoría (Pareto)")
    # Datos simulados para gráfico
    data_cat = pd.DataFrame({
        "Categoría": ["TI & Software", "Servicios G.", "MRO", "Logística", "Consultoría"],
        "Monto Plan": [100, 80, 60, 40, 20],
        "Monto Fuera Plan": [5, 20, 2, 10, 1]
    })
    
    fig = px.bar(data_cat, x="Categoría", y=["Monto Plan", "Monto Fuera Plan"],
                 title="Planificado vs Fuera de Plan",
                 color_discrete_map={"Monto Plan": "#2ECC71", "Monto Fuera Plan": "#E74C3C"},
                 barmode="group")
    
    fig.update_layout(height=350, margin=dict(t=30, b=0, l=0, r=0))
    st.plotly_chart(fig, use_container_width=True)

# =============================================================================
# 4. ANÁLISIS DE DESVIACIONES (Deep Dive)
# =============================================================================
with st.expander("🔍 Ver Análisis de Desviaciones (Causa Raíz)", expanded=True):
    st.warning("⚠️ Se detectan **12 Órdenes de Compra** críticas fuera de plan esta semana.")
    
    # Simulación de tabla de desviaciones
    df_desviacion = pd.DataFrame({
        "ID OC": ["OC-901", "OC-902", "OC-905"],
        "Descripción": ["Licencias Extra", "Reparación Urgente", "Catering Evento"],
        "Monto": [15000, 4500, 2000],
        "Área": ["Tecnología", "Mantenimiento", "Marketing"],
        "Justificación": ["No presupuestado", "Falla crítica", "Urgencia"],
        "Acción Correctiva": ["Regularizar PAC 2025", "Crear Contrato Marco", "Rechazar futura"]
    })
    
    st.dataframe(
        df_desviacion,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Monto": st.column_config.NumberColumn(format="$ %,.0f")
        }
    )