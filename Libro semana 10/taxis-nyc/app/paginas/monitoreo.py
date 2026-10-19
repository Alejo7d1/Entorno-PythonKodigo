"""Página 5 (extra) · Monitoreo del error día a día con alertas."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from comun import cargar_metricas, cargar_monitoreo, etiqueta_fecha, etiqueta_fecha_larga

AZUL = "#1F4E79"
ROJO = "#C0392B"
GRIS = "#8A8F98"

st.title("Monitoreo del error")
st.caption(
    "Un modelo no termina cuando se publica: hay que vigilarlo. Esta página mide el error de cada "
    "día de la semana de prueba y avisa cuando supera un límite."
)

diario, por_zona = cargar_monitoreo()
metricas = cargar_metricas()
umbral_inicial = round(float(metricas["monitoreo"]["umbral_mae"]) * 2) / 2

umbral = st.slider(
    "Límite de alerta para el MAE diario (viajes por hora)",
    min_value=4.0,
    max_value=30.0,
    value=umbral_inicial,
    step=0.5,
    help=(
        "Valor de referencia: el MAE del modelo en la semana de prueba más un 35 % de margen "
        f"({umbral_inicial:.1f}). Si un día lo supera, conviene revisar qué pasó."
    ),
)

FACTOR_ATIPICO = 2.0

dias_en_alerta = diario[diario["mae_modelo"] > umbral]
promedio = float(diario["mae_modelo"].mean())
peor = diario.loc[diario["mae_modelo"].idxmax()]

por_zona_resumen = por_zona.groupby(["zona", "PULocationID"]).agg(
    mae_promedio=("mae_modelo", "mean"),
    mae_maximo=("mae_modelo", "max"),
    mae_regla=("mae_base", "mean"),
).reset_index()
por_zona_resumen["ratio"] = por_zona_resumen["mae_maximo"] / por_zona_resumen["mae_promedio"]
por_zona_resumen = por_zona_resumen.sort_values("ratio", ascending=False)
zonas_atipicas = int((por_zona_resumen["ratio"] >= FACTOR_ATIPICO).sum())

resumen = st.columns(4)
resumen[0].metric("MAE promedio de la semana", f"{promedio:.1f}", border=True)
resumen[1].metric("Peor día", etiqueta_fecha(peor["fecha"].strftime("%Y-%m-%d")),
                  delta=f"MAE {peor['mae_modelo']:.1f}", delta_color="off", border=True)
resumen[2].metric("Días sobre el límite", f"{len(dias_en_alerta)} de {len(diario)}", border=True)
resumen[3].metric(
    "Zonas con un día atípico", f"{zonas_atipicas} de {len(por_zona_resumen)}", border=True,
    help=(
        "Una zona es atípica cuando su peor día supera "
        f"{FACTOR_ATIPICO:.0f} veces su error promedio. Se compara contra sí misma porque un "
        "aeropuerto y un barrio tranquilo tienen escalas muy distintas."
    ),
)

if len(dias_en_alerta) > 0:
    st.error(
        "**Alerta:** " + ", ".join(
            f"{etiqueta_fecha(fila['fecha'].strftime('%Y-%m-%d'))} (MAE {fila['mae_modelo']:.1f})"
            for _, fila in dias_en_alerta.iterrows()
        ) + f" supera el límite de {umbral:.1f} viajes por hora.",
        icon=":material/notification_important:",
    )
    st.toast("Hay días por encima del límite de error.", icon=":material/warning:")
else:
    st.success(
        f"Ningún día de la semana de prueba supera el límite de {umbral:.1f}. "
        "El modelo se mantiene dentro de lo esperado.",
        icon=":material/verified:",
    )

figura = go.Figure()
figura.add_bar(
    x=[etiqueta_fecha(fecha.strftime("%Y-%m-%d")) for fecha in diario["fecha"]],
    y=diario["mae_modelo"],
    name="MAE del modelo",
    marker_color=[ROJO if valor > umbral else AZUL for valor in diario["mae_modelo"]],
)
figura.add_trace(
    go.Scatter(
        x=[etiqueta_fecha(fecha.strftime("%Y-%m-%d")) for fecha in diario["fecha"]],
        y=diario["mae_base"],
        name="Regla simple (hace una semana)",
        mode="lines+markers",
        line=dict(color=GRIS, dash="dash"),
    )
)
figura.add_hline(
    y=umbral, line_dash="dot", line_color=ROJO,
    annotation_text=f"Límite {umbral:.1f}", annotation_position="top left",
)
figura.update_layout(
    height=380,
    margin=dict(l=10, r=10, t=10, b=10),
    yaxis=dict(title="MAE (viajes por hora)", rangemode="tozero"),
    xaxis=dict(title="Día de la semana de prueba"),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    bargap=0.35,
)
st.plotly_chart(figura, width="stretch")

st.divider()
izquierda, derecha = st.columns([1, 2])

with izquierda:
    zona_elegida = st.selectbox(
        "Ver una zona",
        sorted(por_zona["zona"].unique()),
        help="Error diario de esa zona frente al de la regla simple.",
    )

with derecha:
    detalle = por_zona[por_zona["zona"] == zona_elegida].sort_values("fecha")
    if not detalle.empty:
        figura_zona = go.Figure()
        figura_zona.add_trace(go.Scatter(
            x=[etiqueta_fecha(f.strftime("%Y-%m-%d")) for f in detalle["fecha"]],
            y=detalle["mae_modelo"], name="Modelo", mode="lines+markers",
            line=dict(color=AZUL, width=2.5),
        ))
        figura_zona.add_trace(go.Scatter(
            x=[etiqueta_fecha(f.strftime("%Y-%m-%d")) for f in detalle["fecha"]],
            y=detalle["mae_base"], name="Regla simple", mode="lines+markers",
            line=dict(color=GRIS, dash="dash"),
        ))
        figura_zona.add_hline(y=umbral, line_dash="dot", line_color=ROJO)
        figura_zona.update_layout(
            height=300, margin=dict(l=10, r=10, t=10, b=10),
            yaxis=dict(title="MAE (viajes por hora)", rangemode="tozero"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        )
        st.plotly_chart(figura_zona, width="stretch")

st.markdown("**Zonas ordenadas por su peor día frente a su promedio**")
resumen_zonas = por_zona_resumen.copy()
resumen_zonas["alerta"] = np.where(resumen_zonas["ratio"] >= FACTOR_ATIPICO, "Sí", "No")
st.dataframe(
    resumen_zonas.rename(
        columns={
            "zona": "Zona", "PULocationID": "ID", "mae_promedio": "MAE promedio",
            "mae_maximo": "MAE peor día", "mae_regla": "MAE regla simple",
            "ratio": "Peor día / promedio", "alerta": "Día atípico",
        }
    ),
    hide_index=True,
    width="stretch",
    height=340,
    column_config={
        "MAE promedio": st.column_config.NumberColumn(format="%.1f"),
        "MAE peor día": st.column_config.NumberColumn(format="%.1f"),
        "MAE regla simple": st.column_config.NumberColumn(format="%.1f"),
        "Peor día / promedio": st.column_config.ProgressColumn(
            format="%.2f×", min_value=0.0, max_value=3.0,
            help=f"Valores de {FACTOR_ATIPICO:.0f}× o más se marcan como día atípico.",
        ),
    },
)
st.caption(
    "El límite del gráfico se elige aquí y en el notebook (`metricas.json`). Un límite demasiado "
    "ajustado genera falsas alarmas; uno demasiado flojo no avisa a tiempo. Es un punto de partida, "
    "no una verdad absoluta."
)
