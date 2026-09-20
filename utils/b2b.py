"""Carga de la capa B2B: cuentas, ventas por cuenta, entregas, equipo y decisiones.

Archivo nuevo a propósito. El 19-sep se agregaron funciones al final de
`datos.py` y Streamlit Cloud siguió sirviendo la versión vieja en memoria
durante horas: re-ejecuta `app.py` en cada rerun pero no reimporta lo que ya
está en `sys.modules`. Al agregar capacidades a un panel desplegado conviene
que entren por un módulo que nunca se había importado.

Los datos los produce `data/gen_b2b.py`, derivados del catálogo y calibrados
para cuadrar con lo que `finanzas.csv` ya declara como B2B. La regla es la
misma de siempre: nada se genera en paralelo a algo que ya existe.
"""
import numpy as np
import pandas as pd
import streamlit as st

from utils.datos import _leer, CORTE

MES_ACTUAL = "2026-08"
ULTIMOS_12 = "2025-09"
# El trimestre es la ventana para juzgar una cuenta: un mes malo es ruido
# —un bar cierra por remodelación, un club tiene un puente—, tres meses malos
# son una condición comercial que hay que cambiar.
TRIMESTRE = "2026-06"

COLOR_CANAL = {
    "Restaurantes": "#0E113A", "Bares": "#CE6264", "Discotecas": "#7D5BA6",
    "Clubes sociales": "#2B7A9B", "Empresas": "#B5762F",
}


@st.cache_data
def cuentas() -> pd.DataFrame:
    df = _leer("cuentas.csv", keep_default_na=False)
    df["alta"] = pd.to_datetime(df["alta"])
    for c in ("cupo_credito", "plazo_pago"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    for c in ("descuento_pct", "frec_visita_mes", "escala"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


@st.cache_data(show_spinner="Cargando ventas por cuenta…")
def ventas() -> pd.DataFrame:
    df = _leer("ventas_cuenta_mes.csv", keep_default_na=False)
    for c in ("bruto", "descuento", "devoluciones", "neto", "costo",
              "unidades", "entregas", "margen"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df


@st.cache_data
def entregas() -> pd.DataFrame:
    df = _leer("entregas.csv", keep_default_na=False)
    for c in ("entregas", "unidades", "costo_entrega_u", "costo_logistica",
              "margen", "margen_servido"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df


@st.cache_data
def vendedores() -> pd.DataFrame:
    return _leer("vendedores.csv", keep_default_na=False)


@st.cache_data
def hilos() -> pd.DataFrame:
    df = _leer("hilos.csv", keep_default_na=False)
    df["abierto"] = pd.to_datetime(df["abierto"])
    return df


@st.cache_data
def decisiones() -> pd.DataFrame:
    return _leer("decisiones.csv", keep_default_na=False)


@st.cache_data
def rentabilidad() -> pd.DataFrame:
    """La foto que ninguna de las dos fuentes da por separado.

    Un distribuidor sabe cuánto le VENDE a cada bar —eso lo da el ERP— y sabe
    cuánto le cuesta repartir —eso lo da el operador logístico—. Lo que nadie
    junta es cuánto le DEJA cada cuenta después de servirla, y ahí es donde
    aparecen las cuentas que venden bien y cuestan plata.

    Se calcula sobre el ÚLTIMO TRIMESTRE, no sobre doce meses: las condiciones
    comerciales de hace un año ya no son las de hoy, y decidir con un promedio
    largo protege a la cuenta que se deterioró hace tres meses.
    """
    v, e, c = ventas(), entregas(), cuentas()
    vt = v[v["mes"] >= TRIMESTRE]
    et = e[e["mes"] >= TRIMESTRE]

    g = vt.groupby("cuenta_id").agg(
        bruto=("bruto", "sum"), descuento=("descuento", "sum"),
        devoluciones=("devoluciones", "sum"), neto=("neto", "sum"),
        costo=("costo", "sum"), margen=("margen", "sum"),
        unidades=("unidades", "sum"), meses=("mes", "nunique")).reset_index()
    log = et.groupby("cuenta_id").agg(
        entregas=("entregas", "sum"), logistica=("costo_logistica", "sum")).reset_index()
    g = g.merge(log, on="cuenta_id", how="left").merge(
        c[["cuenta_id", "nombre", "canal", "ciudad", "zona", "vendedor",
           "descuento_pct", "plazo_pago", "cupo_credito", "alta"]],
        on="cuenta_id", how="left")
    g["logistica"] = g["logistica"].fillna(0)
    g["entregas"] = g["entregas"].fillna(0)
    g["servido"] = g["margen"] - g["logistica"]
    g["margen_pct"] = np.where(g["neto"] > 0, g["margen"] / g["neto"] * 100, 0)
    g["servido_pct"] = np.where(g["neto"] > 0, g["servido"] / g["neto"] * 100, 0)
    g["ticket_entrega"] = np.where(g["entregas"] > 0, g["neto"] / g["entregas"], 0)
    g["costo_por_entrega"] = np.where(g["entregas"] > 0, g["logistica"] / g["entregas"], 0)

    # El capital que la cuenta tiene inmovilizado: lo que factura al mes por el
    # plazo que le dimos. Un club social a 45 días amarra la mitad de un
    # trimestre de su propia venta.
    g["expuesto"] = g["neto"] / g["meses"].clip(lower=1) * (g["plazo_pago"] / 30)
    g["sobre_cupo"] = g["expuesto"] - g["cupo_credito"]

    g["salud"] = np.select(
        [g["servido_pct"] < 0, g["servido_pct"] < 8, g["servido_pct"] < 18],
        ["Cuesta plata", "Apenas paga", "Aceptable"], default="Buena")
    return g.sort_values("servido", ascending=False)


@st.cache_data
def resumen_b2b() -> dict:
    v, e, r = ventas(), entregas(), rentabilidad()
    u12 = v[v["mes"] >= ULTIMOS_12]
    mes = v[v["mes"] == MES_ACTUAL]
    prev = v[v["mes"] == "2026-07"]
    e12 = e[e["mes"] >= ULTIMOS_12]
    rojas = r[r["servido"] < 0]
    return {
        "neto_12m": float(u12["neto"].sum()),
        "margen_12m_pct": float(u12["margen"].sum() / max(u12["neto"].sum(), 1) * 100),
        "servido_12m_pct": float(e12["margen_servido"].sum() / max(u12["neto"].sum(), 1) * 100),
        "neto_mes": float(mes["neto"].sum()),
        "var_mes": float(mes["neto"].sum() / max(prev["neto"].sum(), 1) - 1) * 100,
        "cuentas_activas": int(mes["cuenta_id"].nunique()),
        "cuentas_total": int(len(cuentas())),
        "cuentas_rojas": int(len(rojas)),
        "plata_en_rojo": float(rojas["servido"].sum()),
        "logistica_12m": float(e12["costo_logistica"].sum()),
        "medellin_pct": float(u12.loc[u12["ciudad"] == "Medellín", "neto"].sum() /
                              max(u12["neto"].sum(), 1) * 100),
        "expuesto": float(r["expuesto"].sum()),
        "sobre_cupo": float(r.loc[r["sobre_cupo"] > 0, "sobre_cupo"].sum()),
    }
