"""Página 3 · Decisión: cuántos taxis enviar según lo que cuesta equivocarse."""

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
NARANJA = "#D9822B"
GRIS = "#8A8F98"


def costo_horario(enviados: np.ndarray, real: np.ndarray, costo_ocioso: float, costo_perdido: float) -> np.ndarray:
    """Problema del vendedor de periódicos: pasarse cuesta distinto que quedarse corto."""
    return np.maximum(enviados - real, 0) * costo_ocioso + np.maximum(real - enviados, 0) * costo_perdido


def niveles_cuantiles(datos: dict) -> np.ndarray:
    nombres = list(datos["horas"][0]["cuantiles"].keys())
    return np.array([int(nombre[1:]) / 100 for nombre in nombres])


def matriz_cuantiles(datos: dict) -> np.ndarray:
    nombres = list(datos["horas"][0]["cuantiles"].keys())
    return np.array([[hora["cuantiles"][nombre] for nombre in nombres] for hora in datos["horas"]])


@st.fragment
def panel_decision(datos: dict, fecha: str) -> None:
    """Controles y resultados en un fragmento: mover un control no recarga toda la página."""
    st.subheader("1 · ¿Cuánto cuesta equivocarse?")
    controles = st.columns(2)
    costo_ocioso = controles[0].slider(
        "Un taxi una hora sin pasajero (USD)", min_value=1, max_value=60, value=10, step=1,
        help="Combustible, salario del conductor y desgaste de una hora sin viaje.",
    )
    costo_perdido = controles[1].slider(
        "Un pasajero que no encuentra taxi (USD)", min_value=5, max_value=150, value=40, step=5,
        help="Viaje perdido, cliente que se va a la competencia y mala reputación.",
    )

    cuantil = costo_perdido / (costo_perdido + costo_ocioso)
    nombres = list(datos["horas"][0]["cuantiles"].keys())
    niveles = niveles_cuantiles(datos)
    matriz = matriz_cuantiles(datos)

    # Cuantil exacto interpolando entre los cuantiles que entrega la API.
    recomendado = np.array([np.interp(cuantil, niveles, fila) for fila in matriz])

    columnas = columnas_horas(datos)
    horas = columnas["hora"]
    p50 = np.array(columnas["p50"])
    semana = np.array([0.0 if v is None else float(v) for v in columnas["hace_una_semana"]])
    reales = np.array([np.nan if v is None else float(v) for v in columnas["real"]])
    hay_reales = not datos["sin_datos_reales"]

    st.subheader("2 · El cuantil que le corresponde")
    izquierda, derecha = st.columns([1, 2])
    with izquierda:
        st.latex(r"\text{cuantil}^* = \frac{C_{\text{pasajero perdido}}}{C_{\text{pasajero perdido}} + C_{\text{taxi ocioso}}}")
        st.metric("Cuantil óptimo", f"{cuantil:.2f}", border=True)
        st.caption(f"Cuantil usado del pronóstico: **{nombres[int(np.argmin(np.abs(niveles - cuantil)))]}**")
    with derecha:
        st.markdown(
            f"""
Con sus costos, **quedarse corto cuesta {costo_perdido / costo_ocioso:.1f} veces más** que pasarse.
Por eso conviene enviar **más** taxis que el pronóstico central: la cantidad del
**cuantil {cuantil:.0%}** del pronóstico.

Dicho en simple: si envía esa cantidad, **en {cuantil:.0%} de las horas habrá suficientes taxis**
y solo se quedará corto en el {1 - cuantil:.0%} restante, que es justo lo que sus costos toleran.
"""
        )

    st.subheader("3 · Plan de taxis por hora")
    enviados = np.round(recomendado).astype(int)
    total_enviados = int(enviados.sum())
    total_p50 = int(np.round(p50).sum())
    st.markdown(
        f"Para **{etiqueta_fecha_larga(fecha)}** recomendamos **{total_enviados:,} taxis-hora** en esta zona "
        f"({total_enviados / 24:.0f} por hora en promedio), frente a **{total_p50:,}** que saldrían de "
        f"enviar el pronóstico central."
    )

    figura = go.Figure()
    figura.add_bar(x=horas, y=enviados, name="Taxis recomendados", marker_color=AZUL)
    figura.add_trace(
        go.Scatter(
            x=horas, y=p50, name="Pronóstico central (p50)", mode="lines",
            line=dict(color=NARANJA, width=2.5),
        )
    )
    if hay_reales:
        figura.add_trace(
            go.Scatter(
                x=horas, y=reales, name="Viajes reales", mode="markers",
                marker=dict(color="#111111", size=8),
            )
        )
    figura.update_layout(
        height=380, margin=dict(l=10, r=10, t=10, b=10), bargap=0.25,
        xaxis=dict(title="Hora del día", dtick=2), yaxis=dict(title="Taxis / viajes por hora", rangemode="tozero"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0), hovermode="x unified",
    )
    st.plotly_chart(figura, width="stretch")

    plan = pd.DataFrame(
        {
            "hora": [f"{h:02d}:00" for h in horas],
            "p10": columnas["p10"],
            "p50": columnas["p50"],
            "p90": columnas["p90"],
            "taxis_recomendados": enviados,
            "real": columnas["real"],
            "hace_una_semana": columnas["hace_una_semana"],
        }
    )

    izquierda, derecha = st.columns([2, 1])
    with izquierda:
        st.dataframe(
            plan,
            hide_index=True,
            width="stretch",
            height=320,
            column_config={
                "hora": st.column_config.TextColumn("Hora", width="small"),
                "p10": st.column_config.NumberColumn("p10", format="%.0f"),
                "p50": st.column_config.NumberColumn("p50", format="%.0f"),
                "p90": st.column_config.NumberColumn("p90", format="%.0f"),
                "taxis_recomendados": st.column_config.ProgressColumn(
                    "Taxis a enviar", format="%d", min_value=0, max_value=int(max(enviados)) or 1
                ),
                "real": st.column_config.NumberColumn("Real", format="%.0f"),
                "hace_una_semana": st.column_config.NumberColumn("Hace 1 sem.", format="%.0f"),
            },
        )
    with derecha:
        st.download_button(
            "Descargar plan (CSV)",
            data=plan.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"plan_taxis_zona_{datos['zona']['id']}_{fecha}.csv",
            mime="text/csv",
            icon=":material/download:",
            width="stretch",
        )
        st.caption("Una fila por hora, con la banda del pronóstico y los taxis recomendados.")

    st.subheader("4 · ¿Esta regla habría costado menos?")
    if not hay_reales:
        st.info(
            "El 1 de febrero no tiene viajes reales, así que todavía no se puede comparar el costo. "
            "Elija un día de la semana de prueba (25 al 31 de enero) para ver la comparación.",
            icon=":material/event_upcoming:",
        )
        return

    costo_recomendacion = float(costo_horario(enviados, reales, costo_ocioso, costo_perdido).sum())
    costo_p50 = float(costo_horario(p50, reales, costo_ocioso, costo_perdido).sum())
    costo_semana = float(costo_horario(semana, reales, costo_ocioso, costo_perdido).sum())

    tres = st.columns(3)
    tres[0].metric("Costo de su recomendación", f"${costo_recomendacion:,.0f}", border=True,
                   help="Suma de las 24 horas del día con sus costos.")
    tres[1].metric(
        "Enviar el p50", f"${costo_p50:,.0f}",
        delta=f"{costo_p50 - costo_recomendacion:+,.0f} USD", delta_color="inverse", border=True,
        help="Si envía el pronóstico central, ¿cuánto más (o menos) le cuesta?",
    )
    tres[2].metric(
        "Igual que hace una semana", f"${costo_semana:,.0f}",
        delta=f"{costo_semana - costo_recomendacion:+,.0f} USD", delta_color="inverse", border=True,
        help="La regla simple: enviar lo que hubo la misma hora de la semana anterior.",
    )

    ahorro_p50 = costo_p50 - costo_recomendacion
    ahorro_semana = costo_semana - costo_recomendacion
    if ahorro_p50 >= 0 and ahorro_semana >= 0:
        st.success(
            f"Según sus costos, su recomendación habría costado **\\${ahorro_p50:,.0f} menos** que el "
            f"pronóstico central y **\\${ahorro_semana:,.0f} menos** que copiar la semana anterior.",
            icon=":material/savings:",
        )
    else:
        st.warning(
            "Con estos costos, alguna de las reglas alternativas habría sido más barata ese día. "
            "Recuerde que la comparación es de un solo día: lo importante es el comportamiento promedio.",
            icon=":material/balance:",
        )


st.title("¿Cuántos taxis envío?")
st.caption(
    "La cantidad correcta no es el pronóstico central: depende de qué cuesta más, un taxi ocioso "
    "o un pasajero que se queda sin taxi."
)

try:
    info = api_info()
except ErrorAPI as error:
    mostrar_error_api(error)
    st.stop()

sincronizar_estado(info)

fila_zona, fila_fecha = st.columns([2, 3])
with fila_zona:
    zona = selector_zona(info)
with fila_fecha:
    fecha = selector_fecha(info)
publicar_parametros()

try:
    datos = api_pronostico(zona, fecha)
except ErrorAPI as error:
    mostrar_error_api(error)
    st.stop()

st.divider()
panel_decision(datos, fecha)
