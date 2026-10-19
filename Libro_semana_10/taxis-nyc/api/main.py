"""API de pronóstico de viajes de taxi amarillo en Nueva York.

Contrato:
    GET /               → estado del servicio
    GET /info           → zonas pronosticables, fechas disponibles y cuantiles
    GET /pronostico     → 24 horas de pronóstico para una zona y una fecha

La API **no recalcula los lags**: lee `demanda.parquet`, que ya trae las variables
calculadas del 25 de enero al 1 de febrero, busca las 24 filas de la zona y la fecha
y devuelve los cuantiles ordenados.
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from fastapi import FastAPI, HTTPException, Query

DIR = Path(__file__).resolve().parent
ESTADO: dict = {}

VERSION = "1.0.0"


def cargar_recursos() -> dict:
    """Carga modelo, datos y catálogo una sola vez, al arrancar."""
    metadatos = json.loads((DIR / "metadatos.json").read_text(encoding="utf-8"))
    catalogo = json.loads((DIR / "zonas.json").read_text(encoding="utf-8"))

    modelo = xgb.XGBRegressor()
    modelo.load_model(str(DIR / "modelo_pronostico.ubj"))

    demanda = pd.read_parquet(DIR / "demanda.parquet")
    demanda["hora"] = pd.to_datetime(demanda["hora"])
    demanda["fecha"] = demanda["hora"].dt.normalize()
    # El parquet guarda el nombre legible para el contrato; el modelo espera `lag_168`.
    demanda = demanda.rename(columns={"hace_una_semana": "lag_168"})

    zonas_por_id = {
        int(zona["id"]): {
            "id": int(zona["id"]),
            "nombre": str(zona.get("nombre") or f"Zona {zona['id']}"),
            "distrito": str(zona.get("distrito") or "Sin distrito"),
            "grupo": zona.get("grupo"),
        }
        for zona in catalogo["zonas"]
    }
    fechas = sorted(fecha.strftime("%Y-%m-%d") for fecha in demanda["fecha"].unique())

    return {
        "modelo": modelo,
        "demanda": demanda,
        "variables": metadatos["variables"],
        "categorias": metadatos["categorias_zona"],
        "cuantiles": metadatos["cuantiles"],
        "zonas_por_id": zonas_por_id,
        "fechas": fechas,
        "entrenamiento_hasta": catalogo.get("fecha_entrenamiento_hasta"),
    }


@asynccontextmanager
async def lifespan(_: FastAPI):
    ESTADO.update(cargar_recursos())
    yield
    ESTADO.clear()


app = FastAPI(
    title="Taxis NYC · API de pronóstico",
    description=(
        "Pronóstico horario de viajes por zona para la ciudad de Nueva York "
        "con bandas de incertidumbre (cuantiles p10 a p90)."
    ),
    version=VERSION,
    lifespan=lifespan,
)


def _predecir(filas: pd.DataFrame) -> np.ndarray:
    """Devuelve los cuantiles ordenados de menor a mayor para cada fila."""
    matriz = filas[ESTADO["variables"]].copy()
    matriz["PULocationID"] = pd.Categorical(
        matriz["PULocationID"], categories=ESTADO["categorias"]
    )
    return np.sort(ESTADO["modelo"].predict(matriz), axis=1)


@app.get("/", summary="Estado del servicio")
def raiz() -> dict:
    """Comprueba rápido que la API está en línea (la app usa esto para el indicador)."""
    return {
        "estado": "en línea",
        "servicio": "Taxis NYC · pronóstico horario",
        "version": VERSION,
        "zonas": len(ESTADO.get("zonas_por_id", {})),
    }


@app.get("/info", summary="Zonas, fechas y cuantiles disponibles")
def info() -> dict:
    """Todo lo que la app necesita para armar sus selectores."""
    return {
        "zonas": sorted(ESTADO["zonas_por_id"].values(), key=lambda z: str(z["nombre"])),
        "fechas": ESTADO["fechas"],
        "cuantiles": ESTADO["cuantiles"],
        "entrenamiento_hasta": ESTADO["entrenamiento_hasta"],
    }


@app.get("/pronostico", summary="Pronóstico de las 24 horas de un día")
def pronostico(
    zona_id: int = Query(..., description="Identificador de la zona de origen (PULocationID)"),
    fecha: date = Query(..., description="Fecha a pronosticar en formato AAAA-MM-DD"),
) -> dict:
    zona = ESTADO["zonas_por_id"].get(zona_id)
    if zona is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"La zona {zona_id} no tiene pronóstico: solo se pronostican las zonas con "
                f"3,000 viajes o más en enero de 2024."
            ),
        )

    dia = pd.Timestamp(fecha)
    filas = ESTADO["demanda"][
        (ESTADO["demanda"]["PULocationID"] == zona_id) & (ESTADO["demanda"]["fecha"] == dia)
    ].sort_values("hora")

    if filas.empty:
        disponibles = ", ".join(ESTADO["fechas"])
        raise HTTPException(
            status_code=404,
            detail=f"No hay datos para la zona {zona_id} el {fecha}. Fechas disponibles: {disponibles}.",
        )

    predicciones = _predecir(filas)
    nombres = ESTADO["cuantiles"]

    horas = []
    for posicion, (_, fila) in enumerate(filas.iterrows()):
        real = fila["real"]
        hace_una_semana = fila["lag_168"]
        horas.append(
            {
                "hora": int(fila["hora"].hour),
                "real": None if pd.isna(real) else int(round(float(real))),
                "hace_una_semana": None
                if pd.isna(hace_una_semana)
                else int(round(float(hace_una_semana))),
                "cuantiles": {
                    nombre: round(float(valor), 1)
                    for nombre, valor in zip(nombres, predicciones[posicion])
                },
            }
        )

    return {
        "zona": zona,
        "fecha": fecha.strftime("%Y-%m-%d"),
        "sin_datos_reales": bool(filas["real"].isna().all()),
        "horas": horas,
    }
