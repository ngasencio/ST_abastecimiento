import streamlit as st

def vista_recepciones(df_filtrado):

    st.markdown("## ✅ Recepciones Conformes")

    ok = df_filtrado[
        df_filtrado["EstadoOC"] == "Recepcion Conforme"
    ]

    st.dataframe(ok, use_container_width=True)
