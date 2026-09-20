"""Pide AM, recibe PM: el horario de despacho contra el horario de consumo.

KYVA despacha de lunes a jueves de 8am a 5pm y el viernes hasta las 4pm
(kyva.co/faq). Pero el licor se compra el jueves por la noche, el viernes y el
sábado. Esta pantalla mide lo que cuesta esa diferencia.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.formatters import *
from utils import datos

ORDEN = ["Pide AM · recibe PM", "Día hábil siguiente", "Espera fin de semana o festivo"]
COLOR_V = {"Pide AM · recibe PM": "#1E9E74", "Día hábil siguiente": CLARO,
           "Espera fin de semana o festivo": ACENTO}


def render():
    st.markdown(HEADER_CSS, unsafe_allow_html=True)
    st.markdown(encabezado(
        "Pide AM, recibe PM",
        "Cuándo compran los clientes, cuándo despacha KYVA y cuánto cuesta la espera · 12 meses",
        "¿Llegamos a tiempo?"), unsafe_allow_html=True)

    e = datos.entregas()
    v = e["ventanas"].reindex(ORDEN)
    p = datos.pedidos()
    p12 = p[p["mes"].isin(datos.ultimos(12))]

    k = st.columns(4, gap="small")
    k[0].markdown(kpi("Salen el mismo día", pct(v.loc[ORDEN[0], "peso_pct"], 0), icon="⚡",
                      ayuda="Pedidos que alcanzan la promesa «pide AM y recibe PM»."),
                  unsafe_allow_html=True)
    k[1].markdown(kpi("Esperan el fin de semana o un festivo", pct(e["finde_pct"], 0),
                      f"{num(v.loc[ORDEN[2], 'horas'])} horas de espera (mediana)", False, "⏳",
                      "Entran el viernes después de mediodía, el sábado, el domingo o un festivo.",
                      "Rappi Licores: 30–60 minutos, todos los días"), unsafe_allow_html=True)
    k[2].markdown(kpi("Cancelados (12 m)", num(e["cancelados12"]),
                      f"{cop(e['valor_cancelado12'])} en pedidos", False, "✖️",
                      f"{pct(e['cancel_pct'])} de todos los pedidos."), unsafe_allow_html=True)
    k[3].markdown(kpi("Entregados en la fecha prometida", pct(e["promesa_pct"]),
                      "Cae en la segunda quincena de diciembre", e["promesa_pct"] > 95, "📍",
                      "Llegaron el día que se comprometió KYVA."), unsafe_allow_html=True)

    st.markdown(espacio(14), unsafe_allow_html=True)
    g1, g2 = st.columns([1.35, 1], gap="medium")
    with g1:
        mapa = p12.groupby(["dia_semana", "hora"]).size().unstack(fill_value=0)
        mapa = mapa.reindex(index=range(7), columns=range(24), fill_value=0)
        fig = go.Figure(go.Heatmap(
            z=mapa.values, x=[f"{h}h" for h in range(24)], y=DIAS_ES,
            colorscale=[[0, "#FFFFFF"], [.4, PALIDO], [.75, CLARO], [1, PRIMARIO]],
            hovertemplate="%{y} %{x}: %{z} pedidos<extra></extra>", showscale=False))
        # El horario de despacho, dibujado encima
        for d in range(5):
            fin = 16 if d == 4 else 17
            fig.add_shape(type="rect", x0=7.5, x1=fin - .5, y0=d - .5, y1=d + .5,
                          line=dict(color=ACENTO, width=1.5), fillcolor="rgba(0,0,0,0)")
        fig.update_layout(yaxis=dict(autorange="reversed"), hovermode="closest")
        st.plotly_chart(light(fig, 360, "Cuándo compran (color) contra cuándo se despacha (recuadro)"),
                        width="stretch", theme=None, config=PLOTLY_CONFIG)
    with g2:
        fig = go.Figure(go.Bar(
            x=ORDEN, y=v["cancelacion"], marker_color=[COLOR_V[o] for o in ORDEN],
            text=[pct(x) for x in v["cancelacion"]], textposition="outside"))
        fig.update_layout(yaxis=dict(ticksuffix="%", title="Pedidos cancelados"))
        st.plotly_chart(light(fig, 360, "Cancelación según cuánto esperó el pedido"),
                        width="stretch", theme=None, config=PLOTLY_CONFIG)

    # ── Zonas ────────────────────────────────────────────────────────────────
    ok = p12[p12["estado"] == "Entregado"]
    z = ok.groupby("zona").agg(pedidos=("pedido_id", "size"), ticket=("valor_bruto", "mean"),
                               costo_envio=("costo_envio", "mean"),
                               envio_gratis=("envio_cobrado", lambda s: (s == 0).mean() * 100),
                               horas=("horas_espera", "median"))
    z = z.sort_values("pedidos", ascending=False)
    tabla = pd.DataFrame({
        "Zona": z.index, "Pedidos 12 m": z["pedidos"].map(num).values,
        "Ticket": z["ticket"].map(cop).values,
        "Costo de llevarlo": z["costo_envio"].map(cop).values,
        "Viajan gratis": z["envio_gratis"].map(lambda x: pct(x, 0)).values,
        "Horas de espera (mediana)": z["horas"].map(lambda x: num(x, 1)).values,
    })
    with st.expander("Por zona de entrega: Bogotá y la Sabana"):
        st.dataframe(tabla, hide_index=True, width="stretch")

    finde = v.loc[ORDEN[2]]
    st.markdown(panel(
        "El punto débil, en números",
        f"<b>{pct(e['finde_pct'], 0)} de los pedidos</b> entran cuando no hay despacho: viernes "
        f"después de mediodía, sábado, domingo o festivo. Esperan en promedio "
        f"<b>{num(finde['horas'])} horas</b> —y en Colombia hay 18 festivos, casi todos en lunes— "
        f"y se cancelan <b>{pct(finde['cancelacion'])}</b> de las veces, contra "
        f"{pct(v.loc[ORDEN[0], 'cancelacion'])} de los que salen el mismo día.<br><br>"
        f"Eso ya son <b>{cop(e['valor_perdido_finde'])}</b> al año en pedidos que se "
        f"cayeron solo por la espera. Y no mide el cliente que ni siquiera hizo el pedido "
        f"porque vio que le llegaba el lunes, ni el que se fue a Rappi.<br><br>"
        f"<b>Propuesta a probar un trimestre:</b> un turno de despacho los sábados de 9am a 2pm "
        f"con un solo operador logístico tercerizado. Con que recupere la mitad de las "
        f"cancelaciones, se paga — y convierte la promesa «pide AM y recibe PM» en una que "
        f"también vale el fin de semana, que es cuando se compra licor.",
        "⏱️", "alerta"), unsafe_allow_html=True)
    st.caption("Horario de despacho, zonas y costos de envío según kyva.co/faq. Festivos de "
               "Colombia 2023–2026. Pedidos simulados con fines de demostración.")
