import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from style.ui import cargar_css


# =============================================================================
# CONFIGURACIÓN INICIAL
# =============================================================================

cargar_css()

# Configuración de página
st.set_page_config(page_title="OKR Center - PAC 2026", layout="wide")

# =============================================================================
# 1. SIMULACIÓN DE DATOS (MOCK DATA)
# =============================================================================
# Datos de OKRs
data_okr = [
    {"ID": "O1", "Objetivo": "🛡️ Blindar Planificación", "KR": "1.1 % Gasto Off-PAC (Meta <10%)", "Actual": 12.5, "Meta": 10.0, "Tipo": "Inverso", "Dueño": "CFO"},
    {"ID": "O1", "Objetivo": "🛡️ Blindar Planificación", "KR": "1.2 % Link Solicitud-PAC", "Actual": 88.0, "Meta": 95.0, "Tipo": "Directo", "Dueño": "Control"},
    {"ID": "O1", "Objetivo": "🛡️ Blindar Planificación", "KR": "1.3 Reducción Urgencias", "Actual": 15.0, "Meta": 40.0, "Tipo": "Directo", "Dueño": "Gte. Compras"},
    
    {"ID": "O2", "Objetivo": "🚀 Excelencia Ejecución", "KR": "2.1 % Ejecución Presupuesto", "Actual": 65.0, "Meta": 90.0, "Tipo": "Directo", "Dueño": "Jefe Abast."},
    {"ID": "O2", "Objetivo": "🚀 Excelencia Ejecución", "KR": "2.2 Lead Time (Días)", "Actual": 8.0, "Meta": 5.0, "Tipo": "Inverso", "Dueño": "Ops"},
    {"ID": "O2", "Objetivo": "🚀 Excelencia Ejecución", "KR": "2.3 Líneas Zombie (Reducción)", "Actual": 45.0, "Meta": 0.0, "Tipo": "Inverso", "Dueño": "Planif."},

    {"ID": "O3", "Objetivo": "💰 Maximización Valor", "KR": "3.1 % Ahorro Real", "Actual": 6.2, "Meta": 8.0, "Tipo": "Directo", "Dueño": "Sourcing"},
    {"ID": "O3", "Objetivo": "💰 Maximización Valor", "KR": "3.2 % Pareto Proveedores", "Actual": 70.0, "Meta": 80.0, "Tipo": "Directo", "Dueño": "Sourcing"},
]
df_okr = pd.DataFrame(data_okr)

# Función para calcular progreso visual (0-1)
def calcular_progreso(row):
    if row['Tipo'] == 'Inverso': # Para métricas donde "menos es mejor" (ej: % Off-PAC, Lead Time)
        # Si Actual > Meta, estamos mal. Calculamos qué tan lejos estamos.
        # Ejemplo Lead Time: Actual 8, Meta 5. Progreso = 5/8 = 0.62
        if row['Actual'] == 0: return 1.0
        return min(1.0, row['Meta'] / row['Actual'])
    else: # Directo: Más es mejor
        if row['Meta'] == 0: return 0.0
        return min(1.0, row['Actual'] / row['Meta'])

df_okr["Progreso_Visual"] = df_okr.apply(calcular_progreso, axis=1)
df_okr["Estado"] = df_okr["Progreso_Visual"].apply(lambda x: "🟢 On Track" if x >= 0.8 else ("🟡 Riesgo" if x >= 0.6 else "🔴 Crítico"))

# =============================================================================
# 2. HEADER & FILTRO DE PERFIL
# =============================================================================
st.markdown("## 🎯 Centro de Comando OKR: Plan Anual de Compras")
st.markdown("**Problema que resuelve:** Centralización de métricas para evitar desviaciones y asegurar ejecución.")

# Selector de Perfil para personalizar la vista
perfil = st.selectbox(
    "👤 Seleccione su Perfil de Usuario:",
    ["Visión General (Todos)", "Dirección Financiera (CFO)", "Gerencia de Compras", "Analista / Operativo"],
    help="Filtra la información relevante para tomar decisiones específicas por rol."
)

st.divider()

# =============================================================================
# 3. SECCIÓN 1: METRICAS ESTRATÉGICAS (Big Numbers)
# =============================================================================
# Usuario: CFO / Gerencia
# Decisión: Aprobar presupuesto extra o exigir recortes.

if perfil in ["Visión General (Todos)", "Dirección Financiera (CFO)", "Gerencia de Compras"]:
    st.subheader("1. Salud del Plan (KPIs Estratégicos)")
    m1, m2, m3, m4 = st.columns(4)
    
    # KPIs simulados
    m1.metric("Adherencia al PAC", "87.5%", "-2.5% vs Meta", help="KR 1.1: Gasto dentro del plan")
    m2.metric("Compras Off-PAC", "$ 145k", "🔴 Crítico", help="Monto total gastado sin planificación")
    m3.metric("Ejecución Acumulada", "65%", "🟡 -25% vs Q3", help="KR 2.1: Ritmo de gasto")
    m4.metric("Ahorro Capturado", "6.2%", "🟡 -1.8%", help="KR 3.1: Ahorro sobre presupuesto")
    
    st.divider()

# =============================================================================
# 4. SECCIÓN 2: DETALLE DE OKRs (Tabla de Gestión)
# =============================================================================
# Usuario: Todos
# Problema: Visibilidad del desempeño de cada KR.

col_okr, col_graf = st.columns([3, 2])

with col_okr:
    st.markdown("### 📋 Monitor de Key Results")
    st.caption("Barra de progreso normalizada hacia la meta.")
    
    # Filtro de datos según perfil (opcional, aquí mostramos todo para contexto)
    st.dataframe(
        df_okr,
        use_container_width=True,
        hide_index=True,
        column_order=["Objetivo", "KR", "Actual", "Meta", "Progreso_Visual", "Estado", "Dueño"],
        column_config={
            "Objetivo": st.column_config.TextColumn("Objetivo Estratégico", width="medium"),
            "KR": st.column_config.TextColumn("Resultado Clave", width="medium"),
            "Actual": st.column_config.NumberColumn("Real", format="%.1f"),
            "Meta": st.column_config.NumberColumn("Target", format="%.1f"),
            "Progreso_Visual": st.column_config.ProgressColumn(
                "Cumplimiento",
                format="%.0f%%",
                min_value=0,
                max_value=1,
            ),
            "Estado": st.column_config.TextColumn("Status"),
            "Dueño": st.column_config.TextColumn("Responsable")
        }
    )

# =============================================================================
# 5. SECCIÓN 3: ANÁLISIS DE CAUSA RAÍZ (Gráficos)
# =============================================================================
# Usuario: Gerencia de Compras / Analistas
# Decisión: Identificar dónde atacar (Pareto).

with col_graf:
    if perfil in ["Dirección Financiera (CFO)"]:
        st.markdown("### 💸 Fuga de Presupuesto por Área")
        # Datos para CFO: Dónde se gasta fuera de plan
        df_fuga = pd.DataFrame({
            "Área": ["Marketing", "Mantenimiento", "TI", "RRHH"],
            "Monto Off-PAC": [50000, 35000, 15000, 10000]
        })
        fig_fuga = px.pie(df_fuga, values="Monto Off-PAC", names="Área", title="Distribución de Gasto No Planificado", hole=0.4)
        st.plotly_chart(fig_fuga, use_container_width=True, key="chart_cfo_fuga")
        
    elif perfil in ["Analista / Operativo", "Gerencia de Compras"]:
        st.markdown("### ⏱️ Cuellos de Botella (Lead Time)")
        # Datos para Ops: Quién se tarda más
        df_lt = pd.DataFrame({
            "Comprador": ["Ana", "Carlos", "Luis", "Maria"],
            "Días Promedio": [8.5, 4.2, 5.1, 3.8],
            "Target": [5, 5, 5, 5]
        })
        fig_lt = px.bar(df_lt, x="Comprador", y="Días Promedio", title="Lead Time por Comprador vs Meta (5 días)",
                        color="Días Promedio", color_continuous_scale="RdYlGn_r") # Rojo si es alto
        fig_lt.add_hline(y=5, line_dash="dot", annotation_text="Meta (5 días)")
        st.plotly_chart(fig_lt, use_container_width=True, key="chart_ops_lt")
        
    else: # Visión General
        st.markdown("### 📊 Estado General de KRs")
        fig_gen = px.bar(df_okr, x="Dueño", y="Progreso_Visual", color="Estado", title="Cumplimiento por Responsable")
        st.plotly_chart(fig_gen, use_container_width=True, key="chart_general_krs")

# =============================================================================
# 6. SECCIÓN 4: ALERTAS DE ACCIÓN INMEDIATA
# =============================================================================
# Usuario: Operativo / Gerencia
# Problema: Falta de acción sobre desviaciones.
# Decisión: Corrección inmediata.

st.markdown("### 🚨 Radar de Desviaciones (Acción Requerida)")
c1, c2 = st.columns(2)

with c1:
    st.info("⚠️ **Compras Off-PAC Detectadas (Semana actual):** 8 órdenes por $12,500. Área crítica: Marketing.")
    st.button("Ver Detalle y Bloquear", key="btn_off_pac")

with c2:
    st.warning("⚠️ **Líneas PAC en Riesgo:** 15 líneas de 'Infraestructura' no tienen OC y vencen en 10 días.")
    st.button("Notificar a Compradores", key="btn_zombie")