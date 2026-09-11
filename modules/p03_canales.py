"""Los cuatro negocios de KYVA: The Store, The Lounge, corporativo y distribución.

Cuatro formas de ganar plata con márgenes, clientes y riesgos distintos. Verlos
en un solo número de ingresos esconde la decisión real: a cuál se le pone el
siguiente peso de capital y de tiempo del equipo.
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.formatters import *
from utils import datos

QUE_ES = {
    "The Store": "Tienda abierta al público desde oct-2023, precio Classic. Clientes "
                 "que llegan por Google, Instagram y referidos.",
    "The Lounge": "La tienda privada de los miembros Elite. La membresía casi siempre "
                  "llega gratis por una marca aliada: el modelo B2B2C.",
    "Corporativo": "Regalos de fin de año, obsequios a clientes, eventos, bodas y catas. "
                   "Pocos pedidos, tickets grandes y 60% de la venta en noviembre y diciembre.",
    "Distribución": "Marcas que KYVA distribuye a restaurantes, bares, hoteles y tiendas: "
                    "Ron Defensor, Marcel Thorel y, en exclusiva desde 2026, Mil Demonios.",
}


def render():
    st.markdown(HEADER_CSS, unsafe_allow_html=True)
    st.markdown(encabezado(
        "Los cuatro negocios",
        "Cuánto pesa cada canal, cuánto crece y cuánto deja · últimos 12 meses",
        "¿Crecer nos deja plata?"), unsafe_allow_html=True)

    m = datos.margen_canal().set_index("canal")
    icm = datos.ingresos_canal_mes()
    ms = datos.meses()
    u12, a12 = ms[-12:], ms[-24:-12]
    crec = {c: (icm[(icm.canal == c) & icm.mes.isin(u12)]["ingreso"].sum() /
                max(icm[(icm.canal == c) & icm.mes.isin(a12)]["ingreso"].sum(), 1) - 1) * 100
            for c in datos.CANALES}

    cols = st.columns(4, gap="small")
    for col, canal in zip(cols, datos.CANALES):
        r = m.loc[canal]
        col.markdown(kpi(
            canal, cop(r["ingreso"]),
            f"{signo(crec[canal], 0)} en 12 meses · {pct(r['peso_pct'], 0)} del total",
            True, ICONOS[canal], QUE_ES[canal],
            f"Le queda el {pct(r['contribucion_pct'])} de cada peso"), unsafe_allow_html=True)

    st.markdown(espacio(16), unsafe_allow_html=True)

    g1, g2 = st.columns([1.35, 1], gap="medium")
    with g1:
        piv = icm.pivot_table(index="mes", columns="canal", values="ingreso", aggfunc="sum")
        piv = piv[datos.CANALES]
        piv12 = piv.rolling(12).sum().dropna()
        mezcla = piv12.div(piv12.sum(axis=1), axis=0) * 100
        fig = go.Figure()
        for canal in datos.CANALES:
            fig.add_scatter(x=[mes_es(x) for x in mezcla.index], y=mezcla[canal], name=canal,
                            stackgroup="uno", line=dict(width=0.5, color=PALETTE_SEGMENTO[canal]),
                            hovertemplate="%{y:.1f}%<extra>" + canal + "</extra>")
        fig.update_layout(yaxis=dict(ticksuffix="%", range=[0, 100]))
        st.plotly_chart(light(fig, 360, "Mezcla de la venta (12 meses móviles)"),
                        use_container_width=True)
    with g2:
        t = m.reset_index()
        fig = go.Figure(go.Scatter(
            x=t["peso_pct"], y=t["contribucion_pct"], mode="markers+text",
            text=t["canal"], textposition="top center",
            marker=dict(size=(t["contribucion"].clip(lower=1) / t["contribucion"].max() * 60 + 18),
                        color=[PALETTE_SEGMENTO[c] for c in t["canal"]], opacity=.85,
                        line=dict(color="#fff", width=2)),
            hovertemplate="%{text}<br>Peso %{x:.0f}% · le queda %{y:.1f}%<extra></extra>"))
        fig.update_layout(xaxis=dict(title="Peso en la venta (%)", ticksuffix="%"),
                          yaxis=dict(title="Le queda de cada peso (%)", ticksuffix="%"),
                          hovermode="closest")
        st.plotly_chart(light(fig, 360, "Tamaño contra rentabilidad"), use_container_width=True)

    # ── Tabla ────────────────────────────────────────────────────────────────
    t = m.reset_index()
    tabla = pd.DataFrame({
        "Canal": t["canal"],
        "Ingreso 12 m": [cop(v) for v in t["ingreso"]],
        "Crecimiento": [signo(crec[c], 0) for c in t["canal"]],
        "Pedidos o facturas": [num(v) for v in t["pedidos"]],
        "Margen bruto": [pct(v) for v in t["margen_bruto_pct"]],
        "Le queda": [cop(v) for v in t["contribucion"]],
        "Le queda (%)": [pct(v) for v in t["contribucion_pct"]],
    })
    st.dataframe(tabla, hide_index=True, width="stretch")

    lo, st_, co, di = (m.loc[c] for c in datos.CANALES)
    st.markdown(panel(
        "Qué habría que decidir",
        f"<b>The Store</b> es hoy el motor: {pct(st_['peso_pct'], 0)} de la venta y el mejor "
        f"margen de los dos canales digitales. <b>The Lounge</b> pesa {pct(lo['peso_pct'], 0)} "
        f"pero le queda {pct(lo['contribucion_pct'])} de cada peso: es el canal que construyó "
        f"la marca y hoy es el que más margen consume.<br><br>"
        f"<b>Corporativo</b> deja {pct(co['contribucion_pct'])} con muy pocos pedidos, pero se "
        f"concentra en ocho semanas y paga a 45–60 días. <b>Distribución</b> es el canal "
        f"nuevo: crece más rápido que todos porque arrancó de cero, y con Mil Demonios obliga "
        f"a comprar inventario por adelantado.<br><br>"
        f"La pregunta para el comité no es cuánto crecer, es <b>con qué mezcla</b>. Cinco "
        f"puntos de venta que pasen de The Lounge a corporativo valen más utilidad que un "
        f"mes entero de crecimiento de The Store.",
        "🧭", "azul"), unsafe_allow_html=True)
    st.caption("Datos simulados con fines de demostración.")
