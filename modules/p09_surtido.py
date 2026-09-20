"""Surtido y rotación: qué se vende, qué deja plata y qué ocupa bodega.

KYVA dice tener «más de 300 referencias». Todas cuestan: capital, espacio,
fotos, fichas y el tiempo de alguien de compras. Aquí se ve cuáles lo pagan.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.formatters import *
from utils import datos


def render():
    st.markdown(HEADER_CSS, unsafe_allow_html=True)
    st.markdown(encabezado(
        "Surtido y rotación",
        "Las referencias que venden, las que dejan margen y las que no se mueven · 12 meses",
        "¿Qué vendemos y a qué precio?"), unsafe_allow_html=True)

    s = datos.surtido()
    cats = ["Todas"] + sorted(s["categoria"].unique().tolist())
    cat = st.selectbox("Categoría", cats, key="su_cat")
    if cat != "Todas":
        s = s[s["categoria"] == cat]

    orden = s.sort_values("ingreso_neto", ascending=False).reset_index(drop=True)
    acum = orden["ingreso_neto"].cumsum() / max(orden["ingreso_neto"].sum(), 1) * 100
    n80 = int((acum < 80).sum()) + 1
    quietas = s[s["unidades_90d"] == 0]
    elite_fino = s[(s["margen_elite_pct"] < 5) & (s["unidades"] > 0)]

    k = st.columns(4, gap="small")
    k[0].markdown(kpi("Referencias en catálogo", num(len(s)),
                      f"{num((s['unidades_90d'] > 0).sum())} vendieron en 90 días", True, "🍾",
                      "Todo lo que se puede comprar en kyva.co."), unsafe_allow_html=True)
    k[1].markdown(kpi("Hacen el 80% de la venta", num(n80),
                      f"{pct(n80/len(s)*100, 0)} del catálogo", True, "🎯",
                      "El resto del catálogo reparte el 20% restante."), unsafe_allow_html=True)
    k[2].markdown(kpi("Sin una venta en 90 días", num(len(quietas)),
                      f"{cop(quietas['valor_stock'].sum())} en bodega", False, "🧊",
                      "Capital quieto, a precio de costo."), unsafe_allow_html=True)
    k[3].markdown(kpi("Margen Elite menor al 5%", num(len(elite_fino)), "referencias con venta",
                      False, "⚠️", "Productos donde el precio de miembro casi no deja nada.",
                      "Por debajo de 5% no alcanza ni para el envío"), unsafe_allow_html=True)

    st.markdown(espacio(14), unsafe_allow_html=True)
    g1, g2 = st.columns([1.25, 1], gap="medium")
    with g1:
        fig = go.Figure()
        fig.add_bar(x=list(range(1, len(orden) + 1)), y=orden["ingreso_neto"], name="Venta 12 m",
                    marker_color=CLARO, hovertext=orden["nombre"],
                    hovertemplate="%{hovertext}<br>%{y:$,.0f}<extra></extra>")
        fig.add_scatter(x=list(range(1, len(orden) + 1)), y=acum, name="% acumulado", yaxis="y2",
                        line=dict(color=ACENTO, width=2.5))
        fig.update_layout(xaxis=dict(title="Referencias, de la que más vende a la que menos"),
                          yaxis2=dict(overlaying="y", side="right", ticksuffix="%",
                                      range=[0, 101], showgrid=False), hovermode="closest")
        st.plotly_chart(light(fig, 360, "La curva del surtido", moneda=True),
                        width="stretch", theme=None, config=PLOTLY_CONFIG)
    with g2:
        c = (datos.surtido().groupby("categoria")
             .agg(ingreso=("ingreso_neto", "sum"), margen=("margen", "sum"),
                  stock=("valor_stock", "sum")))
        c["margen_pct"] = c["margen"] / c["ingreso"] * 100
        c = c.sort_values("ingreso", ascending=True).tail(10)
        fig = go.Figure(go.Bar(y=c.index, x=c["margen_pct"], orientation="h",
                               marker_color=[ACENTO if v < 15 else PRIMARIO for v in c["margen_pct"]],
                               text=[pct(v) for v in c["margen_pct"]], textposition="outside"))
        fig.update_layout(xaxis=dict(ticksuffix="%"), hovermode="y unified")
        st.plotly_chart(light(fig, 360, "Margen bruto por categoría (las 10 que más venden)"),
                        width="stretch", theme=None, config=PLOTLY_CONFIG)

    tab1, tab2, tab3 = st.tabs(["Las que más venden", "Las que no se mueven",
                                "Precio Elite casi al costo"])
    cols = {"nombre": "Referencia", "categoria": "Categoría", "unidades": "Unidades 12 m",
            "ingreso_neto": "Venta 12 m", "margen_pct": "Margen", "stock_u": "Stock",
            "valor_stock": "Valor en bodega", "margen_elite_pct": "Margen precio Elite",
            "precio_classic": "Precio Classic", "precio_elite": "Precio Elite"}

    def _fmt(df, campos):
        out = df[campos].rename(columns=cols).copy()
        for c_ in out.columns:
            if c_ in ("Venta 12 m", "Valor en bodega", "Precio Classic", "Precio Elite"):
                out[c_] = out[c_].map(cop)
            elif c_ in ("Margen", "Margen precio Elite"):
                out[c_] = out[c_].map(lambda v: pct(v) if pd.notna(v) else "—")
            elif c_ in ("Unidades 12 m", "Stock"):
                out[c_] = out[c_].map(num)
        return out

    with tab1:
        st.dataframe(_fmt(orden.head(20), ["nombre", "categoria", "unidades", "ingreso_neto",
                                           "margen_pct", "stock_u"]), hide_index=True, width="stretch")
    with tab2:
        q = quietas.sort_values("valor_stock", ascending=False)
        st.dataframe(_fmt(q.head(25), ["nombre", "categoria", "stock_u", "valor_stock",
                                       "precio_classic"]), hide_index=True, width="stretch")
    with tab3:
        e = elite_fino.sort_values("ingreso_neto", ascending=False)
        st.dataframe(_fmt(e.head(25), ["nombre", "categoria", "precio_classic", "precio_elite",
                                       "margen_elite_pct", "unidades"]), hide_index=True, width="stretch")

    st.markdown(panel(
        "Qué significa",
        f"<b>{num(n80)} referencias</b> hacen el 80% de la venta. Del otro lado, "
        f"<b>{num(len(quietas))}</b> no vendieron una sola unidad en noventa días y tienen "
        f"<b>{cop(quietas['valor_stock'].sum())}</b> quietos en bodega. En un negocio con margen "
        f"operacional cercano a cero, esa plata es la diferencia entre necesitar la línea de "
        f"crédito en octubre o no.<br><br>"
        f"El otro hallazgo es de precio: hay <b>{num(len(elite_fino))}</b> referencias que se "
        f"venden donde el precio Elite deja menos de 5% de margen bruto. Casi todas son whiskies "
        f"de las grandes casas — justo lo que más piden los miembros.<br><br>"
        f"<b>Propuesta:</b> liquidar lo quieto antes de noviembre en combos de regalo corporativo "
        f"(ahí el cliente no compara precio por botella) y fijar un piso de margen por referencia "
        f"para el precio Elite.",
        "🍾", "naranja"), unsafe_allow_html=True)
    st.caption("85 whiskies y más de 300 referencias según kyva.co. Precios de las referencias "
               "marcadas como observadas, tomados de kyva.co el 10-sep-2026. Ventas y stock simulados.")
