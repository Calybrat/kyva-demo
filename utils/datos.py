"""
Carga de datos compartida e indicadores del panel de KYVA.

DOS RAZONES POR LAS QUE ESTE ARCHIVO EXISTE
───────────────────────────────────────────
1. **Memoria.** `st.cache_data` cachea por función: cada tabla se carga UNA vez.
2. **Que ningún módulo contradiga a otro.** Todo indicador que aparece en más
   de una pantalla —ingresos, crecimiento, margen por canal, recompra,
   activación Elite, espera de entrega— se calcula AQUÍ, y los módulos solo lo
   leen. El agente y los reportes usan estas mismas funciones.

No se convierte texto a `category`: al agrupar, pandas devolvería también las
combinaciones que no existen (un canal vendiendo $0 antes de existir).
"""
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

_DATA = Path(__file__).parent.parent / "data"

CORTE = pd.Timestamp("2026-08-31 23:59")
CORTE_TXT = "31 de agosto de 2026"
MES_ACTUAL = "2026-08"
CANALES = ["The Store", "The Lounge", "Corporativo", "Distribución"]
COL_CANAL = {"The Store": "ingreso_store", "The Lounge": "ingreso_lounge",
             "Corporativo": "ingreso_corporativo", "Distribución": "ingreso_distribucion"}
# La última semana completa y la misma semana del año anterior
SEMANA = (pd.Timestamp("2026-08-24"), pd.Timestamp("2026-08-30 23:59"))
SEMANA_ANT = (pd.Timestamp("2025-08-25"), pd.Timestamp("2025-08-31 23:59"))


def _leer(nombre: str, **kw) -> pd.DataFrame:
    kw.setdefault("low_memory", False)
    for c in (_DATA / nombre, _DATA / f"{nombre}.gz"):
        if c.exists():
            return pd.read_csv(c, **kw)
    raise FileNotFoundError(f"No se encontró {nombre} en {_DATA}")


# ── Tablas ───────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Cargando pedidos…")
def pedidos() -> pd.DataFrame:
    df = _leer("pedidos.csv", keep_default_na=False)
    df["fecha"] = pd.to_datetime(df["fecha"])
    df["fecha_entrega"] = pd.to_datetime(df["fecha_entrega"])
    df["en_promesa"] = df["en_promesa"].astype(str) == "True"
    df["lleva_exclusiva"] = df["lleva_exclusiva"].astype(str) == "True"
    for c in ["dia_semana", "hora", "n_compra", "items", "unidades"]:
        df[c] = pd.to_numeric(df[c], downcast="integer")
    return df


@st.cache_data
def entregados() -> pd.DataFrame:
    p = pedidos()
    return p[p["estado"] == "Entregado"]


@st.cache_data
def clientes() -> pd.DataFrame:
    df = _leer("clientes.csv", keep_default_na=False)
    for c in ["primer_pedido", "ultimo_pedido", "fecha_alta"]:
        df[c] = pd.to_datetime(df[c])
    return df


@st.cache_data
def catalogo() -> pd.DataFrame:
    df = _leer("catalogo.csv", keep_default_na=False)
    for c in ["exclusiva", "precio_observado"]:
        df[c] = df[c].astype(str) == "True"
    return df


@st.cache_data
def ventas_sku_mes() -> pd.DataFrame:
    return _leer("ventas_sku_mes.csv")


@st.cache_data
def miembros() -> pd.DataFrame:
    df = _leer("miembros.csv", keep_default_na=False)
    df["fecha_alta"] = pd.to_datetime(df["fecha_alta"])
    df["compro"] = df["compro"].astype(str) == "True"
    return df


@st.cache_data
def mi_circulo() -> pd.DataFrame:
    return _leer("mi_circulo.csv")


@st.cache_data
def corporativo() -> pd.DataFrame:
    df = _leer("corporativo.csv", keep_default_na=False)
    df["fecha_cotizacion"] = pd.to_datetime(df["fecha_cotizacion"])
    df["fecha_entrega"] = pd.to_datetime(df["fecha_entrega"])
    df["probabilidad"] = pd.to_numeric(df["probabilidad"], errors="coerce")
    return df


@st.cache_data
def cuentas_distribucion() -> pd.DataFrame:
    return _leer("cuentas_distribucion.csv", keep_default_na=False)


@st.cache_data
def distribucion() -> pd.DataFrame:
    return _leer("distribucion.csv")


@st.cache_data
def inventario_exclusivas() -> pd.DataFrame:
    return _leer("inventario_exclusivas.csv")


@st.cache_data
def mercadeo() -> pd.DataFrame:
    return _leer("mercadeo.csv")


@st.cache_data
def finanzas() -> pd.DataFrame:
    return _leer("finanzas.csv")


@st.cache_data
def precios_competencia() -> pd.DataFrame:
    df = _leer("precios_competencia.csv")
    df["por_litro"] = df["ml_kyva"] != df["ml_competidor"]
    k_c = df["kyva_classic"] / df["ml_kyva"] * 1000
    k_e = df["kyva_elite"] / df["ml_kyva"] * 1000
    comp = df["precio_competidor"] / df["ml_competidor"] * 1000
    df["dif_classic_pct"] = (k_c / comp - 1) * 100
    df["dif_elite_pct"] = (k_e / comp - 1) * 100
    return df


@st.cache_data
def meses() -> list:
    return finanzas()["mes"].tolist()


def ultimos(n: int = 12) -> list:
    return meses()[-n:]


# ── Indicadores compartidos ──────────────────────────────────────────────────
@st.cache_data
def ingresos_canal_mes() -> pd.DataFrame:
    """mes × canal, la ÚNICA serie de ingresos del panel (sale de finanzas)."""
    f = finanzas()
    largo = f.melt(id_vars="mes", value_vars=list(COL_CANAL.values()),
                   var_name="col", value_name="ingreso")
    inv = {v: k for k, v in COL_CANAL.items()}
    largo["canal"] = largo["col"].map(inv)
    return largo[["mes", "canal", "ingreso"]]


@st.cache_data
def anual() -> pd.DataFrame:
    f = finanzas().copy()
    f["anio"] = f["mes"].str[:4]
    a = f.groupby("anio")[["ingresos", "margen_bruto", "utilidad_operacional"] +
                          list(COL_CANAL.values())].sum()
    a["crecimiento_pct"] = a["ingresos"].pct_change() * 100
    a["margen_bruto_pct"] = a["margen_bruto"] / a["ingresos"] * 100
    a["margen_operacional_pct"] = a["utilidad_operacional"] / a["ingresos"] * 100
    a["meses"] = f.groupby("anio").size()
    return a


@st.cache_data
def cabecera() -> dict:
    """Las cifras de cabecera del panel. Un solo lugar, un solo cálculo."""
    f = finanzas()
    u12, a12 = f.tail(12), f.iloc[-24:-12]
    ytd = f[f["mes"].between("2026-01", MES_ACTUAL)]
    ytd_a = f[f["mes"].between("2025-01", "2025-08")]
    ok = entregados()
    ok12 = ok[ok["fecha"] > CORTE - pd.Timedelta(days=365)]
    cli = clientes()
    return {
        "ingresos12": float(u12["ingresos"].sum()),
        "crec12": float((u12["ingresos"].sum() / a12["ingresos"].sum() - 1) * 100),
        "ingresos_ytd": float(ytd["ingresos"].sum()),
        "crec_ytd": float((ytd["ingresos"].sum() / ytd_a["ingresos"].sum() - 1) * 100),
        "margen_bruto12": float(u12["margen_bruto"].sum() / u12["ingresos"].sum() * 100),
        "utilidad12": float(u12["utilidad_operacional"].sum()),
        "margen_op12": float(u12["utilidad_operacional"].sum() / u12["ingresos"].sum() * 100),
        "margen_op_2025": float(anual().loc["2025", "margen_operacional_pct"]),
        "crec_2025": float(anual().loc["2025", "crecimiento_pct"]),
        "crec_2024": float(anual().loc["2024", "crecimiento_pct"]),
        "pedidos12": int(len(ok12)),
        "ticket12": float(ok12["valor_bruto"].mean()),
        "clientes_activos": int((cli["estado"] == "Activo").sum()),
        "clientes12": int(ok12["cliente_id"].nunique()),
        "caja": float(f["caja"].iloc[-1]),
        "deuda": float(f["deuda"].iloc[-1]),
        "inventario": float(f["inventario"].iloc[-1]),
        "personas": int(f["personas"].iloc[-1]),
        "mes": MES_ACTUAL,
    }


@st.cache_data
def semana() -> dict:
    """La semana pasada (lun 24 – dom 30 ago) contra la misma semana de 2025."""
    p = pedidos()

    def _res(a, b):
        s = p[(p["fecha"] >= a) & (p["fecha"] <= b)]
        ok = s[s["estado"] == "Entregado"]
        return {"ingreso": float(ok["ingreso_neto"].sum()), "pedidos": int(len(ok)),
                "ticket": float(ok["valor_bruto"].mean()) if len(ok) else 0.0,
                "cancelados": int((s["estado"] == "Cancelado").sum()),
                "promesa": float(s["en_promesa"].mean() * 100) if len(s) else 0.0,
                "nuevos": int((ok["n_compra"] == 1).sum()),
                "espera_finde": float((s["ventana"] == "Espera fin de semana o festivo").mean() * 100)}
    return {"actual": _res(*SEMANA), "anterior": _res(*SEMANA_ANT)}


@st.cache_data
def margen_canal(n_meses: int = 12) -> pd.DataFrame:
    """Ingreso, margen bruto y contribución por canal en los últimos n meses.

    Contribución = lo que queda después de la mercancía y de los costos que
    genera cada venta (envío, pasarela, empaque, empaque personalizado).
    """
    ms = ultimos(n_meses)
    ok = entregados()
    ok = ok[ok["mes"].isin(ms)]
    filas = []
    for canal in ("The Store", "The Lounge"):
        s = ok[ok["canal"] == canal]
        filas.append(dict(canal=canal, ingreso=s["ingreso_neto"].sum(),
                          costo=s["costo_mercancia"].sum(),
                          directos=(s["costo_envio"] + s["comision_pasarela"] + s["empaque"]).sum()
                          - (s["envio_cobrado"] / 1.19).sum(),
                          descuento=s["descuento"].sum(), pedidos=len(s)))
    co = corporativo()
    co = co[(co["estado"] == "Ganada") & co["fecha_entrega"].dt.strftime("%Y-%m").isin(ms)]
    filas.append(dict(canal="Corporativo", ingreso=co["ingreso_neto"].sum(),
                      costo=co["costo_mercancia"].sum(), directos=co["empaque_personalizado"].sum(),
                      descuento=0.0, pedidos=len(co)))
    di = distribucion()
    di = di[di["mes"].isin(ms)]
    filas.append(dict(canal="Distribución", ingreso=di["ingreso_neto"].sum(),
                      costo=di["costo_mercancia"].sum(), directos=di["ingreso_neto"].sum() * .02,
                      descuento=0.0, pedidos=len(di)))
    df = pd.DataFrame(filas)
    df["margen_bruto"] = df["ingreso"] - df["costo"]
    df["margen_bruto_pct"] = df["margen_bruto"] / df["ingreso"] * 100
    df["contribucion"] = df["margen_bruto"] - df["directos"]
    df["contribucion_pct"] = df["contribucion"] / df["ingreso"] * 100
    df["peso_pct"] = df["ingreso"] / df["ingreso"].sum() * 100
    return df


@st.cache_data
def recompra_origen() -> pd.DataFrame:
    """Por origen del cliente: cuántos vuelven, cuánto dejan en un año y cuánto
    cuesta traerlos (solo los orígenes con pauta tienen costo directo)."""
    cli = clientes()
    ok = entregados()
    base = cli[cli["primer_pedido"] <= CORTE - pd.Timedelta(days=180)]
    p = ok.merge(base[["cliente_id", "primer_pedido"]], on="cliente_id")
    d = (p["fecha"] - p["primer_pedido"]).dt.days
    vuelve = p[(d > 0) & (d <= 180)].groupby("cliente_id").size()
    base = base.assign(volvio=base["cliente_id"].isin(vuelve.index))
    b12 = cli[cli["primer_pedido"] <= CORTE - pd.Timedelta(days=365)]
    p12 = ok.merge(b12[["cliente_id", "primer_pedido"]], on="cliente_id")
    p12 = p12[(p12["fecha"] - p12["primer_pedido"]).dt.days <= 365]
    val = p12.groupby("cliente_id")["contribucion"].sum()
    b12 = b12.assign(contrib_12m=b12["cliente_id"].map(val).fillna(0))
    r = base.groupby("origen").agg(clientes=("cliente_id", "size"), recompra=("volvio", "mean"))
    r["recompra_pct"] = r["recompra"] * 100
    r["contribucion_12m"] = b12.groupby("origen")["contrib_12m"].mean()
    # CAC: pauta de los últimos 12 meses sobre clientes nuevos de ese origen
    mk = mercadeo()
    mk12 = mk[mk["mes"].isin(ultimos(12))].groupby("canal")["inversion"].sum()
    nuevos12 = cli[cli["primer_pedido"] > CORTE - pd.Timedelta(days=365)].groupby("origen").size()
    r["nuevos_12m"] = nuevos12
    r["inversion_12m"] = [mk12.get(o, np.nan) for o in r.index]
    r["cac"] = r["inversion_12m"] / r["nuevos_12m"]
    return r.drop(columns="recompra").sort_values("recompra_pct", ascending=False)


@st.cache_data
def elite() -> dict:
    """Membresía Elite: cuántos la tienen, cuántos la usan y cuánto cuesta."""
    m = miembros()
    ok = entregados()
    l12 = ok[(ok["canal"] == "The Lounge") & ok["mes"].isin(ultimos(12))]
    s12 = ok[(ok["canal"] == "The Store") & ok["mes"].isin(ultimos(12))]
    cli = clientes()
    el = cli[cli["tipo"] == "Elite"]
    return {
        "miembros": int(len(m)),
        "compraron": int(m["compro"].sum()),
        "activacion_pct": float(m["compro"].mean() * 100),
        "nunca_compraron": int((~m["compro"]).sum()),
        "activos": int((el["estado"] == "Activo").sum()),
        "dormidos": int((el["estado"] == "Dormido").sum()),
        "ingreso12": float(l12["ingreso_neto"].sum()),
        "descuento12": float(l12["descuento"].sum()),
        "contribucion12": float(l12["contribucion"].sum()),
        "margen_bruto_pct": float(l12["margen_bruto"].sum() / l12["ingreso_neto"].sum() * 100),
        "margen_bruto_store_pct": float(s12["margen_bruto"].sum() / s12["ingreso_neto"].sum() * 100),
        "pedidos_por_cliente": float(l12.groupby("cliente_id").size().mean()),
        "pedidos_por_cliente_store": float(s12.groupby("cliente_id").size().mean()),
        "ticket": float(l12["valor_bruto"].mean()),
        "ticket_store": float(s12["valor_bruto"].mean()),
    }


@st.cache_data
def aliados() -> pd.DataFrame:
    m = miembros()
    m = m[m["origen"] == "Alianza"]
    ok = entregados()
    l12 = ok[(ok["canal"] == "The Lounge") & ok["mes"].isin(ultimos(12))]
    cli = clientes()[["cliente_id", "aliado"]]
    l12 = l12.merge(cli, on="cliente_id")
    g = m.groupby("aliado").agg(miembros=("miembro_id", "size"), compraron=("compro", "sum"))
    g["activacion_pct"] = g["compraron"] / g["miembros"] * 100
    v = l12.groupby("aliado").agg(ingreso12=("ingreso_neto", "sum"), descuento12=("descuento", "sum"),
                                  contribucion12=("contribucion", "sum"), pedidos12=("pedido_id", "size"))
    g = g.join(v).fillna(0)
    g["contrib_por_miembro"] = g["contribucion12"] / g["miembros"]
    return g.sort_values("ingreso12", ascending=False)


@st.cache_data
def entregas() -> dict:
    p = pedidos()
    p12 = p[p["mes"].isin(ultimos(12))]
    v = p12.groupby("ventana").agg(pedidos=("pedido_id", "size"),
                                   horas=("horas_espera", "median"),
                                   cancelacion=("estado", lambda s: (s == "Cancelado").mean() * 100),
                                   promesa=("en_promesa", "mean"))
    v["peso_pct"] = v["pedidos"] / v["pedidos"].sum() * 100
    canc = p12[p12["estado"] == "Cancelado"]
    base_cancel = v.loc["Pide AM · recibe PM", "cancelacion"] if "Pide AM · recibe PM" in v.index else 1.3
    finde = p12[p12["ventana"] == "Espera fin de semana o festivo"]
    exceso = (v.loc["Espera fin de semana o festivo", "cancelacion"] - base_cancel) / 100
    return {
        "ventanas": v,
        "pedidos12": int(len(p12)),
        "cancelados12": int(len(canc)),
        "valor_cancelado12": float(canc["valor_bruto"].sum()),
        "cancel_pct": float(len(canc) / len(p12) * 100),
        "promesa_pct": float(p12["en_promesa"].mean() * 100),
        "finde_pct": float(len(finde) / len(p12) * 100),
        "valor_perdido_finde": float(len(finde) * exceso * finde["valor_bruto"].mean()),
        "horas_mediana": float(p12["horas_espera"].median()),
    }


@st.cache_data
def surtido() -> pd.DataFrame:
    """Cada referencia: venta de 12 meses, margen, stock y cobertura."""
    cat = catalogo()
    v = ventas_sku_mes()
    v12 = v[v["mes"].isin(ultimos(12))].groupby("sku")[["unidades", "ingreso_neto", "costo"]].sum()
    df = cat.set_index("sku").join(v12).fillna({"unidades": 0, "ingreso_neto": 0, "costo": 0})
    df["margen"] = df["ingreso_neto"] - df["costo"]
    df["margen_pct"] = np.where(df["ingreso_neto"] > 0, df["margen"] / df["ingreso_neto"] * 100, np.nan)
    df["valor_stock"] = df["stock_u"] * df["costo_unit"]
    df["dias_cobertura"] = np.where(df["unidades_90d"] > 0, df["stock_u"] / (df["unidades_90d"] / 90), np.inf)
    iva = np.where(df["categoria"].isin(["Cerveza", "Mixers y aguas", "Accesorios gourmet"]), .19, .05)
    df["margen_elite_pct"] = (1 - df["costo_unit"] / (df["precio_elite"] / (1 + iva))) * 100
    df["margen_classic_pct"] = (1 - df["costo_unit"] / (df["precio_classic"] / (1 + iva))) * 100
    return df.reset_index()


@st.cache_data
def pipeline_diciembre() -> dict:
    co = corporativo()
    dic25 = co[(co["fecha_entrega"].dt.strftime("%Y-%m").isin(["2025-11", "2025-12"]))]
    ab = co[co["estado"] == "Abierta"]
    ab_fin = ab[ab["fecha_entrega"].dt.month.isin([11, 12])]
    cot_a_la_fecha_25 = dic25[dic25["fecha_cotizacion"] <= pd.Timestamp("2025-08-31")]
    return {
        "ganado_nov_dic_2025": float(dic25.loc[dic25["estado"] == "Ganada", "ingreso_neto"].sum()),
        "cotizado_nov_dic_2025": float(dic25["valor_cotizado"].sum() / 1.05),
        "tasa_cierre_2025": float((dic25["estado"] == "Ganada").mean() * 100),
        "abierto_nov_dic_2026": float(ab_fin["valor_cotizado"].sum() / 1.05),
        "ponderado_nov_dic_2026": float((ab_fin["valor_cotizado"] / 1.05 * ab_fin["probabilidad"]).sum()),
        "n_abiertas": int(len(ab_fin)),
        "cotizado_a_31ago_2025": float(cot_a_la_fecha_25["valor_cotizado"].sum() / 1.05),
    }


# ── Operación: inventario, compras, automatizaciones y alertas ──────────────
# Todo esto lo produce `data/gen_operacion.py`, que lo DERIVA del catálogo y de
# las líneas de pedido. No es una fuente paralela: si se generara aparte, la
# pantalla de surtido diría 108 botellas de Chivas y la de reposición 74.

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
