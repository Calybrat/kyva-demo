"""Tablero Ejecutivo: lo que el equipo de KYVA abre el lunes a las 7.

Tres horizontes en una pantalla: la semana que acaba de cerrar, el año que va
corriendo y la pregunta de fondo — que la empresa crece al 130% con el margen
operacional en cero.
"""
import plotly.graph_objects as go
import streamlit as st

from utils.formatters import *
from utils import datos


def _delta(a, b):
    return (a / b - 1) * 100 if b else 0.0


def render():
    st.markdown(HEADER_CSS, unsafe_allow_html=True)
    st.markdown(encabezado(
        "Tablero Ejecutivo",
        f"Semana del 24 al 30 de agosto · año corrido al {datos.CORTE_TXT}",
        "El lunes a las 7"), unsafe_allow_html=True)

    c = datos.cabecera()
    s = datos.semana()
    a, b = s["actual"], s["anterior"]

    # ── La semana ────────────────────────────────────────────────────────────
    st.markdown("##### La semana que cerró · e-commerce (The Store + The Lounge)")
    k = st.columns(4, gap="small")
    d = _delta(a["ingreso"], b["ingreso"])
    k[0].markdown(kpi("Venta de la semana", cop(a["ingreso"]),
                      f"{signo(d)} vs. la misma semana de 2025", d >= 0, "🛍️",
                      "Ingreso neto, sin IVA, de los pedidos entregados."),
                  unsafe_allow_html=True)
    d = _delta(a["pedidos"], b["pedidos"])
    k[1].markdown(kpi("Pedidos entregados", num(a["pedidos"]),
                      f"{signo(d)} · {num(a['nuevos'])} de clientes nuevos", d >= 0, "📦",
                      "Cuántas entregas salieron de la bodega."), unsafe_allow_html=True)
    d = _delta(a["ticket"], b["ticket"])
    k[2].markdown(kpi("Ticket promedio", cop(a["ticket"]), f"{signo(d)} vs. 2025", d >= 0, "🧾",
                      "Lo que paga el cliente por pedido, con IVA.",
                      f"Envío gratis desde $300.000"), unsafe_allow_html=True)
    k[3].markdown(kpi("Pedidos que esperaron el fin de semana", pct(a["espera_finde"], 0),
                      f"{num(a['cancelados'])} cancelados en la semana", False, "⏳",
                      "Entraron el viernes después de mediodía, el sábado o el domingo: "
                      "no hay despacho hasta el lunes."), unsafe_allow_html=True)

    st.markdown(espacio(18), unsafe_allow_html=True)

    # ── El año ───────────────────────────────────────────────────────────────
    st.markdown("##### El negocio completo · los cuatro canales")
    k = st.columns(4, gap="small")
    k[0].markdown(kpi("Ingresos ene–ago 2026", cop(c["ingresos_ytd"]),
                      f"{signo(c['crec_ytd'])} vs. ene–ago 2025", True, "📈",
                      "The Store, The Lounge, corporativo y distribución.",
                      f"2025 cerró en {signo(c['crec_2025'])}"), unsafe_allow_html=True)
    k[1].markdown(kpi("Margen bruto (12 meses)", pct(c["margen_bruto12"]),
                      "", True, "💰", "Lo que queda de cada peso vendido después de pagar "
                      "la mercancía.", "Retail de licores premium: 20–28%"),
                  unsafe_allow_html=True)
    k[2].markdown(kpi("Margen operacional (12 meses)", pct(c["margen_op12"], 2),
                      f"{cop(c['utilidad12'])} de utilidad", c["margen_op12"] > 1, "⚖️",
                      "Después de todos los gastos. En 2025 fue 0,08%.",
                      "Sano para crecer sin deuda: 4–8%"), unsafe_allow_html=True)
    k[3].markdown(kpi("Caja al corte", cop(c["caja"]),
                      f"Deuda {cop(c['deuda'])}" if c["deuda"] > 0 else "Sin deuda",
                      c["deuda"] == 0, "🏦", f"Inventario: {cop(c['inventario'])}. "
                      f"Equipo: {c['personas']} personas."), unsafe_allow_html=True)

    st.markdown(espacio(18), unsafe_allow_html=True)

    # ── Gráficas ─────────────────────────────────────────────────────────────
    g1, g2 = st.columns([1.55, 1], gap="medium")
    icm = datos.ingresos_canal_mes()
    icm = icm[icm["mes"] >= "2024-01"]
    with g1:
        fig = go.Figure()
        for canal in datos.CANALES:
            s_ = icm[icm["canal"] == canal]
            fig.add_bar(x=[mes_es(m) for m in s_["mes"]], y=s_["ingreso"], name=canal,
                        marker_color=PALETTE_SEGMENTO[canal],
                        hovertemplate="%{y:$,.0f}<extra>" + canal + "</extra>")
        fig.update_layout(barmode="stack")
        st.plotly_chart(light(fig, 360, "Ingresos por mes y por canal", moneda=True),
                        use_container_width=True)
    with g2:
        an = datos.anual()
        an = an[an.index.isin(["2023", "2024", "2025"])]
        fig = go.Figure()
        fig.add_bar(x=an.index.tolist(), y=an["ingresos"], name="Ingresos",
                    marker_color=PRIMARIO, text=[cop(v) for v in an["ingresos"]],
                    textposition="outside", hovertemplate="%{y:$,.0f}<extra>Ingresos</extra>")
        fig.add_bar(x=an.index.tolist(), y=an["utilidad_operacional"], name="Utilidad operacional",
                    marker_color=ACENTO, text=[cop(v) for v in an["utilidad_operacional"]],
                    textposition="outside", hovertemplate="%{y:$,.0f}<extra>Utilidad</extra>")
        fig.update_layout(barmode="group", yaxis=dict(showticklabels=False))
        st.plotly_chart(light(fig, 360, "Vender más no dejó más"), use_container_width=True)

    m = datos.margen_canal()
    peor = m.sort_values("contribucion_pct").iloc[0]
    lounge = m.set_index("canal").loc["The Lounge"]
    store = m.set_index("canal").loc["The Store"]
    st.markdown(panel(
        "Lo que dice el tablero",
        f"KYVA más que duplicó sus ingresos dos años seguidos "
        f"(<b>{signo(c['crec_2024'], 0)}</b> en 2024 y <b>{signo(c['crec_2025'], 0)}</b> en 2025) "
        f"y la utilidad operacional sigue en cero: <b>{pct(c['margen_op_2025'], 2)}</b> en 2025. "
        f"No es un problema de ventas. Es un problema de <b>mezcla</b>.<br><br>"
        f"De cada peso que vende The Lounge quedan <b>{pct(lounge['contribucion_pct'])}</b> "
        f"después de mercancía, envío y pasarela; en The Store quedan "
        f"<b>{pct(store['contribucion_pct'])}</b>. El canal que más creció en miembros es "
        f"el que menos deja, y el descuento Elite de los últimos doce meses sumó "
        f"<b>{cop(lounge['descuento'])}</b>.<br><br>"
        f"<b>La decisión de esta semana:</b> no es vender más, es decidir qué parte del "
        f"crecimiento se quiere comprar con margen. Los módulos de <i>Dónde se va el "
        f"margen</i> y <i>Membresía Elite</i> dicen dónde está cada peso.",
        "📌", "naranja"), unsafe_allow_html=True)

    st.caption("Datos simulados con fines de demostración, anclados a cifras públicas de "
               "KYVA SAS (crecimiento y margen reportados, precios y reglas de envío de "
               "kyva.co). Ver fuentes en el README.")
