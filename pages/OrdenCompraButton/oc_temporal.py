import streamlit as st
import plotly.express as px

def vista_temporal(df_filtrado):

    st.markdown("## 📈 Análisis Temporal OC")

    serie = (
        df_filtrado
        .groupby("Mes")["TotalBruto"]
        .sum()
        .reset_index()
    )

    fig = px.line(
        serie,
        x="Mes",
        y="TotalBruto",
        markers=True
    )

    st.plotly_chart(fig, use_container_width=True)
