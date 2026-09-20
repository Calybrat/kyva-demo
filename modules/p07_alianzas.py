"""Alianzas B2B2C: qué aliado trae miembros que compran.

El modelo de KYVA es regalar la membresía Elite a través de marcas de lujo y
organizaciones (Porsche Center, BoConcept, Argento & Bourbon, Foro de
Presidentes, EO…). Cada aliado trae una base distinta: unos traen compradores,
otros traen nombres en una lista.
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.formatters import *
from utils import datos


def render():
    st.markdown(HEADER_CSS, unsafe_allow_html=True)
    st.markdown(encabezado(
        "Alianzas B2B2C",
        "Cada aliado: cuántos miembros trajo, cuántos compran y cuánto deja · 12 meses",
        "¿Quién compra y vuelve?"), unsafe_allow_html=True)

    a = datos.aliados()
    tot = a.sum(numeric_only=True)
    mejor = a.sort_values("activacion_pct", ascending=False).index[0]
    peor = a.sort_values("activacion_pct").index[0]

    k = st.columns(4, gap="small")
    k[0].markdown(kpi("Aliados activos", num(len(a)), icon="🤝",
                      ayuda="Marcas y organizaciones que regalan la membresía Elite."),
                  unsafe_allow_html=True)
    k[1].markdown(kpi("Miembros traídos por aliados", num(tot["miembros"]),
                      f"{pct(tot['compraron']/tot['miembros']*100, 0)} compró alguna vez", True, "👥",
                      "Desde 2022."), unsafe_allow_html=True)
    k[2].markdown(kpi("Venta de sus miembros (12 m)", cop(tot["ingreso12"]),
                      f"Descuento otorgado: {cop(tot['descuento12'])}", True, "🛍️",
                      "Pedidos de The Lounge hechos por miembros de un aliado."),
                  unsafe_allow_html=True)
    k[3].markdown(kpi("El que mejor convierte", mejor, f"{pct(a.loc[mejor, 'activacion_pct'], 0)} compró",
                      True, "🏆", f"El que menos: {peor} ({pct(a.loc[peor, 'activacion_pct'], 0)})."),
                  unsafe_allow_html=True)

    st.markdown(espacio(14), unsafe_allow_html=True)
    t = a.reset_index()
    fig = go.Figure(go.Scatter(
        x=t["activacion_pct"], y=t["contrib_por_miembro"], mode="markers+text",
        text=t["aliado"], textposition="top center",
        marker=dict(size=(t["miembros"] / t["miembros"].max() * 55 + 14),
                    color=[ACENTO if x == "Convenios de nómina" else PRIMARIO for x in t["aliado"]],
                    opacity=.82, line=dict(color="#fff", width=2)),
        hovertemplate="%{text}<br>Compraron %{x:.0f}% · le deja %{y:$,.0f} por miembro<extra></extra>"))
    fig.update_layout(xaxis=dict(title="Miembros que compraron (%)", ticksuffix="%"),
                      yaxis=dict(title="Lo que le queda a KYVA por miembro (12 m)",
                                 tickprefix="$", tickformat=",.0f"),
                      hovermode="closest")
    st.plotly_chart(light(fig, 420, "Calidad de la base que trae cada aliado (tamaño = miembros)"),
                    width="stretch", theme=None, config=PLOTLY_CONFIG)

    tabla = pd.DataFrame({
        "Aliado": t["aliado"],
        "Miembros": [num(v) for v in t["miembros"]],
        "Compraron": [pct(v, 0) for v in t["activacion_pct"]],
        "Venta 12 m": [cop(v) for v in t["ingreso12"]],
        "Descuento dado 12 m": [cop(v) for v in t["descuento12"]],
        "Le queda a KYVA 12 m": [cop(v) for v in t["contribucion12"]],
        "Por miembro": [cop(v) for v in t["contrib_por_miembro"]],
    })
    st.dataframe(tabla, hide_index=True, width="stretch")

    nom = a.loc["Convenios de nómina"] if "Convenios de nómina" in a.index else None
    st.markdown(panel(
        "Qué hacer con esto",
        f"Los aliados no son iguales. <b>{mejor}</b> trae gente que compra: "
        f"{pct(a.loc[mejor, 'activacion_pct'], 0)} estrenó la membresía. "
        + (f"Los <b>convenios de nómina</b> son el aliado más grande en número "
           f"({num(nom['miembros'])} miembros) y el que menos convierte "
           f"({pct(nom['activacion_pct'], 0)}): regalar la membresía a toda una planta de "
           f"empleados infla el contador de miembros, no la venta. " if nom is not None else "") +
        f"<br><br><b>Propuesta:</b> a cada aliado, un reporte trimestral con cuántos de sus "
        f"miembros compraron y qué compraron. Convierte la alianza en una conversación de "
        f"datos — y le da a KYVA con qué renegociar: a los aliados que convierten, más "
        f"beneficios; a los que no, una activación conjunta (una cata en su sede, como la del "
        f"Porsche Center en septiembre de 2025) antes de renovar.",
        "🤝", "azul"), unsafe_allow_html=True)
    st.caption("Los nombres de los aliados son públicos (prensa y kyva.co). Sus cifras son "
               "simuladas con fines de demostración.")
