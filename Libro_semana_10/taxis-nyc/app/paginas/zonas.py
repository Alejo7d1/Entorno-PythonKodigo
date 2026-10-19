"""Página 2 · Tipos de zona (K-Means + PCA) con selección interactiva."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from comun import (
    cargar_metricas,
    cargar_zonas,
    color_grupo,
    insignia_grupo,
)

st.title("¿Qué tipo de zona es cada una?")
st.caption(
    "K-Means agrupa las 101 zonas con más de 500 viajes según **cómo se usan**: volumen, "
    "distancia, tarifa, propina y franjas horarias. El PCA las dibuja en dos ejes."
)

zonas = cargar_zonas()
metricas = cargar_metricas()
segmentacion = metricas["segmentacion"]
grupos = list(dict.fromkeys(zonas["grupo"]))

varianza = segmentacion["varianza_pca"]

arriba = st.columns(4)
arriba[0].metric("Zonas segmentadas", len(zonas), border=True)
arriba[1].metric("Tipos de zona", len(grupos), border=True)
arriba[2].metric("Grupos elegidos (k)", segmentacion["k"], border=True,
                 help="Elegido con el coeficiente de silueta para k = 2 a 7.")
arriba[3].metric(
    "Variación en 2 ejes",
    f"{varianza[0] + varianza[1]:.0%}",
    border=True,
    help=f"PC1 conserva {varianza[0]:.1%} y PC2 {varianza[1]:.1%} de la variación total.",
)

seleccion = st.pills(
    "Tipos de zona",
    grupos,
    selection_mode="multi",
    default=grupos,
    help="Elija uno o varios tipos para filtrar el mapa y la tabla.",
)
if not seleccion:
    seleccion = grupos

filtrado = zonas[zonas["grupo"].isin(seleccion)].copy()

columnas_insignias = st.columns([max(len(grupo), 8) for grupo in grupos])
for columna, grupo in zip(columnas_insignias, grupos):
    with columna:
        insignia_grupo(grupo)
        st.caption(f"{int((zonas['grupo'] == grupo).sum())} zonas")

mapa, detalle = st.columns([2, 1])

with mapa:
    figura = px.scatter(
        filtrado,
        x="pc1",
        y="pc2",
        color="grupo",
        color_discrete_map={grupo: color_grupo(grupo) for grupo in grupos},
        custom_data=["zona_id"],
        hover_name="zona",
        hover_data={
            "distrito": True,
            "viajes_dia": ":.0f",
            "pc1": False,
            "pc2": False,
            "grupo": False,
        },
        labels={"pc1": "PC1", "pc2": "PC2"},
        height=520,
    )
    figura.update_traces(marker=dict(size=11, line=dict(width=1, color="white")))
    figura.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(title="Tipo de zona", orientation="h", yanchor="bottom", y=1.01, x=0),
    )
    evento = st.plotly_chart(
        figura,
        width="stretch",
        on_select="rerun",
        selection_mode=("points", "box", "lasso"),
        key="mapa_zonas",
    )
    st.caption(
        "Haga clic en un punto, o arrastre un cuadro, para ver el detalle de esas zonas. "
        "También puede filtrar con los botones de arriba."
    )

ids_elegidos: list[int] = []
for punto in getattr(evento, "selection", {}).get("points", []) if evento else []:
    custom = punto.get("customdata") or []
    if custom:
        ids_elegidos.append(int(custom[0]))
ids_elegidos = list(dict.fromkeys(ids_elegidos))

with detalle:
    if ids_elegidos:
        elegidas = zonas[zonas["zona_id"].isin(ids_elegidos)]
        st.markdown(f"### {len(elegidas)} zona(s) seleccionada(s)")
        for _, fila in elegidas.head(6).iterrows():
            with st.container(border=True):
                st.markdown(f"**{fila['zona']}** · {fila['distrito']}")
                insignia_grupo(fila["grupo"])
                st.caption(fila["descripcion"])
                perfil = pd.DataFrame({"hora": range(24), "proporción": fila["perfil"]})
                mini = px.area(perfil, x="hora", y="proporción", height=110)
                mini.update_layout(
                    margin=dict(l=0, r=0, t=0, b=0),
                    xaxis=dict(visible=False),
                    yaxis=dict(visible=False),
                    showlegend=False,
                )
                mini.update_traces(line_color=color_grupo(fila["grupo"]))
                st.plotly_chart(mini, width="stretch", config={"displayModeBar": False})
        if len(elegidas) > 6:
            st.caption(f"Se muestran 6 de {len(elegidas)}. El resto está en la tabla de abajo.")
    else:
        st.markdown("### Cómo son los grupos")
        for grupo in seleccion:
            with st.container(border=True):
                insignia_grupo(grupo)
                descripcion = zonas.loc[zonas["grupo"] == grupo, "descripcion"].iloc[0]
                st.caption(descripcion)
        st.info("Seleccione puntos en el mapa para ver cada zona.", icon=":material/touch_app:")

st.divider()
st.subheader("Todas las zonas")
tabla = filtrado[
    ["zona_id", "zona", "distrito", "grupo", "viajes_dia", "distancia_mediana",
     "tarifa_mediana", "pct_22_5", "perfil"]
].copy()
tabla["tarifa_mediana"] = tabla["tarifa_mediana"].round(2)
tabla["distancia_mediana"] = tabla["distancia_mediana"].round(2)
tabla["pct_22_5"] = tabla["pct_22_5"].round(0)
st.dataframe(
    tabla.sort_values("viajes_dia", ascending=False),
    hide_index=True,
    width="stretch",
    height=420,
    column_config={
        "zona_id": st.column_config.NumberColumn("ID", width="small"),
        "zona": st.column_config.TextColumn("Zona", width="medium"),
        "distrito": st.column_config.TextColumn("Distrito", width="small"),
        "grupo": st.column_config.TextColumn("Tipo", width="medium"),
        "viajes_dia": st.column_config.NumberColumn("Viajes/día", format="%.0f"),
        "distancia_mediana": st.column_config.NumberColumn("Dist. med. (mi)", format="%.2f"),
        "tarifa_mediana": st.column_config.NumberColumn("Tarifa med. ($)", format="%.2f"),
        "pct_22_5": st.column_config.NumberColumn("% de noche", format="%.0f"),
        "perfil": st.column_config.LineChartColumn(
            "Perfil horario (24 h)", width="medium",
            help="Proporción de los viajes de la zona en cada hora del día.",
        ),
    },
)

with st.expander("¿Por qué 4 grupos? Justificación con el coeficiente de silueta"):
    silueta = pd.DataFrame(
        {"k": [int(k) for k in segmentacion["silueta"]], "silueta": list(segmentacion["silueta"].values())}
    ).sort_values("k")
    figura_silueta = go.Figure()
    figura_silueta.add_bar(
        x=silueta["k"].astype(str), y=silueta["silueta"], marker_color="#1F4E79", name="Silueta"
    )
    figura_silueta.add_annotation(
        x=str(segmentacion["k"]), y=silueta["silueta"].max(),
        text="elegido", showarrow=True, arrowhead=2, ay=-30,
    )
    figura_silueta.update_layout(
        height=300, margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title="Número de grupos (k)", yaxis_title="Coeficiente de silueta",
        showlegend=False,
    )
    st.plotly_chart(figura_silueta, width="stretch")
    st.markdown(
        f"La silueta mide qué tan parecida es cada zona a su propio grupo frente al grupo vecino "
        f"(−1 a 1). El mejor valor es **k = {segmentacion['k']}** con "
        f"**{max(segmentacion['silueta'].values()):.3f}**. Los dos ejes del mapa conservan "
        f"**{varianza[0] + varianza[1]:.1%}** de la variación: el dibujo es una vista útil, "
        "no una copia completa de la realidad."
    )
    st.caption(
        "Los nombres de los grupos se asignan por perfil (el de mayor distancia mediana son los "
        "aeropuertos, el de más viajes nocturnos son las zonas nocturnas…), nunca por número: "
        "K-Means numera los grupos al azar en cada entrenamiento."
    )
