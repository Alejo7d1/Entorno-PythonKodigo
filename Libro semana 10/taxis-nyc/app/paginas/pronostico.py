"""Página 1 · Pronóstico horario con banda de incertidumbre."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from comun import (
    ErrorAPI,
    api_info,
    api_pronostico,
    columnas_horas,
    etiqueta_fecha_larga,
    mostrar_error_api,
    publicar_parametros,
    selector_fecha,
    selector_zona,
    sincronizar_estado,
)

AZUL = "#1F4E79"
GRIS = "#8A8F98"


@st.dialog("Cómo leer este gráfico")
def ayuda_pronostico() -> None:
    st.markdown(
        """
**La línea azul** es la mediana: el valor que tiene la mitad de probabilidad de quedar por
debajo y la mitad por encima. Es el pronóstico central.

**La banda azul clara** va del cuantil 10 % al 90 %: en 8 de cada 10 casos, los viajes reales
deberían caer dentro. Si la banda es ancha, el día es difícil de prever y conviene decidir con
más margen.

**Los puntos negros** son los viajes reales. Solo existen del 25 al 31 de enero; el 1 de febrero
es «mañana» y todavía no ocurrió.

**La línea gris punteada** es la regla simple: lo que pasó la misma hora de la semana anterior.
Sirve de comparación honesta.
        """
    )
    st.caption("El modelo no dice «pasarán exactamente X viajes»: dice un rango con probabilidad.")


st.title("¿Cuántos viajes habrá mañana?")
st.caption(
    "Elija una zona y un día. El pronóstico viene de la API; la app nunca carga el modelo."
)

try:
    info = api_info()
except ErrorAPI as error:
    mostrar_error_api(error)
    st.stop()

sincronizar_estado(info)

columna_zona, columna_boton = st.columns([3, 1])
with columna_zona:
    zona = selector_zona(info)
with columna_boton:
    st.write("")
    st.write("")
    if st.button("¿Cómo se lee esto?", icon=":material/help:", width="stretch"):
        ayuda_pronostico()

fecha = selector_fecha(info)
publicar_parametros()

with st.status("Consultando el pronóstico en la API...", expanded=True) as estado:
    try:
        datos = api_pronostico(zona, fecha)
        estado.update(label="Pronóstico recibido", state="complete", expanded=False)
    except ErrorAPI as error:
        estado.update(label="La API no respondió", state="error", expanded=False)
        mostrar_error_api(error)
        st.stop()

datos_horas = columnas_horas(datos)
p10, p50, p90 = datos_horas["p10"], datos_horas["p50"], datos_horas["p90"]
real, semana = datos_horas["real"], datos_horas["hace_una_semana"]
nombre_zona = datos["zona"]["nombre"]

st.subheader(f"{nombre_zona} · {etiqueta_fecha_larga(fecha)}")

total_p50 = float(np.sum(p50))
total_semana = float(np.nansum(semana))
hay_reales = not datos["sin_datos_reales"]
total_real = float(np.nansum(real)) if hay_reales else None

tres = st.columns(3)
tres[0].metric(
    "Viajes previstos (mediana)",
    f"{total_p50:,.0f}",
    delta=None if not total_semana else f"{(total_p50 / total_semana - 1):+.1%} vs. hace una semana",
    delta_color="off",
    border=True,
    chart_data=p50,
    chart_type="area",
    help="Suma de la mediana de las 24 horas del día.",
)
tres[1].metric(
    "Rango esperado (p10–p90)",
    f"{np.sum(p10):,.0f} – {np.sum(p90):,.0f}",
    border=True,
    chart_data=p90,
    chart_type="line",
    help="Si el modelo está bien calibrado, 8 de cada 10 días reales caen dentro de este rango.",
)
if hay_reales:
    tres[2].metric(
        "Viajes reales del día",
        f"{total_real:,.0f}",
        delta=None if not total_p50 else f"{(total_real / total_p50 - 1):+.1%} vs. mediana",
        delta_color="off",
        border=True,
        chart_data=real,
        chart_type="line",
    )
else:
    tres[2].metric(
        "Viajes reales",
        "Sin datos",
        delta="El 1 de febrero todavía no ocurrió",
        delta_color="off",
        border=True,
        help="La app lo dice en lugar de mostrar un hueco o un error.",
    )

horas = datos_horas["hora"]
figura = go.Figure()
figura.add_trace(
    go.Scatter(x=horas, y=p90, line=dict(width=0), hoverinfo="skip", showlegend=False)
)
figura.add_trace(
    go.Scatter(
        x=horas,
        y=p10,
        line=dict(width=0),
        fill="tonexty",
        fillcolor="rgba(31, 78, 121, 0.22)",
        name="Banda p10–p90",
        hovertemplate="%{y:.0f} viajes<extra>p10</extra>",
    )
)
figura.add_trace(
    go.Scatter(
        x=horas, y=p50, name="Mediana (p50)", line=dict(color=AZUL, width=3),
        hovertemplate="%{y:.0f} viajes<extra>p50</extra>",
    )
)
figura.add_trace(
    go.Scatter(
        x=horas, y=semana, name="Hace una semana", line=dict(color=GRIS, width=2, dash="dash"),
        hovertemplate="%{y:.0f} viajes<extra>hace una semana</extra>",
    )
)
if hay_reales:
    figura.add_trace(
        go.Scatter(
            x=horas, y=real, name="Viajes reales", mode="markers",
            marker=dict(color="#111111", size=8),
            hovertemplate="%{y:.0f} viajes<extra>real</extra>",
        )
    )
figura.update_layout(
    height=420,
    margin=dict(l=10, r=10, t=10, b=10),
    xaxis=dict(title="Hora del día", dtick=2, range=[-0.5, 23.5]),
    yaxis=dict(title="Viajes por hora", rangemode="tozero"),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    hovermode="x unified",
)
st.plotly_chart(figura, width="stretch")

if hay_reales:
    hora_punta = int(np.argmax(p50))
    st.markdown(
        f"**Punto clave:** la mayor demanda se espera a las **{hora_punta}:00**, con unos "
        f"**{p50[hora_punta]:,.0f}** viajes previstos (entre {p10[hora_punta]:,.0f} y "
        f"{p90[hora_punta]:,.0f}). En la misma hora de la semana anterior hubo "
        f"**{semana[hora_punta]:,.0f}**."
    )
else:
    st.info(
        "**El 1 de febrero es «mañana»:** no existen viajes reales todavía, así que el gráfico "
        "muestra solo el pronóstico y la comparación con hace una semana. Cuando lleguen los datos "
        "reales, se podrán superponer para revisar el acierto.",
        icon=":material/event_upcoming:",
    )

tabla = pd.DataFrame(
    {
        "Hora": [f"{h:02d}:00" for h in horas],
        "Real": real,
        "Hace una semana": semana,
        "p10": p10,
        "p50": p50,
        "p90": p90,
    }
)
st.dataframe(
    tabla,
    hide_index=True,
    width="stretch",
    height=330,
    column_config={
        "Hora": st.column_config.TextColumn("Hora", width="small"),
        "Real": st.column_config.NumberColumn("Real", format="%.0f", help="Null si el día no tiene datos."),
        "Hace una semana": st.column_config.NumberColumn("Hace 1 sem.", format="%.0f"),
        "p50": st.column_config.ProgressColumn(
            "p50 (mediana)", format="%.0f", min_value=0, max_value=float(max(p90)) or 1
        ),
        "p10": st.column_config.NumberColumn("p10", format="%.0f"),
        "p90": st.column_config.NumberColumn("p90", format="%.0f"),
    },
)
