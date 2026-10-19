"""Punto de entrada de la app: define la navegación entre las cinco páginas."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

DIR = Path(__file__).resolve().parent
if str(DIR) not in sys.path:
    sys.path.insert(0, str(DIR))

from comun import api_en_linea, url_api  # noqa: E402

st.set_page_config(
    page_title="Taxis NYC · decisiones con datos",
    page_icon="🚕",
    layout="wide",
)

paginas = [
    st.Page("paginas/pronostico.py", title="Pronóstico", icon=":material/query_stats:", default=True),
    st.Page("paginas/zonas.py", title="Tipos de zona", icon=":material/scatter_plot:"),
    st.Page("paginas/decision.py", title="Cuántos taxis enviar", icon=":material/local_taxi:"),
    st.Page("paginas/ficha.py", title="Ficha del modelo", icon=":material/description:"),
    st.Page("paginas/monitoreo.py", title="Monitoreo", icon=":material/monitoring:"),
]

with st.sidebar:
    st.markdown("### 🚕 Taxis amarillos de Nueva York")
    st.caption("Pronóstico horario por zona · enero de 2024")
    if api_en_linea():
        st.badge("API en línea", icon=":material/check_circle:", color="green")
    else:
        st.badge("API sin respuesta", icon=":material/error:", color="red")
    st.caption(f"Servicio: `{url_api()}`")
    st.divider()
    st.caption(
        "Datos: NYC TLC · *Yellow Taxi Trip Data*, enero de 2024. "
        "Pronóstico con XGBoost de cuantiles, entrenado hasta el 24 de enero."
    )

navegacion = st.navigation(paginas)
navegacion.run()
