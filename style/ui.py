import streamlit as st

def cargar_css(path="style/style.css"):
    try:
        with open(path) as f:
            css_content = f.read()
            st.markdown(
                f"<style>{css_content}</style>",
                unsafe_allow_html=True
            )
    except FileNotFoundError:
        st.warning("No se encontró el archivo style.css")