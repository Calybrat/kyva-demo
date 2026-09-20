"""Membresía Elite (The Lounge): la promesa de la marca y su costo.

La membresía Elite casi siempre se regala a través de un aliado. Es lo que hizo
a KYVA distinta y es, a la vez, el canal con el margen más delgado. La pregunta
no es si sirve: es cuánto cuesta cada miembro que nunca estrenó la membresía y
cuánto descuento se le da a quien igual habría comprado.
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.formatters import *
from utils import datos


def render():
    st.markdown(HEADER_CSS, unsafe_allow_html=True)
    st.markdown(encabezado(
        "Membresía Elite",
        "The Lounge: cuántos miembros hay, cuántos compran y cuánto cuesta el descuento",
        "¿Quién compra y vuelve?"), unsafe_allow_html=True)

    e = datos.elite()
    m = datos.miembros()

    k = st.columns(4, gap="small")
    k[0].markdown(kpi("Miembros Elite", num(e["miembros"]),
                      f"{num(e['nunca_compraron'])} nunca compraron", False, "🥂",
                      "Todos los que recibieron o compraron la membresía desde 2022."),
                  unsafe_allow_html=True)
    k[1].markdown(kpi("Estrenaron la membresía", pct(e["activacion_pct"], 0), icon="✨",
                      ayuda="Miembros que hicieron al menos una compra en The Lounge.",
                      referencia="Programas de membresía regalada: 35–50%"),
                  unsafe_allow_html=True)
    k[2].markdown(kpi("Descuento Elite (12 meses)", cop(e["descuento12"]),
                      f"{pct(e['descuento12']/e['ingreso12']*100)} de la venta de The Lounge", False, "🎟️",
                      "Diferencia entre el precio Classic y lo que pagó el miembro."),
                  unsafe_allow_html=True)
    k[3].markdown(kpi("Margen bruto The Lounge", pct(e["margen_bruto_pct"]),
                      f"The Store: {pct(e['margen_bruto_store_pct'])}", False, "⚖️",
                      "Ingreso sin IVA menos mercancía."), unsafe_allow_html=True)

    st.markdown(espacio(14), unsafe_allow_html=True)
    g1, g2 = st.columns([1.3, 1], gap="medium")
    with g1:
        m2 = m.copy()
        m2["mes"] = m2["fecha_alta"].dt.strftime("%Y-%m")
        m2 = m2[m2["mes"] >= "2024-01"]
        g = m2.groupby(["mes", "origen"]).size().unstack(fill_value=0)
        fig = go.Figure()
        colores = {"Alianza": PRIMARIO, "Referido Elite": ACENTO, "Compra de membresía": CLARO}
        for o in ["Alianza", "Referido Elite", "Compra de membresía"]:
            if o in g:
                fig.add_bar(x=[mes_es(x) for x in g.index], y=g[o], name=o, marker_color=colores[o])
        fig.update_layout(barmode="stack")
        st.plotly_chart(light(fig, 350, "Miembros nuevos por mes, según cómo llegaron"),
                        width="stretch", theme=None, config=PLOTLY_CONFIG)
    with g2:
        act = m.groupby("origen")["compro"].mean() * 100
        fig = go.Figure(go.Bar(x=act.index, y=act.values,
                               marker_color=[colores.get(x, CLARO) for x in act.index],
                               text=[pct(v, 0) for v in act.values], textposition="outside"))
        fig.update_layout(yaxis=dict(ticksuffix="%", range=[0, 105]))
        st.plotly_chart(light(fig, 350, "Estrenaron la membresía, por origen"),
                        width="stretch", theme=None, config=PLOTLY_CONFIG)

    # ── Elite vs Classic ─────────────────────────────────────────────────────
    st.markdown("##### Un miembro Elite frente a un cliente de The Store")
    comp = pd.DataFrame({
        "": ["Ticket promedio (con IVA)", "Pedidos por cliente al año",
             "Margen bruto", "Descuento sobre precio Classic"],
        "The Lounge (Elite)": [cop(e["ticket"]), num(e["pedidos_por_cliente"], 1),
                               pct(e["margen_bruto_pct"]),
                               pct(e["descuento12"] / (e["ingreso12"] + e["descuento12"]) * 100)],
        "The Store (Classic)": [cop(e["ticket_store"]), num(e["pedidos_por_cliente_store"], 1),
                                pct(e["margen_bruto_store_pct"]), "solo en promociones"],
    })
    st.dataframe(comp, hide_index=True, width="stretch")

    no_al = m[(m["origen"] == "Alianza") & (~m["compro"])]
    st.markdown(panel(
        "El punto débil, dicho con cariño",
        f"El miembro Elite compra más seguido y con ticket más alto: la membresía sí "
        f"genera lealtad. Pero se paga cara. En doce meses KYVA regaló "
        f"<b>{cop(e['descuento12'])}</b> en descuento Elite, y el margen bruto de The Lounge "
        f"es <b>{pct(e['margen_bruto_pct'])}</b> contra <b>{pct(e['margen_bruto_store_pct'])}</b> "
        f"de The Store.<br><br>"
        f"El otro costo es invisible: <b>{num(len(no_al))}</b> personas recibieron la membresía "
        f"por un aliado y nunca compraron. No cuestan descuento, pero sí la promesa que KYVA le "
        f"hizo al aliado, y nadie las está llamando.<br><br>"
        f"<b>Tres decisiones posibles:</b> (1) Elite con precio escalonado — descuento completo "
        f"a partir del segundo pedido del año; (2) caducidad a los 12 meses sin compra, con una "
        f"invitación a reactivarla; (3) que el descuento de las marcas Pernod y Diageo lo "
        f"cofinancie la marca, que es la que gana con la exposición.",
        "🥂", "alerta"), unsafe_allow_html=True)
    st.caption("Membresía y precios Elite según kyva.co/faq. Cifras simuladas con fines de "
               "demostración.")
