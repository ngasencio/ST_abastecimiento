import streamlit as st
import os
import pandas as pd

# ===== CARGAR CSS =====
def cargar_css():
    try:
        with open("style/style.css") as f:
            # Usamos una sola línea y eliminamos espacios innecesarios con .strip()
            css_content = f.read().replace("\n", "").strip()
            st.markdown(
                f"<style>{css_content}</style>", 
                unsafe_allow_html=True
            )
    except FileNotFoundError:
        st.error("⚠️ No se encontró el archivo style.css")

# Llama a la función al principio de todo, justo después de st.set_page_config
cargar_css()


# =============================================================================
# CONFIGURACIÓN
# =============================================================================
st.set_page_config(page_title="Repositorio Documental", layout="wide")

# Ruta a la carpeta de documentos (Ajustada a tu estructura)
BASE_DOC_PATH = os.path.join("resources", "Documentos")

# LISTA MAESTRA DE DOCUMENTOS
# Agrega aquí nuevos archivos. El sistema agrupará automáticamente por "categoria".
DOCUMENTOS = [
    {
        "titulo": "Resolución Directiva N°6 - PAC 2025",
        "archivo": "568-B_Res_Directiva6_2025_PAC.pdf",
        "categoria": "Directivas y Resoluciones",
        "descripcion": "Normativa oficial para la ejecución del Plan Anual de Compras 2025.",
        "icono": "📄"
    },
    # --- Ejemplos de relleno para demostrar la funcionalidad (Puedes borrarlos) ---
    {
        "titulo": "Ley 19.886 - Ley de Compras Públicas",
        "archivo": "Ley_19886_Referencia.pdf",
        "categoria": "Marco Legal",
        "descripcion": "Ley de Bases sobre Contratos Administrativos de Suministro.",
        "icono": "⚖️"
    },
    {
        "titulo": "Reglamento de la Ley de Compras",
        "archivo": "Reglamento_Compras.pdf",
        "categoria": "Marco Legal",
        "descripcion": "Decreto 250 que aprueba el reglamento de la ley 19.886.",
        "icono": "⚖️"
    },
    {
        "titulo": "Manual de Procedimientos Abastecimiento 2025",
        "archivo": "Manual-de-Procedimientos-2025.pdf",
        "categoria": "Manuales y Guías",
        "descripcion": "Manual de Procedimientos Abastecimiento 2025.",
        "icono": "📘"
    }
]

# Estilos CSS para diseño minimalista y limpio
st.markdown("""
    <style>
    .stTextInput > div > div > input {
        background-color: #f0f2f6;
        border-radius: 20px;
        padding-left: 15px;
    }
    .category-header {
        font-size: 18px;
        font-weight: 600;
        color: #138AEC;
        margin-top: 20px;
        margin-bottom: 10px;
        border-bottom: 1px solid #ddd;
        padding-bottom: 5px;
    }
    .doc-row {
        padding: 10px 0;
        border-bottom: 1px solid #f0f0f0;
    }
    </style>
""", unsafe_allow_html=True)

# =============================================================================
# HEADER Y BUSCADOR
# =============================================================================
col_header, col_search = st.columns([2, 1])

with col_header:
    st.markdown("### 📂 Repositorio de Documentos")
    st.markdown("Acceso centralizado a la normativa vigente y manuales.")

with col_search:
    st.write("") # Espaciador vertical
    busqueda = st.text_input("🔍 Buscar documento...", placeholder="Escribe nombre o categoría").lower()

# =============================================================================
# LÓGICA DE FILTRADO
# =============================================================================
docs_filtrados = []
for doc in DOCUMENTOS:
    contenido_busqueda = (doc["titulo"] + doc["categoria"] + doc["descripcion"]).lower()
    if busqueda in contenido_busqueda:
        docs_filtrados.append(doc)

# Agrupar por categorías
categorias_encontradas = sorted(list(set(d["categoria"] for d in docs_filtrados)))

# =============================================================================
# RENDERIZADO (Lista Indentada)
# =============================================================================
st.markdown("---")

if not docs_filtrados:
    st.info("No se encontraron documentos que coincidan con tu búsqueda.")
else:
    for categoria in categorias_encontradas:
        # 1. Cabecera de Categoría
        st.markdown(f"<div class='category-header'>{categoria}</div>", unsafe_allow_html=True)
        
        # Filtrar docs de esta categoría específica
        docs_en_cat = [d for d in docs_filtrados if d["categoria"] == categoria]
        
        for doc in docs_en_cat:
            # 2. Fila del Documento (Indentación visual usando columnas)
            # Columna 1: Espacio vacío (indentación)
            # Columna 2: Icono
            # Columna 3: Título y descripción
            # Columna 4: Botón descarga
            col_spacer, col_icon, col_text, col_btn = st.columns([0.2, 0.3, 4, 1])
            
            with col_icon:
                st.write(f"### {doc['icono']}")
            
            with col_text:
                st.markdown(f"**{doc['titulo']}**")
                st.caption(doc['descripcion'])
            
            with col_btn:
                ruta_completa = os.path.join(BASE_DOC_PATH, doc["archivo"])
                st.write("") # Alineación vertical
                
                if os.path.exists(ruta_completa):
                    with open(ruta_completa, "rb") as f:
                        st.download_button(
                            label="⬇️ Descargar",
                            data=f,
                            file_name=doc["archivo"],
                            mime="application/pdf",
                            key=f"btn_{doc['archivo']}",
                            use_container_width=True
                        )
                else:
                    st.warning("No disponible")
            
            st.markdown("<div class='doc-row'></div>", unsafe_allow_html=True)

# =============================================================================
# FOOTER
# =============================================================================
st.write("")
st.caption("Nota: Los documentos marcados como 'No disponible' no se encuentran cargados en el servidor.")

# =============================================================================
# FOOTER / NOTAS
# =============================================================================
with st.expander("ℹ️ Ayuda sobre los documentos"):
    st.markdown("""
    * **Directivas:** Instrucciones internas de cumplimiento obligatorio para los departamentos.
    * **Legislación:** Marco legal nacional (Ley de Compras, Reglamento).
    * **Manuales:** Guías de uso de plataformas y procedimientos.
    
    Si necesita agregar un documento a este repositorio, contacte al administrador del sistema.
    """)