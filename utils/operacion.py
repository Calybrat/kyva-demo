"""Carga de los datos de OPERACIÓN: inventario, compras, automatizaciones y alertas.

Vive aparte de `datos.py` por una razón que costó un despliegue roto:
**Streamlit Cloud re-ejecuta `app.py` en cada rerun pero NO reimporta los
módulos que ya están en `sys.modules`.** Al agregar funciones al final de
`datos.py`, el contenedor siguió sirviendo la versión vieja en memoria —el menú
mostraba las pantallas nuevas, porque sale de `app.py`, y `datos.alertas()` no
existía—. Un archivo que nunca se había importado no tiene ese problema.

La lección general: al agregar capacidades a un panel ya desplegado, conviene
que entren por un módulo nuevo y no como apéndice de uno vivo.

Todo lo de aquí lo produce `data/gen_operacion.py`, que lo DERIVA del catálogo
y de las líneas de pedido. No es una fuente paralela: si se generara aparte, la
pantalla de surtido diría 108 botellas de Chivas y la de reposición 74.
"""
import numpy as np
import pandas as pd
import streamlit as st

from utils.datos import _leer, CORTE

# El pico de fin de año. Para un distribuidor de licores noviembre y diciembre
# son el año entero, y el corte del panel —31 de agosto— cae justo dentro de la
# ventana en que esa compra se decide.
PICO = pd.Timestamp("2026-12-01")
FACTOR_PICO = 2.6


@st.cache_data(show_spinner="Cargando inventario…")
def inventario() -> pd.DataFrame:
    df = _leer("inventario_bodega.csv", keep_default_na=False)
    for c in ("unidades", "punto_reorden", "necesidad_pico", "faltante_pico",
              "dias_reposicion", "unidades_90d", "dias_para_limite"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    for c in ("costo_unit", "valor_inventario", "demanda_dia", "dias_cobertura"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in ("hay_que_pedir", "nacional", "surtida_aqui"):
        df[c] = df[c].astype(str) == "True"
    df["fecha_limite_pedido"] = pd.to_datetime(df["fecha_limite_pedido"])
    df["valor_faltante"] = df["faltante_pico"] * df["costo_unit"]
    return df


@st.cache_data
def proveedores() -> pd.DataFrame:
    df = _leer("proveedores.csv", keep_default_na=False)
    df["nacional"] = df["nacional"].astype(str) == "True"
    return df


@st.cache_data
def ordenes_compra() -> pd.DataFrame:
    df = _leer("ordenes_compra.csv", keep_default_na=False)
    for c in ("emitida", "eta", "eta_real"):
        df[c] = pd.to_datetime(df[c])
    return df


@st.cache_data
def automatizaciones() -> pd.DataFrame:
    df = _leer("automatizaciones.csv", keep_default_na=False)
    df["aprueba"] = df["aprueba"].astype(str) == "True"
    return df


@st.cache_data(show_spinner="Cargando bitácora…")
def ejecuciones() -> pd.DataFrame:
    df = _leer("ejecuciones.csv", keep_default_na=False)
    df["momento"] = pd.to_datetime(df["momento"])
    return df


@st.cache_data
def alertas() -> pd.DataFrame:
    df = _leer("alertas.csv", keep_default_na=False)
    df["cuando"] = pd.to_datetime(df["cuando"])
    return df


@st.cache_data
def resumen_operacion() -> dict:
    """Los números que más de una pantalla usa. Se calculan una sola vez.

    `en_transito` se resta de la necesidad a propósito: sin eso el panel
    recomienda comprar 60 unidades que ya vienen en el barco, y comprar dos
    veces lo mismo es el error caro de un MRP mal hecho.
    """
    inv, oc, eje = inventario(), ordenes_compra(), ejecuciones()
    rota = inv[inv["demanda_dia"] > 0]
    transito = oc[oc["estado"] != "Recibida"].groupby("sku")["unidades"].sum()
    falt = rota.copy()
    falt["en_transito"] = falt["sku"].map(transito).fillna(0).astype(int)
    falt["faltante_neto"] = (falt["faltante_pico"] - falt["en_transito"]).clip(lower=0)
    falt["valor_neto"] = falt["faltante_neto"] * falt["costo_unit"]
    ok = (eje["resultado"] == "ok")
    return {
        "valor_inventario": float(inv["valor_inventario"].sum()),
        "referencias_activas": int(rota["sku"].nunique()),
        "urge_semana": int((rota["urgencia"] == "Pedir esta semana").sum()),
        "ventana_cerrada": int((rota["urgencia"] == "Ventana cerrada").sum()),
        "compra_diciembre": float(falt["valor_neto"].sum()),
        "en_transito_valor": float(oc.loc[oc["estado"] != "Recibida", "valor"].sum()),
        "ordenes_atrasadas": int((oc["dias_atraso"] > 0).sum()),
        "corridas_mes": int(len(eje)),
        "acierto_pct": float(ok.mean() * 100),
        "horas_mes": float(eje["minutos_ahorrados"].sum() / 60),
        "para_revisar": int((~ok).sum()),
        "faltantes": falt,
    }
