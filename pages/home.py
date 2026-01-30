import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import sys
import os
import matplotlib.pyplot as plt
import seaborn as sns

# ===== CARGAR CSS =====
def cargar_css():
    with open("style/style.css", encoding="utf-8") as f:
      st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

cargar_css()


st.set_page_config(
    page_title="Portal DSSO",
    page_icon="logosso.jpg", 
    layout="wide",
    initial_sidebar_state="expanded")


#Titulo
st.title("Abastecimiento DSSO")
st.subheader("Bienvenido al portal de abastecimiento")