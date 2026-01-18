import streamlit as st
import plotly.express as px

def vista_proveedores(df_filtrado):

    st.markdown("## 📦 Análisis de Proveedores")

    top = (
        df_filtrado
        .groupby("Proveedor")["TotalBruto"]
        .sum()
        .reset_index()
        .sort_values("TotalBruto", ascending=False)
        .head(10)
    )

    fig = px.bar(
        top,
        x="TotalBruto",
        y="Proveedor",
        orientation="h",
        title="Top 10 Proveedores por Monto"
    )

    st.plotly_chart(fig, use_container_width=True)
