"""Marcas en distribución: Ron Defensor, Marcel Thorel y Mil Demonios.

El negocio más nuevo de KYVA: vender marcas a restaurantes, bares, hoteles y
otras tiendas. Con Mil Demonios en exclusiva desde 2026, KYVA pasa de revender
a tener que comprar inventario por adelantado y abrir mercado.
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.formatters import *
from utils import datos

COLOR_MARCA = {"Ron Defensor": PRIMARIO, "Marcel Thorel": CLARO, "Mil Demonios": ACENTO}


def render():
    st.markdown(HEADER_CSS, unsafe_allow_html=True)
    st.markdown(encabezado(
        "Marcas en distribución",
        "Sell-in a restaurantes, bares, hoteles y tiendas · inventario de la exclusiva",
        "¿Qué vendemos y a qué precio?"), unsafe_allow_html=True)

    d = datos.distribucion()
    cu = datos.cuentas_distribucion()
    inv = datos.inventario_exclusivas()
    u = datos.ultimos(3)
    act = d[d["mes"].isin(u)]["cuenta_id"].nunique()
    d12 = d[d["mes"].isin(datos.ultimos(12))]
    ult = inv.iloc[-1]
    ritmo = (inv["ventas_distribucion_u"] + inv["ventas_ecommerce_u"]).tail(3).mean()

    k = st.columns(4, gap="small")
    k[0].markdown(kpi("Venta de distribución (12 m)", cop(d12["ingreso_neto"].sum()),
                      icon="🚚", ayuda="Facturado a cuentas, sin IVA."), unsafe_allow_html=True)
    k[1].markdown(kpi("Cuentas que compraron (3 meses)", num(act),
                      f"{num(len(cu))} abiertas desde 2024", True, "🍽️",
                      "Restaurantes, bares, hoteles, clubes y tiendas."), unsafe_allow_html=True)
    k[2].markdown(kpi("Stock de Mil Demonios", f"{num(ult['stock_final_u'])} u",
                      f"{num(ult['stock_final_u'] / max(ritmo, 1) * 30)} días de venta", False, "🔥",
                      "Botellas de 700 ml en bodega. Es el stock que muestra kyva.co.",
                      "Cobertura sana para una marca nueva: 45–60 días"),
                  unsafe_allow_html=True)
    mb = (d12["ingreso_neto"] - d12["costo_mercancia"]).sum() / d12["ingreso_neto"].sum() * 100
    k[3].markdown(kpi("Margen bruto de distribución", pct(mb), icon="💰",
                      ayuda="Precio a la cuenta menos costo al productor."),
                  unsafe_allow_html=True)

    st.markdown(espacio(14), unsafe_allow_html=True)
    g1, g2 = st.columns([1.3, 1], gap="medium")
    with g1:
        g = d.groupby(["mes", "marca"])["ingreso_neto"].sum().unstack(fill_value=0)
        fig = go.Figure()
        for mca in ["Ron Defensor", "Marcel Thorel", "Mil Demonios"]:
            if mca in g:
                fig.add_bar(x=[mes_es(m) for m in g.index], y=g[mca], name=mca,
                            marker_color=COLOR_MARCA[mca])
        fig.update_layout(barmode="stack")
        st.plotly_chart(light(fig, 350, "Sell-in por marca", moneda=True),
                        width="stretch", theme=None, config=PLOTLY_CONFIG)
    with g2:
        x = [mes_es(m) for m in inv["mes"]]
        fig = go.Figure()
        fig.add_bar(x=x, y=inv["compras_u"], name="Compras al productor", marker_color=PALIDO)
        fig.add_bar(x=x, y=inv["ventas_distribucion_u"] + inv["ventas_ecommerce_u"],
                    name="Ventas (cuentas + kyva.co)", marker_color=ACENTO)
        fig.add_scatter(x=x, y=inv["stock_final_u"], name="Stock al cierre",
                        line=dict(color=PRIMARIO, width=3))
        fig.update_layout(barmode="group")
        st.plotly_chart(light(fig, 350, "Mil Demonios: compra, venta y stock (unidades)"),
                        width="stretch", theme=None, config=PLOTLY_CONFIG)

    cu_t = d12.merge(cu, on="cuenta_id").groupby("tipo").agg(
        cuentas=("cuenta_id", "nunique"), ingreso=("ingreso_neto", "sum"), unidades=("unidades", "sum"))
    cu_t["por_cuenta"] = cu_t["ingreso"] / cu_t["cuentas"]
    tabla = pd.DataFrame({
        "Tipo de cuenta": cu_t.index,
        "Cuentas": cu_t["cuentas"].map(num).values,
        "Venta 12 m": cu_t["ingreso"].map(cop).values,
        "Por cuenta": cu_t["por_cuenta"].map(cop).values,
        "Unidades": cu_t["unidades"].map(num).values,
    })
    st.dataframe(tabla, hide_index=True, width="stretch")

    ecom = inv["ventas_ecommerce_u"].sum()
    tot = (inv["ventas_distribucion_u"] + inv["ventas_ecommerce_u"]).sum()
    st.markdown(panel(
        "Lo que implica la exclusiva",
        f"Desde febrero KYVA compró <b>{num(inv['compras_u'].sum())}</b> botellas de Mil Demonios "
        f"y vendió <b>{num(tot)}</b>; solo el <b>{pct(ecom/tot*100, 0)}</b> salió por kyva.co, "
        f"el resto por cuentas. La marca vende 55.000–60.000 botellas al año en todo el país "
        f"y está en apenas 8 de los 32 departamentos (El Tiempo, dic-2025): la exclusiva es una "
        f"apuesta a abrirle Bogotá.<br><br>"
        f"Tres cosas para vigilar: (1) el <b>precio</b> — La Licorera la vende más barata que "
        f"KYVA (ver <i>Precio vs. competencia</i>); (2) la <b>cartera</b>, porque las cuentas de "
        f"distribución pagan a 60 días mientras el productor cobra antes; (3) la "
        f"<b>concentración</b>: pocas cuentas grandes hacen buena parte del volumen.<br><br>"
        f"<b>Propuesta:</b> un tablero semanal por cuenta — quién pidió, quién no repitió en 45 "
        f"días y quién paga tarde — para que el ejecutivo de cuentas llame a las correctas.",
        "🚚", "naranja"), unsafe_allow_html=True)
    st.caption("Mil Demonios en exclusiva desde 2026, Ron Defensor y Marcel Thorel según el "
               "perfil de LinkedIn de KYVA; stock según kyva.co. Cifras de sell-in simuladas.")
