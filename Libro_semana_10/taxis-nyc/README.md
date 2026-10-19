# Taxis NYC — una app para quien toma decisiones

Herramienta para coordinar una flota de taxis amarillos en Nueva York: pronostica **cuántos viajes
habrá en cada zona y cada hora del día siguiente**, explica **qué tipo de zona es cada una** y
recomienda **cuántos taxis enviar** según lo que cuesta equivocarse.

> Actividad del Módulo 2 (AIMLF1): FastAPI + despliegue, K-Means + PCA y series de tiempo.

## Enlaces publicados

| Qué | Enlace |
|---|---|
| **App (Streamlit Cloud)** | `https://taxisnyc-alejo-kodigo.streamlit.app/` |
| **API (Render)** | `https://taxisnyc-alejokodigo.onrender.com/docs` |
| **Notebook de preparación** | [`preparacion.ipynb`](preparacion.ipynb) |

**Integrantes:** Alejandro Orellana

## Resultados principales

Todas las cifras salen de `preparacion.ipynb` y se guardan en `app/data/metricas.json`.

| Qué | Valor |
|---|---|
| Viajes de enero de 2024 analizados | 2,954,246 |
| Zonas pronosticadas (≥ 3,000 viajes) | 58 de 259 (97.7 % de los viajes) |
| Zonas segmentadas (≥ 500 viajes) | 101 |
| Modelo | XGBoost de cuantiles (p10…p90, 9 cuantiles) con lags ≥ 24 h y calendario |
| Entrenamiento / prueba | hasta el 24 de enero / del 25 al 31 de enero |
| MAE mediana del modelo | **11.71** viajes por hora |
| MAE regla «igual que hace una semana» | **11.88** viajes por hora (mejora: **+1.5 %**) |
| Cobertura del rango p10–p90 | **86.7 %** (lo esperado es ~80 %) |
| Segmentación | **k = 4** (silueta 0.416); PCA conserva **64.8 %** de la varianza |
| Costo con $40 / $10 (pasajero perdido / taxi ocioso) | cuantil óptimo **0.80** |

## Estructura

```text
taxis-nyc/
├── preparacion.ipynb          # datos, modelos, métricas y artefactos
├── example.env                # plantilla de variables de entorno (copiar a app/.env)
├── api/
│   ├── main.py                # FastAPI: /, /info, /pronostico
│   ├── modelo_pronostico.ubj  # modelo (1.7 MB)
│   ├── demanda.parquet        # horas del 25 ene al 1 feb con variables ya calculadas
│   ├── zonas.json             # zonas, fechas y cuantiles para /info
│   ├── metadatos.json         # orden de variables y categorías de zona
│   └── requirements.txt
├── app/
│   ├── streamlit_app.py       # entrada con st.navigation
│   ├── comun.py               # cliente de la API y utilidades compartidas
│   ├── paginas/
│   │   ├── pronostico.py      # 1 · pronóstico con banda de incertidumbre
│   │   ├── zonas.py           # 2 · segmentación K-Means + PCA
│   │   ├── decision.py        # 3 · cuántos taxis enviar
│   │   ├── ficha.py           # 4 · ficha del modelo
│   │   └── monitoreo.py       # 5 · extra: error día a día y alertas
│   ├── data/                  # segmentación, métricas y monitoreo precalculados
│   ├── .streamlit/config.toml # tema de colores
│   └── requirements.txt
└── README.md
```

La regla de oro: **la app nunca carga el modelo**. Le pide el pronóstico a la API, que es la única
que lo tiene.

## Cómo correr el proyecto en tu computadora

Requisitos: Python 3.10+ y los datos del mes en la carpeta que contiene `taxis-nyc/`.

```bash
# 1. Dependencias
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt -r api/requirements.txt

# 2. API (deja esta terminal abierta)
cd api
uvicorn main:app --reload
# → http://localhost:8000/docs

# 3. App (otra terminal)
cd app
streamlit run streamlit_app.py
# → http://localhost:8501
```


`comun.py` lee, en este orden: `st.secrets["API_URL"]`, la variable `API_URL` (incluida la de
`app/.env`) y, si no hay ninguna, `http://localhost:8000`.

Para regenerar todos los artefactos (modelo, parquet, métricas y CSV de la app) basta con
**ejecutar el notebook de principio a fin** desde la carpeta `Libro semana 10` o desde `taxis-nyc/`.

### Datos necesarios para el notebook

El notebook lee dos archivos de la carpeta que lo contiene **o de su carpeta padre**. No se encuentran en el repositorio, descárgalos antes de ejecutarlo:

```bash
curl -O https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet
curl -O https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv
```

Los artefactos ya están generados en el repositorio, así que **la API y la app funcionan sin volver
a ejecutar el notebook**.

## El contrato de la API

| Endpoint | Recibe | Devuelve |
|---|---|---|
| `GET /` | — | estado del servicio |
| `GET /info` | — | zonas (`id`, `nombre`, `distrito`), fechas y cuantiles |
| `GET /pronostico?zona_id=161&fecha=2024-01-25` | zona y fecha `AAAA-MM-DD` | las 24 horas con sus cuantiles, el valor real (`null` si no existe) y el de hace una semana |

Ejemplo real (hora 17):

```json
{
  "zona": {"id": 161, "nombre": "Midtown Center", "distrito": "Manhattan", "grupo": "Zonas de oficinas y tarde"},
  "fecha": "2024-01-25",
  "sin_datos_reales": false,
  "horas": [
    {
      "hora": 17,
      "real": 580,
      "hace_una_semana": 623,
      "cuantiles": {"p10": 412.1, "p20": 481.1, "p30": 493.5, "p40": 505.1, "p50": 521.1,
                    "p60": 536.5, "p70": 565.8, "p80": 587.9, "p90": 605.2}
    }
  ]
}
```

Los errores se responden con **404 y un mensaje claro**, nunca con una excepción:

```json
{"detail": "La zona 9999 no tiene pronóstico: solo se pronostican las zonas con 3,000 viajes o más en enero de 2024."}
```

La API **no recalcula los lags**: `demanda.parquet` ya trae las variables calculadas del 25 de
enero al 1 de febrero y solo busca la fila y predice.

## Las cinco páginas

1. **Pronóstico** — mediana, banda p10–p90, puntos reales y comparación con «hace una semana».
   El 1 de febrero se avisa explícitamente de que no hay datos reales.
2. **Tipos de zona** — mapa PCA con selección de puntos (clic, cuadro o lazo), filtros por grupo,
   badges, tabla con perfil horario y justificación de *k* con la silueta.
3. **Cuántos taxis enviar** — dos controles de costo, cuantil óptimo con su fórmula, plan por hora,
   comparación de costos contra p50 y contra la regla simple, y descarga del plan en CSV.
4. **Ficha del modelo** — propósito, datos, evaluación, cobertura real, errores por tipo de zona,
   limitaciones y usos no recomendados, con valoración del usuario.
5. **Monitoreo (extra)** — error día a día frente a un límite configurable, zonas con días atípicos
   y alertas.


## Funciones avanzadas de Streamlit usadas

| Función | Dónde |
|---|---|
| `st.navigation` + `st.Page` | `streamlit_app.py` (cinco páginas con íconos) |
| `@st.fragment` | `decision.py`: mover un costo no recarga toda la página |
| `@st.dialog` | `pronostico.py`: ventana de ayuda |
| `st.plotly_chart(on_select="rerun")` | `zonas.py`: seleccionar zonas en el mapa |
| `st.column_config` | `ProgressColumn`, `LineChartColumn`, `NumberColumn` en tres páginas |
| `@st.cache_data` | `comun.py`: no repetir llamadas a la API (1 h) ni lecturas de CSV |
| `st.secrets` | `comun.py`: dirección de la API fuera del código |
| `st.query_params` + `st.session_state` | la zona y la fecha se recuerdan y se pueden compartir por link |
| `st.status`, `st.toast` | avance de la conexión y avisos |
| `st.pills`, `st.segmented_control` | filtros y selector de fecha con botones |
| `st.badge`, `st.metric(chart_data=...)` | grupos etiquetados y métricas con mini gráfico |
| `.streamlit/config.toml` | tema de colores propio |

## Decisiones de diseño (y trampas evitadas)

- **Ningún lag menor a 24 horas.** El pronóstico se hace el día anterior para todo el día
  siguiente; usar `lag_1` daría métricas excelentes en el notebook y un modelo inservible en
  producción. Es fuga de datos.
- **División por tiempo**, nunca `train_test_split`.
- **Un solo modelo de 9 cuantiles** (`reg:quantileerror` + `multi_output_tree`): pesa 1.7 MB y
  predice 24 horas en milisegundos.
- **Cuantiles ordenados por fila** con `np.sort(..., axis=1)` antes de usarlos: el modelo puede
  devolver un p60 menor que el p50.
- **Zona como categoría nativa** de XGBoost, guardando el orden de las categorías en
  `metadatos.json` para que la API cargue el modelo exactamente como se entrenó.
- **Nombres de grupo por perfil, no por número**: K-Means numera los grupos al azar, así que el
  nombre se asigna con reglas sobre el perfil (mayor distancia mediana → aeropuertos, más viajes
  nocturnos → zonas nocturnas…).
- **La zona 264 («Unknown») se excluye** aunque tenga miles de viajes: el enunciado pide descartar
  las zonas «Unknown».

## Limitaciones

- Entrenado con **un solo mes**: no captura estacionalidad, clima ni eventos.
- Solo **taxis amarillos**.
- **201 de las 259 zonas con viajes no tienen pronóstico** (2.3 % de los viajes).
- Supone **un taxi = un viaje por hora**.
- Gana **por poco** a la regla simple. Su valor está en el **rango de incertidumbre**, que la regla
  simple no entrega.
- **No usar** para recortar servicio en barrios de baja demanda ni para fijar turnos con el p50.
