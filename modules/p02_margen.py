"""Dónde se va el margen: de lo que paga el cliente a lo que le queda a KYVA.

Una cascada por pedido, canal por canal. Es la pantalla que explica por qué
una empresa que crece al 130% tiene utilidad operacional en cero.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.formatters import *
from utils import datos


def _cascada(p: pd.DataFrame) -> dict:
    """Pesos promedio por pedido, desde el precio sugerido de mercado."""
    n = len(p)
    pagado = (p["valor_bruto"] + p["envio_cobrado"] - p["cupon"]).sum()
    iva = pagado - (p["ingreso_neto"]).sum()
    return {
        "Precio de mercado": p["pvp"].sum() / n,
        "Descuento KYVA": -(p["pvp"] - p["valor_bruto"]).sum() / n,
        "Envío cobrado": p["envio_cobrado"].sum() / n,
        "Cupón Mi Círculo": -p["cupon"].sum() / n,
        "IVA": -iva / n,
        "Mercancía": -p["costo_mercancia"].sum() / n,
        "Envío a domicilio": -p["costo_envio"].sum() / n,
        "Pasarela de pago": -p["comision_pasarela"].sum() / n,
        "Empaque": -p["empaque"].sum() / n,
    }


def render():
    st.markdown(HEADER_CSS, unsafe_allow_html=True)
    st.markdown(encabezado(
        "Dónde se va el margen",
        "De lo que paga el cliente a lo que le queda a KYVA · últimos 12 meses",
        "¿Crecer nos deja plata?"), unsafe_allow_html=True)

    ok = datos.entregados()
    ok = ok[ok["mes"].isin(datos.ultimos(12))]
    canal = st.radio("Canal", ["The Store", "The Lounge"], horizontal=True, key="mg_canal")
    p = ok[ok["canal"] == canal]
    c = _cascada(p)
    queda = sum(c.values())

    m = datos.margen_canal().set_index("canal")
    k = st.columns(4, gap="small")
    k[0].markdown(kpi("Pedido promedio (precio de mercado)", cop(c["Precio de mercado"]),
                      icon="🏷️", ayuda="Lo que costaría la misma canasta al precio sugerido."),
                  unsafe_allow_html=True)
    k[1].markdown(kpi("Descuento KYVA por pedido", cop(-c["Descuento KYVA"]),
                      f"{pct(-c['Descuento KYVA']/c['Precio de mercado']*100)} del precio de mercado",
                      False, "🎟️", "La promesa de valor de KYVA — y su costo."),
                  unsafe_allow_html=True)
    k[2].markdown(kpi("Margen bruto", pct(m.loc[canal, "margen_bruto_pct"]),
                      icon="💰", ayuda="Ingreso sin IVA menos la mercancía.",
                      referencia="Retail de licores premium: 20–28%"), unsafe_allow_html=True)
    k[3].markdown(kpi("Le queda a KYVA por pedido", cop(queda),
                      f"{pct(m.loc[canal, 'contribucion_pct'])} del ingreso", queda > 20_000,
                      "🪙", "Antes de nómina, arriendo, pauta y todo lo demás."),
                  unsafe_allow_html=True)

    st.markdown(espacio(14), unsafe_allow_html=True)

    etiquetas = list(c.keys()) + ["Le queda a KYVA"]
    valores = list(c.values()) + [queda]
    medidas = ["absolute"] + ["relative"] * (len(c) - 1) + ["total"]
    fig = go.Figure(go.Waterfall(
        x=etiquetas, y=valores, measure=medidas,
        text=[cop(abs(v)) for v in valores], textposition="outside",
        increasing=dict(marker=dict(color=CLARO)),
        decreasing=dict(marker=dict(color=ACENTO)),
        totals=dict(marker=dict(color=PRIMARIO)),
        connector=dict(line=dict(color=BORDER))))
    fig.update_layout(yaxis=dict(showticklabels=False), showlegend=False)
    st.plotly_chart(light(fig, 420, f"Un pedido promedio de {canal}, peso por peso"),
                    use_container_width=True)

    # ── Comparación de canales ───────────────────────────────────────────────
    st.markdown("##### Los cuatro canales, lado a lado")
    t = m.reset_index()
    fig = go.Figure()
    fig.add_bar(y=t["canal"], x=t["margen_bruto_pct"], orientation="h", name="Margen bruto",
                marker_color=CLARO, text=[pct(v) for v in t["margen_bruto_pct"]],
                textposition="outside")
    fig.add_bar(y=t["canal"], x=t["contribucion_pct"], orientation="h", name="Le queda después de costos de la venta",
                marker_color=[PALETTE_SEGMENTO[x] for x in t["canal"]],
                text=[pct(v) for v in t["contribucion_pct"]], textposition="outside")
    fig.update_layout(barmode="group", xaxis=dict(ticksuffix="%"), hovermode="y unified",
                      yaxis=dict(autorange="reversed"))
    col1, col2 = st.columns([1.3, 1], gap="medium")
    with col1:
        st.plotly_chart(light(fig, 330, "Porcentaje del ingreso"), use_container_width=True)
    with col2:
        tabla = pd.DataFrame({
            "Canal": t["canal"],
            "Ingreso 12 m": [cop(v) for v in t["ingreso"]],
            "Peso": [pct(v, 0) for v in t["peso_pct"]],
            "Margen bruto": [pct(v) for v in t["margen_bruto_pct"]],
            "Le queda": [cop(v) for v in t["contribucion"]],
        })
        st.dataframe(tabla, hide_index=True, width="stretch")

    # ── Pedidos que pierden plata ────────────────────────────────────────────
    neg = p[p["contribucion"] < 0]
    chicos = p[p["valor_bruto"] < 300_000]
    grandes = p[p["valor_bruto"] >= 300_000]
    st.markdown(panel(
        "Qué significa",
        f"En {canal} se entregaron <b>{num(len(p))}</b> pedidos en doce meses y "
        f"<b>{num(len(neg))} ({pct(len(neg)/len(p)*100, 0)})</b> dejaron plata negativa "
        f"antes de pagar un solo gasto fijo. Casi todos tienen algo en común: "
        f"<b>están por encima de $300.000 y viajan gratis</b>, o llevan un producto con "
        f"descuento de promoción encima del precio de miembro.<br><br>"
        f"Un pedido de menos de $300.000 deja en promedio "
        f"<b>{cop(chicos['contribucion'].mean())}</b>; uno de más de $300.000 deja "
        f"<b>{cop(grandes['contribucion'].mean())}</b>. El umbral de envío gratis se "
        f"fijó cuando el ticket era otro.<br><br>"
        f"<b>Tres palancas, en orden de facilidad:</b> (1) subir el umbral de envío gratis "
        f"o cobrarlo en la Sabana, donde cuesta un 45% más; (2) no apilar promociones sobre "
        f"el precio Elite; (3) negociar con Pernod y Diageo que el descuento Elite lo "
        f"cofinancie la marca, como ya hacen con el retail tradicional.",
        "🔎", "alerta"), unsafe_allow_html=True)

    st.caption("Precio de mercado = precio sugerido de venta al público. Datos simulados "
               "con fines de demostración.")
