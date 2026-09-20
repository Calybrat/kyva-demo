"""Mi Círculo: el programa de referidos, que es el propio lema de la marca.

«Join the circle». Cada cliente puede invitar a quien quiera; el invitado recibe
un cupón y quien lo invitó recibe otro después de la primera compra del
invitado (kyva.co/faq). Es el canal de adquisición más barato que tiene KYVA.
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.formatters import *
from utils import datos


def render():
    st.markdown(HEADER_CSS, unsafe_allow_html=True)
    st.markdown(encabezado(
        "Mi Círculo",
        "Invitaciones, registros, primeras compras y lo que cuesta cada cupón",
        "¿Quién compra y vuelve?"), unsafe_allow_html=True)

    mc = datos.mi_circulo()
    u12 = mc[mc["mes"].isin(datos.ultimos(12))]
    cli = datos.clientes()
    r = datos.recompra_origen()
    ref = cli[cli["referido_por"] != ""]
    top = ref.groupby("referido_por").size().sort_values(ascending=False)
    top_20 = top.head(int(len(top) * .2)).sum() / top.sum() * 100 if len(top) else 0
    cac_pauta = r["cac"].dropna()
    costo_ref = u12["costo_cupones"].sum() / max(u12["primera_compra"].sum(), 1)

    k = st.columns(4, gap="small")
    k[0].markdown(kpi("Invitaciones (12 m)", num(u12["invitaciones"].sum()), icon="✉️",
                      ayuda="Enviadas desde la sección Mi Círculo."), unsafe_allow_html=True)
    conv = u12["primera_compra"].sum() / u12["invitaciones"].sum() * 100
    k[1].markdown(kpi("De invitación a compra", pct(conv), icon="🎯",
                      ayuda="Invitaciones que terminaron en una primera compra.",
                      referencia="Programas de referidos en e-commerce: 5–12%"),
                  unsafe_allow_html=True)
    k[2].markdown(kpi("Clientes nuevos por referido (12 m)", num(u12["primera_compra"].sum()),
                      icon="⭕", ayuda="Classic por Mi Círculo y Elite referidos por otro miembro."),
                  unsafe_allow_html=True)
    k[3].markdown(kpi("Costo por cliente referido", cop(costo_ref),
                      f"Pauta: {cop(cac_pauta.min())}–{cop(cac_pauta.max())}" if len(cac_pauta) else "",
                      True, "🪙", "Los dos cupones (invitado y anfitrión) sobre las primeras compras."),
                  unsafe_allow_html=True)

    st.markdown(espacio(14), unsafe_allow_html=True)
    g1, g2 = st.columns([1, 1.3], gap="medium")
    with g1:
        etapas = ["Invitaciones", "Se registraron", "Primera compra"]
        vals = [u12["invitaciones"].sum(), u12["registrados"].sum(), u12["primera_compra"].sum()]
        fig = go.Figure(go.Funnel(y=etapas, x=vals, textinfo="value+percent initial",
                                  marker=dict(color=[PALIDO, CLARO, PRIMARIO])))
        fig.update_layout(hovermode="closest")
        st.plotly_chart(light(fig, 330, "El embudo de los últimos 12 meses"),
                        width="stretch", theme=None, config=PLOTLY_CONFIG)
    with g2:
        mm = mc[mc["mes"] >= "2024-01"]
        fig = go.Figure()
        fig.add_bar(x=[mes_es(m) for m in mm["mes"]], y=mm["primera_compra"],
                    name="Clientes nuevos por referido", marker_color=PRIMARIO)
        fig.add_scatter(x=[mes_es(m) for m in mm["mes"]],
                        y=mm["primera_compra"] / mm["invitaciones"] * 100,
                        name="Conversión (%)", yaxis="y2", mode="lines",
                        line=dict(color=ACENTO, width=2.5))
        fig.update_layout(yaxis2=dict(overlaying="y", side="right", ticksuffix="%",
                                      showgrid=False, rangemode="tozero"))
        st.plotly_chart(light(fig, 330, "Mes a mes"), width="stretch", theme=None, config=PLOTLY_CONFIG)

    st.markdown(panel(
        "El círculo lo mueve poca gente",
        f"El <b>20% de los anfitriones</b> trae el <b>{pct(top_20, 0)}</b> de los referidos. "
        f"Hay {num(len(top))} clientes que han invitado a alguien que compró; los diez más "
        f"activos trajeron {num(top.head(10).sum())} clientes entre todos.<br><br>"
        f"Es la palanca de adquisición más barata del negocio y además la de mejor calidad: "
        f"el referido vuelve más que el cliente de pauta. Y está sub-explotada: una de cada "
        f"{num(1/ max(conv/100, 1e-9))} invitaciones termina en compra, y casi nadie invita.<br><br>"
        f"<b>Propuesta:</b> un programa de embajadores para los anfitriones que ya refieren — "
        f"acceso anticipado a lanzamientos (Mil Demonios es el candidato perfecto) y una cata "
        f"privada al año. Cuesta menos que un mes de pauta en Meta.",
        "⭕", "ok"), unsafe_allow_html=True)

    lista = (top.head(12).rename("referidos_que_compraron").reset_index()
             .rename(columns={"referido_por": "Cliente anfitrión"}))
    lista = lista.merge(cli[["cliente_id", "tipo", "zona", "pedidos"]],
                        left_on="Cliente anfitrión", right_on="cliente_id").drop(columns="cliente_id")
    lista.columns = ["Cliente anfitrión", "Referidos que compraron", "Tipo", "Zona", "Pedidos propios"]
    with st.expander("Los 12 anfitriones que más han traído"):
        st.dataframe(lista, hide_index=True, width="stretch")
    st.caption(md("Reglas del programa según kyva.co/faq. Valor del cupón ($25.000) y cifras "
               "simuladas con fines de demostración."))
