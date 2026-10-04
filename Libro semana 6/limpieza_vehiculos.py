import numpy as np
import pandas as pd

COLUMNAS = [
    "fila_carga", "anuncio_id", "precio", "anio", "marca", "modelo",
    "condicion", "combustible", "odometro", "transmision",
    "tipo_vehiculo", "estado", "fecha_publicacion",
]

CATEGORIAS = [
    "marca", "modelo", "condicion", "combustible",
    "transmision", "tipo_vehiculo", "estado",
]

ANIO_MINIMO = 1886


def preparar_textos(X):
    # Comprueba que estén todas las columnas del contrato.
    faltantes = [c for c in COLUMNAS if c not in X.columns]
    if faltantes:
        raise KeyError(f"Faltan columnas: {faltantes}")

    X = X[COLUMNAS].copy()

    # Texto: sin espacios alrededor, sin espacios repetidos y en minúsculas.
    # No se recorta el modelo: 'f-150 lariat' conserva su información.
    for c in CATEGORIAS:
        X[c] = (
            X[c].astype("string")
            .str.strip()
            .str.replace(r"\s+", " ", regex=True)
            .str.lower()
        )

    # El ID y la fecha se tratan aparte: no son categorías.
    X["anuncio_id"] = X["anuncio_id"].astype("string").str.strip()
    X["fecha_publicacion"] = X["fecha_publicacion"].astype("string").str.strip()

    # Cadena vacía o solo espacios -> faltante reconocido.
    X = X.replace("", pd.NA)
    return X


def resolver_duplicados(X):
    X = X.copy()

    # ID válido: solo dígitos y no vacío.
    id_valido = X["anuncio_id"].notna() & X["anuncio_id"].str.fullmatch(r"\d+")
    X = X[id_valido]

    # Ante ID repetido, conservar la fila con menor fila_carga.
    X = X.sort_values("fila_carga", kind="stable")
    X = X.drop_duplicates(subset="anuncio_id", keep="first")
    return X.reset_index(drop=True)


def convertir_tipos(X):
    X = X.copy()

    # Lo interpretable se convierte; lo demás queda como faltante.
    for c in ["precio", "anio", "odometro"]:
        X[c] = pd.to_numeric(X[c], errors="coerce").astype("Float64")

    # Fechas con desplazamiento horario -> instante UTC.
    X["fecha_publicacion"] = pd.to_datetime(
        X["fecha_publicacion"], format="ISO8601", errors="coerce", utc=True
    )
    return X


def aplicar_reglas(X):
    X = X.copy()

    # Precio: no positivo o no interpretable -> faltante (no se inventa).
    X.loc[(X["precio"] <= 0).fillna(False), "precio"] = pd.NA

    # Odómetro: negativo o no interpretable -> faltante.
    X.loc[(X["odometro"] < 0).fillna(False), "odometro"] = pd.NA

    # Año: entero, >= 1886 y, si hay fecha, <= año de publicación + 1.
    # Sin fecha no se puede comprobar el tope relativo: solo se exige el mínimo.
    tope = X["fecha_publicacion"].dt.year.astype("Float64") + 1
    es_entero = (X["anio"] % 1 == 0).fillna(False)
    cumple_minimo = (X["anio"] >= ANIO_MINIMO).fillna(False)
    cumple_tope = ((X["anio"] <= tope) | tope.isna()).fillna(False)

    X.loc[~(es_entero & cumple_minimo & cumple_tope), "anio"] = pd.NA
    X["anio"] = X["anio"].astype("Int64")
    return X


def crear_salida(X):
    X = X.copy()

    # Indicador para analizar precios sin borrar anuncios incompletos.
    X["precio_utilizable"] = X["precio"].notna() & (X["precio"] > 0)

    # Antigüedad con el año UTC; un modelo más nuevo que el anuncio es 0.
    anio_publicacion = X["fecha_publicacion"].dt.year.astype("Float64")
    antiguedad = (anio_publicacion - X["anio"].astype("Float64")).clip(lower=0)
    X["antiguedad_al_publicar"] = antiguedad.astype("Int64")

    # Se retira la columna técnica y se fija el orden final.
    X = X.drop(columns=["fila_carga"])
    orden = [
        "anuncio_id", "precio", "anio", "marca", "modelo", "condicion",
        "combustible", "odometro", "transmision", "tipo_vehiculo", "estado",
        "fecha_publicacion", "precio_utilizable", "antiguedad_al_publicar",
    ]
    return X[orden]
