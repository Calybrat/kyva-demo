"""Carga de la capa de gerencia: cartera real, marcas, quiebres, lotes, PDV,
presupuesto y compromisos.

Todo esto existe porque una revisión adversaria hecha por un COO de
distribuidora encontró que el panel medía bien lo que se vendió y no medía
nada de lo que cuesta plata: la cartera real, el compromiso con las marcas, lo
que no se alcanzó a despachar, lo que se vence en bodega y lo que pasa dentro
del bar.
"""
import numpy as np
import pandas as pd
import streamlit as st

from utils.datos import _leer, CORTE

TRAMOS = ["Corriente", "1 a 30", "31 a 60", "61 a 90", "Más de 90"]
# Probabilidad de cobro por tramo. Cambia la conversación: no «me deben 40»
# sino «de esos 40 espero cobrar 31».
COBRO = {"Corriente": 0.99, "1 a 30": 0.95, "31 a 60": 0.82,
         "61 a 90": 0.58, "Más de 90": 0.28}
COLOR_TRAMO = {"Corriente": "#2f7a48", "1 a 30": "#7FA65C", "31 a 60": "#B5762F",
               "61 a 90": "#CE6264", "Más de 90": "#8B1E1E"}


@st.cache_data(show_spinner="Cargando cartera…")
def facturas() -> pd.DataFrame:
    df = _leer("facturas.csv", keep_default_na=False)
    for c in ("emitida", "vence"):
        df[c] = pd.to_datetime(df[c])
    df["pagada"] = df["pagada"].astype(str) == "True"
    for c in ("valor", "saldo", "dias_vencida", "dias_atraso_real", "plazo"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    df["mes"] = df["emitida"].dt.strftime("%Y-%m")
    df["esperado"] = df["saldo"] * df["tramo"].map(COBRO).fillna(0.9)
    return df


@st.cache_data
def marcas_mes() -> pd.DataFrame:
    df = _leer("marcas_mes.csv", keep_default_na=False)
    df["exclusiva"] = df["exclusiva"].astype(str) == "True"
    return df


@st.cache_data
def rebates() -> pd.DataFrame:
    df = _leer("rebates.csv", keep_default_na=False)
    df["exclusiva"] = df["exclusiva"].astype(str) == "True"
    for c in ("cuota", "unidades", "cumplimiento", "tasa_rebate", "compra",
              "rebate", "faltan_para_siguiente", "bonificadas", "costo_bonificacion",
              "siguiente_tramo"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df


@st.cache_data
def quiebres() -> pd.DataFrame:
    df = _leer("quiebres.csv", keep_default_na=False)
    for c in ("pedidas", "servidas", "faltantes", "valor_perdido"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df


@st.cache_data
def devoluciones() -> pd.DataFrame:
    df = _leer("devoluciones.csv", keep_default_na=False)
    for c in ("unidades", "valor"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df


@st.cache_data
def lotes() -> pd.DataFrame:
    df = _leer("lotes.csv", keep_default_na=False)
    df["vence"] = pd.to_datetime(df["vence"])
    for c in ("unidades", "costo_unit", "valor", "dias_para_vencer",
              "vendible", "en_riesgo_u", "en_riesgo", "demanda_dia"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df


@st.cache_data
def punto_venta() -> pd.DataFrame:
    df = _leer("punto_venta.csv", keep_default_na=False)
    for c in ("pvp_sugerido", "precio_carta", "sobreprecio_pct",
              "rotacion_mes", "visitada_hace_dias"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df


@st.cache_data
def presupuesto() -> pd.DataFrame:
    df = _leer("presupuesto.csv", keep_default_na=False)
    for c in ("presupuesto", "real", "cumplimiento", "brecha"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df


@st.cache_data
def compromisos_base() -> pd.DataFrame:
    df = _leer("compromisos.csv", keep_default_na=False)
    for c in ("creado", "vence"):
        df[c] = pd.to_datetime(df[c])
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0)
    return df


@st.cache_data
def v_entregas() -> int:
    """Total de entregas del periodo, que es el denominador del fill rate."""
    from utils.b2b import ventas
    v = ventas()
    return int(v.loc[v["mes"] >= "2026-03", "entregas"].sum())


@st.cache_data
def resumen_gerencia() -> dict:
    """Los seis números que el COO dijo que miraría el lunes a las 7."""
    f, r, q, l, c = facturas(), rebates(), quiebres(), lotes(), compromisos_base()
    ab = f[~f["pagada"]]
    venc = ab[ab["dias_vencida"] > 0]
    tri = r[r["trimestre"] == "2026-T3"]
    completos = r[r["trimestre"].isin(["2025-T4", "2026-T1", "2026-T2"])]

    # Lo que se dejó de ganar por quedarse corto de un tramo.
    #
    # No es «no alcanzó cuota»: es «alcanzó un tramo y se quedó a nada del
    # siguiente». Diageo cerró 2026-T2 en 97,5% —le faltaron 56 unidades— y esas
    # 56 unidades valían la diferencia entre el tramo de 1,5% y el de 4%. Ese es
    # el dinero que se pierde sin que nadie lo vea, porque nadie está mirando el
    # contador a quince días del cierre.
    cerca = completos[(completos["faltan_para_siguiente"] > 0) &
                      (completos["faltan_para_siguiente"] <
                       completos["cuota"] * 0.08) &
                      (completos["siguiente_tramo"] > 0)]
    perdido = float(((cerca["siguiente_tramo"] - cerca["tasa_rebate"]) *
                     cerca["compra"]).sum())

    q12 = q[q["mes"] >= "2026-03"]
    # El fill rate NO se puede calcular sobre la tabla de quiebres: ahí solo
    # están las líneas que fallaron, y dividir entre ellas da un 35% imposible.
    # El denominador son TODAS las líneas despachadas, que se estiman de las
    # entregas (una entrega a un bar lleva del orden de once referencias).
    lineas_totales = float(v_entregas() * 11)
    faltantes = float(q12["faltantes"].sum())
    pedidas_ok = lineas_totales + len(q12)
    return {
        "cartera": float(ab["saldo"].sum()),
        "vencida": float(venc["saldo"].sum()),
        "en_riesgo": float(ab["saldo"].sum() - ab["esperado"].sum()),
        "atraso_real": float(f.loc[f["pagada"], "dias_atraso_real"].mean()),
        "rebate_12m": float(completos["rebate"].sum()),
        "rebate_perdido": perdido,
        "marcas_bajo_cuota": int((tri["cumplimiento"] < 66).sum()),
        "bonificacion": float(marcas_mes().tail(72)["costo_bonificacion"].sum()),
        "venta_perdida": float(q12["valor_perdido"].sum()),
        "fill_rate": float((1 - len(q12) / max(pedidas_ok, 1)) * 100),
        "lineas_incompletas": int(len(q12)),
        "por_vencer": float(l.loc[l["estado"].isin(["Crítico", "Vencido"]), "en_riesgo"].sum()),
        "compromisos_vencidos": int((c["estado"] == "Vencido").sum()),
    }
