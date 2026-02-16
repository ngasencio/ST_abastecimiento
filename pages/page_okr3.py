import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time

# =============================================================================
# CONFIGURACIÓN E INTEGRACIÓN
# =============================================================================
# Instrucciones para main.py:
# 1. Guardar este archivo como 'pages/dash_okr_pac.py'
# 2. Asegurarse de tener las librerías instaladas: pip install plotly pandas streamlit
# 3. El sistema asumirá el estilo global del main.py si existe.

def app():
    st.markdown("## 🎯 Centro de Comando OKR: Plan Anual de Compras")
    st.markdown("Monitor de Adherencia, Ejecución y Valor Estratégico.")

    # =============================================================================
    # 1. DATOS SIMULADOS (MOCK DATA)
    # =============================================================================
    # Simulamos datos conectados al df_filtrado original
    data_okr = [
        {"ID": "O1", "Objetivo": "🛡️ Blindaje Financiero", "KR": "1.1 % Gasto Off-PAC (<10%)", "Actual": 12.4, "Meta": 10.0, "Tipo": "Inverso", "Dueño": "CFO", "Frecuencia": "Semanal"},
        {"ID": "O1", "Objetivo": "🛡️ Blindaje Financiero", "KR": "1.2 Vinculación PAC (>95%)", "Actual": 88.0, "Meta": 95.0, "Tipo": "Directo", "Dueño": "Control", "Frecuencia": "Semanal"},
        {"ID": "O1", "Objetivo": "🛡️ Blindaje Financiero", "KR": "1.3 Reducción Urgencias (-40%)", "Actual": -15.0, "Meta": -40.0, "Tipo": "Directo", "Dueño": "Gte. Compras", "Frecuencia": "Mensual"},
        
        {"ID": "O2", "Objetivo": "🚀 Velocidad Ejecución", "KR": "2.1 Ejecución Presupuesto (90-100%)", "Actual": 65.0, "Meta": 90.0, "Tipo": "Directo", "Dueño": "Gte. Compras", "Frecuencia": "Mensual"},
        {"ID": "O2", "Objetivo": "🚀 Velocidad Ejecución", "KR": "2.2 Lead Time (<5 días)", "Actual": 7.2, "Meta": 5.0, "Tipo": "Inverso", "Dueño": "Ops", "Frecuencia": "Semanal"},
        
        {"ID": "O3", "Objetivo": "💎 Excelencia Valor", "KR": "3.1 Savings/Ahorro (>8%)", "Actual": 5.5, "Meta": 8.0, "Tipo": "Directo", "Dueño": "Sourcing", "Frecuencia": "Trimestral"},
        {"ID": "O3", "Objetivo": "💎 Excelencia Valor", "KR": "3.2 NPS Cliente Interno (>50)", "Actual": 42.0, "Meta": 50.0, "Tipo": "Directo", "Dueño": "Calidad", "Frecuencia": "Semestral"},
    ]
    df_okr = pd.DataFrame(data_okr)

    # Lógica de Progreso Visual (Normalización)
    def calcular_progreso(row):
        if row['Tipo'] == 'Inverso': 
            # Para métricas inversas (ej: Lead Time, Off-PAC), si Actual > Meta es malo.
            # Normalizamos: Meta / Actual (con tope 1.0)
            if row['Actual'] == 0: return 1.0
            return min(1.0, row['Meta'] / row['Actual'])
        else: 
            # Directo
            if row['Meta'] == 0: return 0.0
            return min(1.0, row['Actual'] / row['Meta'])

    df_okr["Progreso"] = df_okr.apply(calcular_progreso, axis=1)
    
    # Estado Semáforo
    def get_status(p):
        if p >= 0.9: return "🟢 On Track"
        if p >= 0.7: return "🟡 Riesgo"
        return "🔴 Crítico"
    
    df_okr["Estado"] = df_okr["Progreso"].apply(get_status)

    # =============================================================================
    # 2. FILTROS Y BARRA LATERAL (Reportabilidad)
    # =============================================================================
    with st.sidebar:
        st.header("👤 Perfil de Usuario")
        perfil = st.selectbox(
            "Selecciona tu Rol:",
            ["Gerencia General / CFO", "Gerente de Compras", "Analista / Operativo"],
            index=1
        )
        
        st.divider()
        st.header("📄 Generador de Reportes")
        st.caption("Descarga de reportes obligatorios")
        
        rep_type = st.selectbox("Frecuencia:", ["Semanal (Radar)", "Mensual (Flash)", "Trimestral (QBR)", "Semestral (Prov)", "Anual (Cierre)"])
        
        if st.button(f"Generar Reporte {rep_type.split()[0]}"):
            with st.spinner("Compilando KPIs y Análisis..."):
                time.sleep(1) # Simulación de proceso
            st.success(f"Reporte {rep_type} generado exitosamente.")
            st.download_button("⬇️ Descargar PDF", data="Simulacion PDF", file_name=f"Reporte_{rep_type}.pdf")

    # =============================================================================
    # 3. VISUALIZACIÓN POR PERFIL
    # =============================================================================
    
    # --- KPIs MACRO (Big Numbers) ---
    st.markdown("### 1. Termómetro Estratégico")
    k1, k2, k3, k4 = st.columns(4)
    
    # Datos dinámicos según perfil (Simulación de foco)
    if perfil == "Gerencia General / CFO":
        k1.metric("Adherencia PAC", "87.6%", "-2.4%", help="Objetivo: Blindaje Financiero")
        k2.metric("Gasto Off-PAC", "$1.2M", "🔴 +12% vs Meta", help="Dinero gastado fuera de planificación")
        k3.metric("Ahorro Acumulado", "$450k", "🟡 5.5% (Meta 8%)")
        k4.metric("Ejecución Global", "65%", "En Plan")
    elif perfil == "Analista / Operativo":
        k1.metric("Lead Time Promedio", "7.2 días", "🔴 +2.2 días", help="Meta: 5 días")
        k2.metric("OCs Sin Vínculo", "15", "Requieren corrección")
        k3.metric("Líneas Zombie", "45", "Limpieza pendiente")
        k4.metric("NPS Interno", "42", "🟡 Mejorable")
    else: # Gerente Compras (Visión Balanceada)
        k1.metric("Ejecución PAC", "65%", "🟡 Riesgo Subejecución")
        k2.metric("Compras Urgentes", "18%", "🔴 Alta incidencia")
        k3.metric("Lead Time", "7.2 días", "Lento")
        k4.metric("Eficiencia (Ahorro)", "5.5%", "Bajo")

    st.divider()

    # --- TABLA DE GESTIÓN OKR ---
    st.markdown("### 2. Monitor de Objetivos (Live)")
    
    # Filtro de visualización
    cols_to_show = ["Objetivo", "KR", "Actual", "Meta", "Progreso", "Estado", "Dueño"]
    if perfil == "Analista / Operativo":
        # Operativos ven sus KRs específicos
        df_display = df_okr[df_okr["Dueño"].isin(["Ops", "Control", "Calidad"])]
    elif perfil == "Gerencia General / CFO":
        # CFO ve financieros y estratégicos
        df_display = df_okr[df_okr["Dueño"].isin(["CFO", "Sourcing", "Gte. Compras"])]
    else:
        df_display = df_okr # Gerente ve todo

    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Objetivo": st.column_config.TextColumn("Objetivo Estratégico", width="medium"),
            "KR": st.column_config.TextColumn("Key Result", width="large"),
            "Actual": st.column_config.NumberColumn("Valor Real", format="%.1f"),
            "Meta": st.column_config.NumberColumn("Target", format="%.1f"),
            "Progreso": st.column_config.ProgressColumn(
                "Cumplimiento",
                format="%.0f%%",
                min_value=0,
                max_value=1,
            ),
            "Estado": st.column_config.TextColumn("Status"),
        }
    )

    # --- ANÁLISIS GRÁFICO ---
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("#### 📊 Desviación Presupuestaria (Pareto)")
        # Simulación datos pareto
        df_pareto = pd.DataFrame({
            "Gerencia": ["TI", "Marketing", "Operaciones", "RRHH", "Finanzas"],
            "Gasto Off-PAC": [45000, 32000, 15000, 8000, 2000]
        })
        fig = px.bar(df_pareto, x="Gerencia", y="Gasto Off-PAC", 
                     title="Top Áreas con Compras No Planificadas",
                     color="Gasto Off-PAC", color_continuous_scale="Reds")
        st.plotly_chart(fig, use_container_width=True, key="chart_pareto_offpac")
    
    with c2:
        st.markdown("#### 📉 Tendencia de Ejecución")
        # Simulación datos tendencia
        df_trend = pd.DataFrame({
            "Mes": ["Ene", "Feb", "Mar", "Abr", "May"],
            "Planificado": [100, 200, 300, 400, 500],
            "Ejecutado": [90, 180, 250, 320, 380] # Subejecución visible
        })
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=df_trend["Mes"], y=df_trend["Planificado"], name="Planificado (PAC)", line=dict(dash='dot')))
        fig2.add_trace(go.Scatter(x=df_trend["Mes"], y=df_trend["Ejecutado"], name="Ejecutado (Real)", fill='tozeroy'))
        fig2.update_layout(title="Curva S: Plan vs Real Acumulado", xaxis_title="Mes", yaxis_title="Monto ($)")
        st.plotly_chart(fig2, use_container_width=True, key="chart_trend_s")

    # --- SECCIÓN DE ACCIÓN (ALERTAS) ---
    st.markdown("### 🚨 Acciones Requeridas")
    
    col_alerta, col_accion = st.columns([3, 1])
    with col_alerta:
        st.warning("**Desviación Crítica:** El área de **TI** ha consumido el 40% de su presupuesto anual en compras urgentes (Off-PAC).")
    with col_accion:
        if st.button("Enviar Alerta a Gerente TI"):
            st.toast("📧 Correo de advertencia enviado a Gerencia TI", icon="✅")

# Si se ejecuta directamente
if __name__ == "__main__":
    app()