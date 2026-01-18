import streamlit as st

def vista_ultimas(df_filtrado):

    st.markdown("## 🧾 Últimas OC Emitidas")

    ultimas = (
        df_filtrado
        .sort_values("FechaCreacion", ascending=False)
        .head(20)
    )

    st.dataframe(ultimas, use_container_width=True)
