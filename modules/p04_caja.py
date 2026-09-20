"""Caja y capital de trabajo: por qué crecer al 130% con margen cero pide deuda.

En distribución de licores la plata se queda en tres lugares: la bodega, lo que
deben los clientes corporativos y lo que se le debe al proveedor. Con la
exclusiva de Mil Demonios, además, hay que comprar antes de vender.
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.formatters import *
from utils import datos


def render():
    st.markdown(HEADER_CSS, unsafe_allow_html=True)
    st.markdown(encabezado(
        "Caja y capital de trabajo",
        "Estado de resultados, inventario, cartera y deuda · mes a mes",
        "¿Crecer nos deja plata?"), unsafe_allow_html=True)

    f = datos.finanzas()
    c = datos.cabecera()
    u = f.iloc[-1]
    dias_inv = u["inventario"] / (f["costo_mercancia"].tail(3).mean() / 30)

    k = st.columns(4, gap="small")
    k[0].markdown(kpi("Caja", cop(u["caja"]), icon="🏦",
                      ayuda="Saldo al cierre de agosto."), unsafe_allow_html=True)
    k[1].markdown(kpi("Deuda de corto plazo", cop(u["deuda"]),
                      f"Máximo del período: {cop(f['deuda'].max())}", u["deuda"] == 0, "💳",
                      "Línea de crédito para cubrir el capital de trabajo."),
                  unsafe_allow_html=True)
    k[2].markdown(kpi("Inventario", cop(u["inventario"]), f"{num(dias_inv)} días de venta",
                      dias_inv < 45, "📦", "Incluye la compra de la exclusiva de Mil Demonios.",
                      "E-commerce de licores: 30–45 días"), unsafe_allow_html=True)
    k[3].markdown(kpi("Margen operacional 12 m", pct(c["margen_op12"], 2),
                      cop(c["utilidad12"]), c["margen_op12"] > 1, "⚖️",
                      "La utilidad que queda para financiar el crecimiento."),
                  unsafe_allow_html=True)

    st.markdown(espacio(14), unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["Capital de trabajo y deuda", "Estado de resultados"])

    with tab1:
        x = [mes_es(m) for m in f["mes"]]
        fig = go.Figure()
        fig.add_bar(x=x, y=f["inventario"], name="Inventario", marker_color=PRIMARIO)
        fig.add_bar(x=x, y=f["cartera"], name="Cartera por cobrar", marker_color=CLARO)
        fig.add_bar(x=x, y=-f["proveedores"], name="Deuda con proveedores", marker_color=PALIDO)
        fig.add_scatter(x=x, y=f["deuda"], name="Deuda bancaria", mode="lines",
                        line=dict(color=ACENTO, width=3))
        fig.update_layout(barmode="relative")
        st.plotly_chart(light(fig, 380, "Dónde está la plata", moneda=True),
                        width="stretch", theme=None, config=PLOTLY_CONFIG)
        st.markdown(panel(
            "Cómo leerlo",
            "Las barras de arriba son plata de KYVA inmovilizada (botellas en la bodega y "
            "facturas corporativas por cobrar). La barra de abajo es plata que los "
            "proveedores le prestan a KYVA mientras le pagan. Cuando lo de arriba crece más "
            "rápido que lo de abajo, la diferencia sale de la caja — o del banco.<br><br>"
            "Cada octubre se ve el mismo patrón: <b>se compra el inventario de diciembre "
            "antes de venderlo</b>, la deuda sube y se paga en enero. Con una utilidad "
            "operacional cercana a cero, no hay colchón para absorberlo: todo el pico lo "
            "financia la línea de crédito.",
            "🧭"), unsafe_allow_html=True)

    with tab2:
        f24 = f[f["mes"] >= "2025-01"].copy()
        filas = ["ingresos", "costo_mercancia", "margen_bruto", "logistica", "pasarela_y_empaque",
                 "mercadeo", "nomina", "arriendo_y_bodega", "tecnologia", "otros_gastos",
                 "utilidad_operacional"]
        nombres = ["Ingresos", "Costo de la mercancía", "Margen bruto", "Envíos a domicilio",
                   "Pasarela y empaque", "Mercadeo y eventos", "Nómina", "Arriendo y bodega",
                   "Tecnología", "Otros gastos", "Utilidad operacional"]
        f24["anio"] = f24["mes"].str[:4]
        a = f24.groupby("anio")[filas].sum().T
        a.index = nombres
        a.columns = ["2025" if x == "2025" else "ene–ago 2026" for x in a.columns]
        pct_ing = a.div(a.loc["Ingresos"], axis=1) * 100
        tabla = pd.DataFrame({
            "Concepto": nombres,
            "2025": [cop(v) for v in a["2025"]],
            "% de ingresos 2025": [pct(v) for v in pct_ing["2025"]],
            "ene–ago 2026": [cop(v) for v in a["ene–ago 2026"]],
            "% de ingresos 2026": [pct(v) for v in pct_ing["ene–ago 2026"]],
        })
        st.dataframe(tabla, hide_index=True, width="stretch")
        an = datos.anual()
        st.markdown(panel(
            "Lo que dice el estado de resultados",
            f"En 2025 los ingresos crecieron <b>{signo(an.loc['2025', 'crecimiento_pct'], 0)}</b> y "
            f"la utilidad operacional pasó de {cop(an.loc['2024', 'utilidad_operacional'])} a "
            f"{cop(an.loc['2025', 'utilidad_operacional'])}: el margen se quedó en "
            f"<b>{pct(an.loc['2025', 'margen_operacional_pct'], 2)}</b>. Los gastos crecieron "
            f"exactamente al ritmo de la venta — no hubo economía de escala.<br><br>"
            f"Las líneas que más se movieron son las que acompañan cada pedido: envíos, "
            f"pasarela y descuentos. Esas no bajan solas con el volumen; bajan con "
            f"decisiones de precio y de umbral de envío gratis.",
            "📑", "naranja"), unsafe_allow_html=True)
    st.caption("Datos simulados con fines de demostración. El margen operacional de 2025 y "
               "el crecimiento de la utilidad operacional están calibrados contra lo que "
               "reportó KYVA SAS (EMIS).")
