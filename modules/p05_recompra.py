"""Recompra y cohortes: ¿el cliente que llega vuelve?

En licores la primera compra casi nunca paga lo que costó traer al cliente. El
negocio está en la segunda, la tercera y el diciembre siguiente. Aquí se ve
quién vuelve, según por dónde llegó.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.formatters import *
from utils import datos


@st.cache_data
def _cohortes() -> pd.DataFrame:
    """% de cada cohorte trimestral que compra en cada trimestre posterior."""
    ok = datos.entregados()[["cliente_id", "fecha"]]
    cli = datos.clientes()[["cliente_id", "primer_pedido", "tipo"]]
    p = ok.merge(cli, on="cliente_id")
    p["coh"] = p["primer_pedido"].dt.to_period("Q")
    p["q"] = p["fecha"].dt.to_period("Q")
    p["k"] = (p["q"] - p["coh"]).apply(lambda x: x.n)
    base = p.groupby("coh")["cliente_id"].nunique()
    act = p.groupby(["coh", "k"])["cliente_id"].nunique().unstack()
    ret = act.div(base, axis=0) * 100
    ret = ret[ret.index >= pd.Period("2024Q1", "Q")]
    ret.index = [f"{x.year} T{x.quarter}" for x in ret.index]
    ret.insert(0, "Clientes", base[base.index >= pd.Period("2024Q1", "Q")].values)
    return ret


def render():
    st.markdown(HEADER_CSS, unsafe_allow_html=True)
    st.markdown(encabezado(
        "Recompra y cohortes",
        "Quién vuelve a comprar, según por dónde llegó",
        "¿Quién compra y vuelve?"), unsafe_allow_html=True)

    r = datos.recompra_origen()
    cli = datos.clientes()
    c = datos.cabecera()
    base180 = cli[cli["primer_pedido"] <= datos.CORTE - pd.Timedelta(days=180)]
    una = (cli["pedidos"] == 1).mean() * 100
    dorm = (cli["estado"] == "Dormido").sum()

    k = st.columns(4, gap="small")
    rec_total = (r["recompra_pct"] * r["clientes"]).sum() / r["clientes"].sum()
    k[0].markdown(kpi("Vuelven en 6 meses", pct(rec_total, 0), icon="🔁",
                      ayuda="Clientes que hicieron una segunda compra en los 180 días "
                            "siguientes a la primera.",
                      referencia="E-commerce de licores: 30–40%"), unsafe_allow_html=True)
    k[1].markdown(kpi("Compraron una sola vez", pct(una, 0), f"{num((cli['pedidos']==1).sum())} clientes",
                      False, "1️⃣", "De todos los clientes que ha tenido KYVA."),
                  unsafe_allow_html=True)
    k[2].markdown(kpi("Clientes activos", num(c["clientes_activos"]),
                      f"{num(c['clientes12'])} compraron en 12 meses", True, "🟢",
                      "Compraron en los últimos 90 días."), unsafe_allow_html=True)
    k[3].markdown(kpi("Dormidos con historial", num(dorm), "Más de 180 días sin comprar", False, "💤",
                      "La base más barata de reactivar: ya confiaron una vez."),
                  unsafe_allow_html=True)

    st.markdown(espacio(14), unsafe_allow_html=True)
    g1, g2 = st.columns([1, 1.25], gap="medium")
    with g1:
        rr = r.reset_index()
        fig = go.Figure(go.Bar(
            y=rr["origen"], x=rr["recompra_pct"], orientation="h",
            marker_color=[ACENTO if o in ("Instagram y Meta", "Google y SEO") else PRIMARIO
                          for o in rr["origen"]],
            text=[pct(v, 0) for v in rr["recompra_pct"]], textposition="outside"))
        fig.update_layout(yaxis=dict(autorange="reversed"), xaxis=dict(ticksuffix="%"),
                          hovermode="y unified")
        st.plotly_chart(light(fig, 360, "Vuelven en 6 meses, por origen"), width="stretch", theme=None, config=PLOTLY_CONFIG)
    with g2:
        coh = _cohortes()
        z = coh.drop(columns="Clientes")
        z = z[[x for x in z.columns if 1 <= x <= 6]]
        fig = go.Figure(go.Heatmap(
            z=z.values, x=[f"+{x} trim." for x in z.columns], y=z.index,
            colorscale=[[0, "#FFFFFF"], [.5, CLARO], [1, PRIMARIO]],
            text=[[pct(v, 0) if not np.isnan(v) else "" for v in fila] for fila in z.values],
            texttemplate="%{text}", hovertemplate="%{y} · %{x}: %{z:.1f}%<extra></extra>",
            showscale=False))
        fig.update_layout(yaxis=dict(autorange="reversed"), hovermode="closest")
        st.plotly_chart(light(fig, 360, "Cohortes: % que compra en cada trimestre siguiente"),
                        width="stretch", theme=None, config=PLOTLY_CONFIG)

    # ── Tabla de origen con economía ─────────────────────────────────────────
    t = r.reset_index()
    tabla = pd.DataFrame({
        "Origen": t["origen"],
        "Clientes (base)": [num(v) for v in t["clientes"]],
        "Vuelven en 6 m": [pct(v, 0) for v in t["recompra_pct"]],
        "Le dejan a KYVA en su primer año": [cop(v) for v in t["contribucion_12m"]],
        "Nuevos en 12 m": [num(v) if not np.isnan(v) else "—" for v in t["nuevos_12m"]],
        "Costo de traer uno": [cop(v) if not np.isnan(v) else "sin pauta" for v in t["cac"]],
    })
    st.dataframe(tabla, hide_index=True, width="stretch")

    pago = t[t["cac"].notna()]
    ref = t.set_index("origen")
    mc = ref.loc["Mi Círculo (referido)"] if "Mi Círculo (referido)" in ref.index else None
    lineas = "".join(
        f"<br>· <b>{o}</b>: cuesta {cop(x['cac'])} traer un cliente y deja "
        f"{cop(x['contribucion_12m'])} en su primer año — "
        f"{'se paga' if x['contribucion_12m'] >= x['cac'] else 'no alcanza a pagarse'}."
        for o, x in pago.set_index("origen").iterrows())
    st.markdown(panel(
        "Lo que dice",
        f"La pauta trae volumen, pero el cliente que llega por pauta es el que menos "
        f"vuelve.{lineas}<br><br>"
        + (f"El cliente referido por <b>Mi Círculo</b> vuelve un "
           f"<b>{pct(mc['recompra_pct'], 0)}</b> de las veces y su costo es un cupón. "
           if mc is not None else "") +
        f"<b>La decisión:</b> mover presupuesto de pauta a dos cosas que ya existen — el "
        f"cupón de Mi Círculo y una campaña de reactivación a los {num(dorm)} dormidos, "
        f"empezando por los que compraron en diciembre y no volvieron.",
        "🔁", "naranja"), unsafe_allow_html=True)
    st.caption("Cohorte = trimestre de la primera compra. Datos simulados con fines de demostración.")
