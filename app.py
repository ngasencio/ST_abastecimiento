import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime


st.set_page_config(
    page_title="Dashboard DSSO",
    page_icon=":bar_chart:", 
    layout="wide",
    initial_sidebar_state="expanded")




# Importas Datos
def generar_datos_empresa():
    fechas = pd.date_range(start="2024-01-01", end=datetime.today(), freq='D')
    datos = {
        "Fecha": fechas,
        "ingresos_diarios": np.random.normal(50000, 15000, size=len(fechas)),
        "usuarios_activos": np.random.normal(12000, 3000, size=len(fechas)),
        "conversion_rate": np.random.normal(2.5, 0.8, size=len(fechas)),
        "costo_adquisicion": np.random.normal(45, 12, size=len(fechas)),
        "ltv_cliente": np.random.normal(180, 40, size=len(fechas)),
    }
    
    df=pd.DataFrame(datos)
    df["ingresos_diarios"] *= (1+ np.arange(len(df)) * 0.0001) #tendencia creciente
    return df

df = generar_datos_empresa()

#Titulo
st.markdown("<h1 class='main-header'>📊 Dashboard DSSO</h1>", unsafe_allow_html=True)

st.write("""
Este informe presenta una visión ejecutiva del desempeño operacional y financiero,
considerando los principales indicadores de la organización.
""")

#filtros
col1, col2, col3 = st.columns(3)
with col1:
    periodo = st.selectbox("📅 Período",
                    ["Últimos 30 días", "Último trimestre", "Último año"])
with col2:
    categoria = st.selectbox("📊 Categoría",
                    ["General", "Ventas", "Marketing", "Producto"])
with col3:
    comparacion = st.selectbox("📈 Comparar con:",
                    ["Periodo anterior", "Año pasado", "Promedio"])


##### KPIS ####
st.markdown("## 📈 KPIs Principales")
col1, col2, col3, col4 = st.columns(4)
with col1:
    ingresos_totales = df["ingresos_diarios"].sum()
    st.metric("💰 Ingresos Totales", 
            f"${ingresos_totales:,.0f}",
            f"{np.random.uniform(5, 15):.1f}%")
    
with col2:
    usuarios_prom = df["usuarios_activos"].mean()
    st.metric("👥  Usuarios Activos", 
            f"{usuarios_prom:,.0f}",
            f"{np.random.uniform(2, 8):.1f}%")

with col3:
    conversion_prom = df["conversion_rate"].mean()
    st.metric("🎯 Tasa de Conversión", 
            f"{conversion_prom:.2f}%",
            f"{np.random.uniform(0.5, 2):.1f}%")
    
with col4:
    cac_prom = df["costo_adquisicion"].mean()
    st.metric("💸Costo de Adquisición", 
            f"${cac_prom:.2f}",
            f"-{np.random.uniform(1, 5):.1f}%")
    


##### GRAFICOS ####
st.markdown("## 📊 Análisis Detallado")

col1, col2 = st.columns(2)
with col1:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Fecha"], y=df["ingresos_diarios"],mode="lines+markers", name="Ingresos Reales", line=dict(color='blue')))
    z = np.polyfit(np.arange(len(df)), df["ingresos_diarios"], 1)
    p = np.poly1d(z)
    fig.add_trace(go.Scatter(x=df["Fecha"], y=p(np.arange(len(df))), mode="lines", name="Tendencia", line=dict(color='orange', dash='dash')))
    fig.update_layout(title="💰 Ingresos Diarios con Tendencia", height=400, template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)
    
with col2:
    etapas = ['Visitantes', 'Leads', 'Oportunidades', 'Clientes']
    valores = [10000, 2500, 625, 156]
    funenel = go.Figure(go.Funnel(y=etapas, x=valores, textinfo="value+percent initial"))
    funenel.update_layout(title="🎯 Embudo de Conversión", height=400, template="plotly_white")
    st.plotly_chart(funenel, use_container_width=True)    
    

st.markdown("## 🌎 Mapa de Calor Geografico")
paises = ["Mexico", "Colombia", "Argentina", "Chile", "Peru", "Brasil"]
ventas_pais = np.random.randint(1000, 10000, size=len(paises))
mapa = px.bar(x=paises, y=ventas_pais, color=ventas_pais, color_continuous_scale="viridis", labels={"x":"País", "y":"Ventas"}, title="💵 Ventas por País")
mapa.update_layout(height=400, template="plotly_white", showlegend=True)
st.plotly_chart(mapa, use_container_width=True)


st.markdown("## 🚦 Centro de Alertas Inteligentes")
alertas = []

if df["ingresos_diarios"].tail(7).mean() < df["ingresos_diarios"].head(-7).mean():
    alertas.append({'tipo': "⚠️ Alerta: Ingresos diarios por debajo del promedio en 7 dias.", 'color': "orange"})

if df["conversion_rate"].tail(1).iloc[0] < 2.0:
    alertas.append({'tipo': "❗ Alerta: Tasa de conversión ha caído por debajo del 2% en la última semana.", 'color': "red"})

if df["usuarios_activos"].tail(1).iloc[0] > df["usuarios_activos"].quantile(0.9):
    alertas.append({'tipo': "✅ Notificación: Usuarios activos han superado el 90 percentil.", 'color': "green"})
    
for alerta in alertas:
    st.markdown(f"""<div style="padding: 1rem; margin:0.5rem 0; background-color: {alerta['color']}; color: white; border-radius: 10px; font-weight: bold;">{alerta['tipo']}:{alerta['tipo']}</div>""", unsafe_allow_html=True)
    
    
st.markdown("## 📅 Tabla de Datos")
with st.expander(" 📅Ver Datos Completos"):
    st.dataframe(df.style.format({
        # --- CAMBIO AQUÍ: Eliminar .dt ---
        "Fecha": lambda x: x.strftime("%Y-%m-%d"), 
        # -----------------------------------
        "ingresos_diarios": "${:,.2f}".format,
        "usuarios_activos": "{:,.0f}".format,
        "conversion_rate": "{:.2f}%".format,
        "costo_adquisicion": "${:.2f}".format,
        "ltv_cliente": "${:.2f}".format,
    }), height=400)