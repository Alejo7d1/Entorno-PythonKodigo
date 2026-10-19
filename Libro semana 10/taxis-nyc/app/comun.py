"""Utilidades compartidas por las páginas de la app de taxis."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

DIR = Path(__file__).resolve().parent
DIR_DATOS = DIR / "data"

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
MESES_LARGOS = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]

TIEMPO_MAXIMO = 90  # segundos: en Render el plan gratuito tarda ~1 minuto en despertar

COLORES_GRUPO = {
    "Aeropuertos y viajes largos": "#2E86AB",
    "Zonas de oficinas y tarde": "#F18F01",
    "Zonas nocturnas": "#8E44AD",
    "Zonas de barrio con poca demanda": "#6C757D",
    "Zonas madrugadoras": "#2CA02C",
    "Zonas muy transitadas": "#D62728",
    "Zonas de ocio de fin de semana": "#E377C2",
}
INSIGNIAS_GRUPO = {
    "Aeropuertos y viajes largos": "blue",
    "Zonas de oficinas y tarde": "orange",
    "Zonas nocturnas": "violet",
    "Zonas de barrio con poca demanda": "gray",
    "Zonas madrugadoras": "green",
    "Zonas muy transitadas": "red",
    "Zonas de ocio de fin de semana": "pink",
}
PALETA_EXTRA = ["#17BECF", "#BCBD22", "#7F7F7F", "#E45756", "#72B7B2", "#B279A2"]


class ErrorAPI(Exception):
    """Problema al pedir datos a la API (sin conexión, tiempo agotado o error de datos)."""


def url_api() -> str:
    """Dirección de la API: primero Secrets, luego variable de entorno, luego localhost."""
    try:
        valor = st.secrets.get("API_URL")
    except Exception:  # no hay secrets.toml
        valor = None
    return str(valor or os.getenv("API_URL") or "http://localhost:8000").rstrip("/")


def _llamar(ruta: str, **parametros) -> dict:
    try:
        respuesta = requests.get(f"{url_api()}{ruta}", params=parametros, timeout=TIEMPO_MAXIMO)
    except requests.Timeout as error:
        raise ErrorAPI(
            "La API tardó más de 90 segundos en responder. "
            "En el plan gratuito de Render, la API se duerme tras 15 minutos sin uso."
        ) from error
    except requests.RequestException as error:
        raise ErrorAPI(f"No se pudo conectar con la API en {url_api()}.") from error

    if respuesta.status_code == 404:
        try:
            detalle = respuesta.json().get("detail", "No hay datos para esa consulta.")
        except ValueError:
            detalle = "No hay datos para esa consulta."
        raise ErrorAPI(detalle)
    if respuesta.status_code != 200:
        raise ErrorAPI(f"La API respondió con un error {respuesta.status_code}.")
    return respuesta.json()


@st.cache_data(ttl=3600, show_spinner=False)
def api_info() -> dict:
    """Zonas, fechas y cuantiles. Se guarda una hora en caché."""
    return _llamar("/info")


@st.cache_data(ttl=3600, show_spinner=False)
def api_pronostico(zona_id: int, fecha: str) -> dict:
    """Pronóstico de 24 horas. Se guarda una hora para no repetir la llamada en cada clic."""
    return _llamar("/pronostico", zona_id=zona_id, fecha=fecha)


@st.cache_data(ttl=60, show_spinner=False)
def api_en_linea() -> bool:
    """Comprobación rápida del estado de la API (timeout corto)."""
    try:
        return requests.get(f"{url_api()}/", timeout=6).status_code == 200
    except requests.RequestException:
        return False


def mostrar_error_api(error: ErrorAPI) -> None:
    """Mensaje entendible cuando la API no responde (nunca un error de Python)."""
    api_en_linea.clear()
    st.error("No pudimos obtener los datos de la API.", icon=":material/cloud_off:")
    st.markdown(f"**Detalle técnico:** {error}")
    st.info(
        "**Qué puede hacer**\n\n"
        "1. Abrir el enlace de la API en otra pestaña y esperar hasta un minuto: "
        "el plan gratuito de Render la duerme a los 15 minutos sin uso.\n"
        "2. Pulsar **Reintentar**.\n"
        f"3. Revisar que la dirección configurada sea correcta: `{url_api()}`."
    )
    if st.button("Reintentar", icon=":material/refresh:"):
        st.cache_data.clear()
        st.rerun()


@st.cache_data(show_spinner=False)
def cargar_zonas() -> pd.DataFrame:
    zonas = pd.read_csv(DIR_DATOS / "zonas_segmentadas.csv")
    zonas["perfil"] = zonas["perfil_horario"].apply(json.loads)
    return zonas


@st.cache_data(show_spinner=False)
def cargar_metricas() -> dict:
    return json.loads((DIR_DATOS / "metricas.json").read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def cargar_monitoreo() -> tuple[pd.DataFrame, pd.DataFrame]:
    diario = pd.read_csv(DIR_DATOS / "monitoreo.csv", parse_dates=["fecha"])
    por_zona = pd.read_csv(DIR_DATOS / "monitoreo_zonas.csv", parse_dates=["fecha"])
    return diario, por_zona


def color_grupo(nombre: str) -> str:
    if nombre in COLORES_GRUPO:
        return COLORES_GRUPO[nombre]
    return PALETA_EXTRA[hash(nombre) % len(PALETA_EXTRA)]


def insignia_grupo(nombre: str) -> None:
    st.badge(nombre, color=INSIGNIAS_GRUPO.get(nombre, "green"))


def etiqueta_fecha(iso: str) -> str:
    fecha = pd.Timestamp(iso)
    return f"{DIAS[fecha.dayofweek]} {fecha.day} {MESES[fecha.month - 1]}"


def etiqueta_fecha_larga(iso: str) -> str:
    fecha = pd.Timestamp(iso)
    return f"{DIAS[fecha.dayofweek]} {fecha.day} de {MESES_LARGOS[fecha.month - 1]} de {fecha.year}"


def sincronizar_estado(info: dict) -> None:
    """Recupera zona y fecha desde el link (query params) o pone valores por defecto."""
    ids = [zona["id"] for zona in info["zonas"]]
    if st.session_state.get("zona_id") not in ids:
        try:
            link = int(st.query_params.get("zona", ""))
        except (TypeError, ValueError):
            link = None
        st.session_state["zona_id"] = link if link in ids else (161 if 161 in ids else ids[0])

    fechas = info["fechas"]
    if st.session_state.get("fecha") not in fechas:
        link = st.query_params.get("fecha")
        st.session_state["fecha"] = link if link in fechas else fechas[0]


def publicar_parametros(incluir_fecha: bool = True) -> None:
    """Deja la zona (y la fecha) en el link para poder compartirlo."""
    st.query_params["zona"] = str(st.session_state.get("zona_id"))
    if incluir_fecha:
        st.query_params["fecha"] = str(st.session_state.get("fecha"))


def selector_zona(info: dict, etiqueta: str = "Zona de origen") -> int:
    zonas = info["zonas"]
    ids = [zona["id"] for zona in zonas]
    nombre = {zona["id"]: zona["nombre"] for zona in zonas}
    distrito = {zona["id"]: zona["distrito"] for zona in zonas}
    return st.selectbox(
        etiqueta,
        ids,
        format_func=lambda z: f"{nombre[z]} · {distrito[z]}",
        key="zona_id",
        help="Solo aparecen las zonas con 3,000 viajes o más en enero de 2024.",
    )


def selector_fecha(info: dict, etiqueta: str = "Fecha") -> str:
    fechas = info["fechas"]
    return (
        st.segmented_control(
            etiqueta,
            fechas,
            format_func=etiqueta_fecha,
            key="fecha",
            required=True,
            help="Del 25 al 31 de enero hay viajes reales. El 1 de febrero es «mañana»: todavía no existen.",
        )
        or fechas[0]
    )


def columnas_horas(datos: dict) -> dict:
    """Convierte la respuesta de la API en listas ordenadas por hora."""
    horas = datos["horas"]
    return {
        "hora": [h["hora"] for h in horas],
        "p10": [h["cuantiles"]["p10"] for h in horas],
        "p50": [h["cuantiles"]["p50"] for h in horas],
        "p90": [h["cuantiles"]["p90"] for h in horas],
        "real": [h["real"] for h in horas],
        "hace_una_semana": [h["hace_una_semana"] for h in horas],
    }
