"""Página 4 · Ficha del modelo (model card) y comunicación ética."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from comun import cargar_metricas

st.title("Ficha del modelo")
st.caption(
    "Un documento corto y estándar para que cualquier persona entienda el modelo **antes** de usarlo. "
    "Todas las cifras salen del notebook `preparacion.ipynb`."
)

metricas = cargar_metricas()
datos = metricas["datos"]
modelo = metricas["modelo"]
regla = metricas["regla_simple"]
segmentacion = metricas["segmentacion"]

zonas_con_viajes = datos.get("zonas_con_viajes", 260)
sin_pronostico = zonas_con_viajes - datos["zonas_pronostico"]

# --------------------------------------------------------------------------- resumen
columnas = st.columns(4)
columnas[0].metric(
    "Error típico · MAE (viajes/hora)", f"{modelo['mae_p50']:.1f}", border=True,
    help="Diferencia media entre la mediana prevista y los viajes reales, en la semana de prueba.",
)
columnas[1].metric(
    "Regla simple · MAE (viajes/hora)", f"{regla['mae']:.1f}", border=True,
    help="El mismo error, pero usando los viajes de la misma hora de la semana anterior.",
)
columnas[2].metric(
    "Cobertura del rango 80 %", f"{modelo['cobertura_80']:.0%}", border=True,
    help="Porcentaje de horas reales que caen entre p10 y p90. Lo esperado sería ~80 %.",
)
columnas[3].metric(
    "Zonas donde pierde", f"{modelo['zonas_donde_pierde']} de {modelo['zonas_evaluadas']}", border=True,
    help="Zonas en las que la regla simple tuvo menos error que el modelo en la semana de prueba.",
)

st.divider()

# --------------------------------------------------------------------------- propósito
izquierda, derecha = st.columns(2)
with izquierda:
    with st.container(border=True):
        st.subheader("Para qué sirve")
        st.markdown(
            "Estimar **cuántos viajes de taxi amarillo habrá en cada zona y cada hora del día siguiente**, "
            "con un rango de incertidumbre. Con eso, una persona que coordina una flota puede decidir "
            "cuántos vehículos enviar a cada zona sin adivinar.\n\n"
            "**Lo que no hace:** no dice cuánto se va a facturar, no reparte taxis entre conductores "
            "y no decide por usted. Solo entrega el pronóstico y su margen de error."
        )
    with st.container(border=True):
        st.subheader("Con qué datos se entrenó")
        st.markdown(
            f"- **{datos['viajes_enero_2024']:,}** viajes de taxi amarillo de enero de 2024 (NYC TLC).\n"
            f"- **{datos['zonas_pronostico']}** zonas de origen con 3,000 viajes o más en el mes "
            f"(excluidas las zonas «Unknown»).\n"
            f"- Entrenamiento: del **{metricas['entrenamiento']['desde']}** al "
            f"**{metricas['entrenamiento']['hasta']}** ({metricas['entrenamiento']['filas']:,} filas zona-hora).\n"
            f"- Prueba: del **{metricas['prueba']['desde']}** al **{metricas['prueba']['hasta']}** "
            f"({metricas['prueba']['filas']:,} filas zona-hora).\n"
            "- Variables: viajes de hace 24, 48, 167, 168 y 169 horas, promedio del día anterior, "
            "hora, día de la semana, feriado y zona."
        )

with derecha:
    with st.container(border=True):
        st.subheader("Cómo se evaluó")
        st.markdown(
            "- **Por tiempo**, nunca con `train_test_split`: se entrena hasta el 24 de enero y se "
            "prueba del 25 al 31. Pronosticar hacia adelante es el único escenario realista.\n"
            "- Ningún lag menor a 24 horas: el pronóstico se hace el día anterior para todo el día "
            "siguiente, así que no se puede usar información de horas que aún no ocurrieron.\n"
            f"- Métrica principal: **MAE de la mediana** y **pérdida pinball** para los 9 cuantiles "
            f"({modelo['pinball']:.2f}).\n"
            f"- Calibración: **cobertura real del rango p10–p90**.\n"
            "- Comparación obligatoria contra la regla simple **«igual que hace una semana»**."
        )
    with st.container(border=True):
        st.subheader("Qué tan bien funciona")
        mejora = regla["mejora_relativa_pct"]
        if mejora >= 0:
            st.markdown(
                f"El modelo **gana por poco**: mejora el MAE de la regla simple en "
                f"**{mejora:.1f} %** ({modelo['mae_p50']:.2f} contra {regla['mae']:.2f} viajes por hora). "
                "Es esperable: la demanda de taxis se repite mucho de una semana a otra."
            )
        else:
            st.markdown(
                f"El modelo **pierde** contra la regla simple en la semana de prueba: su MAE es "
                f"**{abs(mejora):.1f} %** peor ({modelo['mae_p50']:.2f} contra {regla['mae']:.2f})."
            )
        st.markdown(
            f"Su valor está en **el rango**: la regla simple no dice nada sobre cuánto puede variar "
            f"el resultado. El rango p10–p90 cubrió el **{modelo['cobertura_80']:.1%}** de las horas "
            f"reales, frente al **80 %** que se esperaría de un rango bien calibrado: el modelo es "
            "algo **conservador** (la banda es un poco más ancha de lo necesario)."
        )

# --------------------------------------------------------------------------- errores
st.divider()
st.subheader("Dónde se equivoca más")
st.markdown(
    "Cruzar el error con la segmentación de zonas responde una pregunta que el error global esconde: "
    "**¿a quién le está fallando el modelo?**"
)

tabla_grupos = pd.DataFrame(metricas["por_grupo"])
tabla_grupos = tabla_grupos.rename(
    columns={
        "grupo": "Tipo de zona",
        "zonas": "Zonas",
        "mae_modelo": "MAE modelo",
        "mae_base": "MAE regla simple",
        "cobertura": "Cobertura 80 %",
    }
)
st.dataframe(
    tabla_grupos.sort_values("MAE modelo", ascending=False),
    hide_index=True,
    width="stretch",
    column_config={
        "Tipo de zona": st.column_config.TextColumn(width="medium"),
        "MAE modelo": st.column_config.NumberColumn(format="%.1f"),
        "MAE regla simple": st.column_config.NumberColumn(format="%.1f"),
        "Cobertura 80 %": st.column_config.ProgressColumn(format="%.0f%%", min_value=0, max_value=1),
    },
)

peor_grupo = max(metricas["por_grupo"], key=lambda fila: fila["mae_modelo"])
st.markdown(
    f"- El error más alto está en **{peor_grupo['grupo']}** ({peor_grupo['mae_modelo']:.1f} viajes por hora): "
    "son pocas zonas y muy grandes, donde una hora mala pesa mucho.\n"
    "- En **zonas nocturnas** el modelo **pierde** contra la regla simple: el patrón semanal "
    "ya explica casi todo y el modelo añade poco.\n"
    "- En las zonas de **barrio con poca demanda** el error es pequeño en términos absolutos, pero "
    "también pequeño el número de viajes: **un error de 2 viajes puede ser el 30 % de la demanda**."
)

st.markdown("**Las zonas donde el modelo falla más**")
tabla_peores = pd.DataFrame(metricas["peores_zonas"]).rename(
    columns={
        "zona": "Zona",
        "grupo": "Tipo",
        "mae_modelo": "MAE modelo",
        "mae_base": "MAE regla simple",
        "cobertura": "Cobertura",
    }
)
st.dataframe(
    tabla_peores[["Zona", "Tipo", "MAE modelo", "MAE regla simple", "Cobertura"]],
    hide_index=True,
    width="stretch",
    column_config={
        "MAE modelo": st.column_config.NumberColumn(format="%.1f"),
        "MAE regla simple": st.column_config.NumberColumn(format="%.1f"),
        "Cobertura": st.column_config.NumberColumn(format="%.0f%%"),
    },
)

# --------------------------------------------------------------------------- limitaciones
st.divider()
with st.container(border=True):
    st.subheader("Limitaciones y usos no recomendados")
    st.markdown(
        f"""
**Lo que el modelo no puede ver**

- **Está entrenado con un solo mes** (enero de 2024, sin eventos especiales): no aprende
  estacionalidad, ni el efecto de la lluvia, ni de un concierto o un cierre de calles.
- **Solo cubre taxis amarillos**, que se toman sobre todo en la calle y en el centro. No representa
  a los viajes de aplicaciones ni a otros vehículos.
- **No pronostica {sin_pronostico} de las {zonas_con_viajes} zonas** con viajes del mes: quedaron
  fuera por tener menos de 3,000 viajes. Son el {100 - datos["viajes_cubiertos_pct"]:.1f} % de los viajes.
- **Supone un taxi = un viaje por hora.** Si un viaje dura 20 minutos, se podría atender más de
  un pasajero por hora; el plan es una aproximación de carga, no un cálculo exacto de turnos.
- **Los cuantiles se ordenan por fila** antes de usarlos: el modelo puede entregar un p60 menor
  que el p50, y sin ordenar la banda sería incoherente.
- **El modelo es el de la semana de prueba y queda congelado**: si la ciudad cambia, hay que
  reentrenarlo y volver a medir.

**Usos no recomendados**

- **Recortar el servicio en barrios de baja demanda.** Ahí el error absoluto es pequeño pero el
  relativo es enorme; usar el modelo para justificar menos taxis dejaría a personas sin servicio,
  precisamente donde hay menos alternativas.
- **Fijar turnos de conductores con el p50.** La mediana no es un objetivo: sin mirar la banda y
  los costos, la mitad de los días se quedará corto.
- **Usarlo para zonas sin pronóstico o para fechas fuera de enero de 2024.** La API responde 404
  a propósito en esos casos.

**¿A quién podría perjudicar una mala decisión?**

- A **pasajeros de zonas periféricas**, si se interpreta «poca demanda» como «poca prioridad».
- A **conductores** que reciben un plan demasiado ajustado y pasan horas sin viaje.
- A **quienes dependen del taxi de la calle** en barrios donde no llegan las aplicaciones y que
  no aparecen bien representados por un modelo entrenado con datos de Manhattan.
"""
    )
    st.caption(
        "Regla simple para decidir: use el pronóstico como **un rango**, no como un número; "
        "y revise la banda antes de tomar una decisión que afecte a personas."
    )

# --------------------------------------------------------------------------- opinión
st.divider()
estrellas = st.feedback("stars", key="valoracion_ficha")
if estrellas is not None:
    st.toast("¡Gracias! Su opinión se tendrá en cuenta para la próxima versión.", icon=":material/favorite:")
    st.caption("Valoración registrada en esta sesión.")
