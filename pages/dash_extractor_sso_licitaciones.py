import contextlib
import io
from datetime import date
import pandas as pd
import plotly.express as px
import streamlit as st
from style.ui import cargar_css

# Importamos la versión optimizada V3 creada anteriormente
import api.LI_SSO_PorDiaPeriodo_v3 as sso

st.set_page_config(page_title="Extractor SSO (Licitaciones)", layout="wide")
cargar_css()

@st.cache_data(ttl=60, show_spinner=False)
def _listar_archivos_diario():
    # Ajustado al patrón de nombres de Licitaciones
    res = sorted([p.name for p in sso.CARPETA_DIARIO.glob("LICITACION_*_RESUMEN.csv")])
    det = sorted([p.name for p in sso.CARPETA_DIARIO.glob("LICITACION_*_DETALLES.csv")])
    return res, det


@st.cache_data(ttl=60, show_spinner=False)
def _listar_maestros():
    ruta_res = sso.CARPETA_MAESTROS / "Maestro_Resumen.csv"
    ruta_det = sso.CARPETA_MAESTROS / "Maestro_Detalle.csv"
    return ruta_res.exists(), ruta_det.exists(), ruta_res, ruta_det


@st.cache_data(ttl=600, show_spinner=False)
def _cargar_maestro_resumen():
    ruta = sso.CARPETA_MAESTROS / "Maestro_Resumen.csv"
    if not ruta.exists():
        return pd.DataFrame()
    return pd.read_csv(ruta, sep=";", encoding="utf-8-sig", dtype=str)


@st.cache_data(ttl=600, show_spinner=False)
def _cargar_maestro_detalles():
    ruta = sso.CARPETA_MAESTROS / "Maestro_Detalle.csv"
    if not ruta.exists():
        return pd.DataFrame()
    return pd.read_csv(ruta, sep=";", encoding="utf-8-sig", dtype=str)


def _run_with_captured_logs(fn, *args, **kwargs):
    buf = io.StringIO()
    ok = False
    err = None
    with contextlib.redirect_stdout(buf):
        try:
            result = fn(*args, **kwargs)
            ok = True
            return ok, result, buf.getvalue(), err
        except Exception as e:
            err = e
            return ok, None, buf.getvalue(), err


def _init_progress_state() -> None:
    if "progress_day" not in st.session_state:
        st.session_state["progress_day"] = None
    if "progress_codigo" not in st.session_state:
        st.session_state["progress_codigo"] = None
    if "progress_done" not in st.session_state:
        st.session_state["progress_done"] = 0
    if "progress_total" not in st.session_state:
        st.session_state["progress_total"] = 0


_init_progress_state()


st.markdown(
    """
    <div style="padding: 1.2rem 1.5rem; margin-bottom: 1.5rem; background: linear-gradient(90deg, #138AEC, #3E9FEF); color: white; border-radius: 14px; box-shadow: 0 4px 10px rgba(0,0,0,0.15);">
        <div style="font-size: 28px; font-weight: 800;">🏛️ Extractor SSO - Licitaciones</div>
        <div style="font-size: 15px; opacity: 0.9; margin-top: 4px;">Descarga diaria / por rango, unificación a maestros, validación y exportación</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("## 🧭 Panel de Control")

ctl_left, ctl_mid, ctl_right = st.columns([1.2, 1.0, 1.0])

with ctl_left:
    with st.expander("⚙️ Parámetros", expanded=True):
        codigo_organismo = st.text_input("Código Organismo", value=sso.CODIGO_ORGANISMO)
        ticket = st.text_input("Ticket API", value=sso.TICKET, type="password")

with ctl_mid:
    with st.expander("🔁 Rendimiento", expanded=True):
        max_workers = st.number_input(
            "Workers (detalle)",
            min_value=1,
            max_value=20,
            value=int(sso.MAX_WORKERS_DETALLE),
            help="Número de hilos simultáneos para descargar detalles de licitaciones."
        )
        espera_det = st.number_input(
            "Espera entre detalles (s)",
            min_value=0.0,
            max_value=2.0,
            value=float(sso.ESPERA_ENTRE_DETALLES),
            step=0.01,
            help="Tiempo de espera entre peticiones para evitar bloqueo de API."
        )

with ctl_right:
    with st.expander("📅 Período y Acción", expanded=True):
        hoy = date.today()
        rango = st.date_input("Rango", value=(hoy, hoy))
        modo_actualizar = st.checkbox("Forzar actualización (re-descargar)", value=False)

        accion = st.radio(
            "Acción",
            options=["Descargar rango", "Unificar maestros", "Refresh maestros"],
            index=0,
        )

        ejecutar = st.button("▶ Ejecutar", type="primary", use_container_width=True)


st.markdown("---")

colA, colB = st.columns([2, 1])

with colA:
    st.markdown("## 🚀 Ejecución")

    progress_box = st.container()
    with progress_box:
        p_col1, p_col2 = st.columns([2, 1])
        progreso_txt = p_col1.empty()
        li_txt = p_col1.empty()
        barra = p_col2.progress(0)

    if ejecutar:
        if not (isinstance(rango, (list, tuple)) and len(rango) == 2 and rango[0] and rango[1]):
            st.error("Selecciona un rango válido (inicio y fin).")
        else:
            f_ini, f_fin = rango
            if f_ini > f_fin:
                st.error("La fecha de inicio no puede ser mayor que la fecha de fin.")
            else:
                with st.spinner("Ejecutando..."):
                    if accion == "Descargar rango":
                        ok_all = True
                        logs_total = ""
                        cur = f_ini

                        st.session_state["progress_day"] = None
                        st.session_state["progress_codigo"] = None
                        st.session_state["progress_done"] = 0
                        st.session_state["progress_total"] = 0

                        def _cb_progress(codigo: str, done: int, total: int) -> None:
                            st.session_state["progress_day"] = cur
                            st.session_state["progress_codigo"] = codigo
                            st.session_state["progress_done"] = done
                            st.session_state["progress_total"] = total

                            progreso_txt.markdown(
                                f"**Día:** `{cur}`\n\n**Progreso:** `{done}/{total}`"
                            )
                            li_txt.markdown(f"**Licitación actual:** `{codigo}`")
                            pct = int(done / total * 100) if total else 0
                            barra.progress(pct)

                        while cur <= f_fin:
                            progreso_txt.markdown(f"**Día:** `{cur}`")
                            li_txt.markdown("**Licitación actual:** iniciando...")
                            barra.progress(0)

                            ok, result, logs, err = _run_with_captured_logs(
                                sso.procesar_dia,
                                cur,
                                modo_actualizar=modo_actualizar,
                                codigo_organismo=codigo_organismo,
                                ticket=ticket,
                                max_workers_detalle=int(max_workers),
                                espera_entre_detalles=float(espera_det),
                                progress_callback=_cb_progress,
                            )
                            logs_total += logs
                            if err:
                                ok_all = False
                                logs_total += f"\n❌ Error en {cur}: {err}\n"
                            cur = cur + pd.Timedelta(days=1)

                        st.session_state["last_logs"] = logs_total
                        progreso_txt.markdown("**Estado:** finalizado")
                        barra.progress(100)
                        if ok_all:
                            st.success("Descarga completada.")
                        else:
                            st.warning("Descarga completada con advertencias/errores. Revisa logs.")

                    elif accion == "Unificar maestros":
                        ok, result, logs, err = _run_with_captured_logs(sso.unificar_base_datos)
                        st.session_state["last_logs"] = logs
                        if err:
                            st.error(f"Error: {err}")
                        else:
                            st.success("Maestros generados/actualizados.")

                    elif accion == "Refresh maestros":
                        st.session_state["progress_day"] = None
                        st.session_state["progress_codigo"] = None
                        st.session_state["progress_done"] = 0
                        st.session_state["progress_total"] = 0

                        def _cb_refresh(dia, codigo: str, done: int, total: int) -> None:
                            st.session_state["progress_day"] = dia
                            st.session_state["progress_codigo"] = codigo
                            st.session_state["progress_done"] = done
                            st.session_state["progress_total"] = total

                            progreso_txt.markdown(
                                f"**Día:** `{dia}`\n\n**Progreso:** `{done}/{total}`"
                            )
                            li_txt.markdown(f"**Licitación actual:** `{codigo}`")
                            pct = int(done / total * 100) if total else 0
                            barra.progress(pct)

                        # Importante: Pasar f_ini y f_fin correctamente tipados (aunque date_input devuelve date, sso v3 lo maneja)
                        ok, result, logs, err = _run_with_captured_logs(
                            sso.refresh_base_datos,
                            f_ini,
                            f_fin,
                            codigo_organismo=codigo_organismo,
                            ticket=ticket,
                            max_workers_detalle=int(max_workers),
                            espera_entre_detalles=float(espera_det),
                            progress_callback=_cb_refresh,
                        )
                        st.session_state["last_logs"] = logs
                        if err:
                            st.error(f"Error: {err}")
                        else:
                            st.success("Refresh completado (Descarga + Unificación).")

                _listar_archivos_diario.clear()
                _listar_maestros.clear()
                _cargar_maestro_resumen.clear()
                _cargar_maestro_detalles.clear()

with colB:
    st.markdown("## ✅ Validación")
    res_files, det_files = _listar_archivos_diario()
    has_m_res, has_m_det, ruta_m_res, ruta_m_det = _listar_maestros()

    st.write(f"DIARIO resumen: {len(res_files)}")
    st.write(f"DIARIO detalles: {len(det_files)}")
    st.write(f"Maestro Resumen existe: {has_m_res}")
    st.write(f"Maestro Detalles existe: {has_m_det}")


st.markdown("---")

tab_logs, tab_resultados = st.tabs(["📄 Logs", "📦 Resultados"])

with tab_logs:
    logs = st.session_state.get("last_logs", "")
    st.text_area("Salida", value=logs, height=360)

with tab_resultados:
    df_res = _cargar_maestro_resumen()
    df_det = _cargar_maestro_detalles()

    st.write(f"Registros resumen: {len(df_res):,}")
    st.write(f"Registros detalle: {len(df_det):,}")

    if not df_res.empty and "FechaCreacion" in df_res.columns:
        df_res_vis = df_res.copy()
        df_res_vis["FechaCreacion"] = pd.to_datetime(df_res_vis["FechaCreacion"], errors="coerce", dayfirst=True)
        df_res_vis = df_res_vis.dropna(subset=["FechaCreacion"])

        if not df_res_vis.empty:
            df_res_vis["Mes"] = df_res_vis["FechaCreacion"].dt.to_period("M").dt.to_timestamp()
            
            # Gráfico de barras por Mes
            serie = df_res_vis.groupby("Mes").size().reset_index(name="Cantidad")
            fig = px.bar(serie, x="Mes", y="Cantidad", title="Licitaciones por mes")
            st.plotly_chart(fig, use_container_width=True)
            
            # Gráfico de Estado
            if "Estado" in df_res_vis.columns:
                 fig_estado = px.pie(df_res_vis, names='Estado', title='Distribución por Estado', hole=0.4)
                 st.plotly_chart(fig_estado, use_container_width=True)

    # Tabla y descargas
    if not df_res.empty:
        st.dataframe(df_res.head(200), use_container_width=True, hide_index=True)

        csv_bytes = df_res.to_csv(sep=";", index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(
            "⬇️ Descargar Maestro Resumen (CSV)",
            data=csv_bytes,
            file_name="Maestro_Licitaciones_Resumen.csv",
            mime="text/csv",
        )

    if not df_det.empty:
        csv_bytes = df_det.to_csv(sep=";", index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(
            "⬇️ Descargar Maestro Detalles (CSV)",
            data=csv_bytes,
            file_name="Maestro_Licitaciones_Detalles.csv",
            mime="text/csv",
        )
