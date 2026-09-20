"""Temporada de fin de año: lo que hay que decidir en septiembre.

Diciembre es más de una quinta parte del año, y lo que se venda en diciembre
se decide en septiembre: el inventario se compra en octubre, las cotizaciones
corporativas se cierran en octubre y noviembre, y la capacidad de despacho se
arma antes. Amor y Amistad (19 de septiembre) es el ensayo general.
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.formatters import *
from utils import datos


def render():
    st.markdown(HEADER_CSS, unsafe_allow_html=True)
    st.markdown(encabezado(
        "Temporada de fin de año",
        "Estacionalidad, pipeline corporativo y la lección del IVA de enero",
        "¿Qué viene?"), unsafe_allow_html=True)

    f = datos.finanzas()
    pdic = datos.pipeline_diciembre()
    an = datos.anual()
    dic25 = f.loc[f["mes"] == "2025-12", "ingresos"].iloc[0]
    peso_dic = dic25 / an.loc["2025", "ingresos"] * 100
    cobertura = pdic["cotizado_a_31ago_2025"]

    k = st.columns(4, gap="small")
    k[0].markdown(kpi("Diciembre sobre el año", pct(peso_dic, 0), f"{cop(dic25)} en dic-2025",
                      True, "🎄", "Una quinta parte de la venta en cuatro semanas.",
                      "Aguardiente en Colombia: ~20% (El Colombiano)"), unsafe_allow_html=True)
    k[1].markdown(kpi("Corporativo ganado nov–dic 2025", cop(pdic["ganado_nov_dic_2025"]),
                      f"Tasa de cierre {pct(pdic['tasa_cierre_2025'], 0)}", True, "🎁",
                      "Regalos de fin de año, obsequios y eventos."), unsafe_allow_html=True)
    k[2].markdown(kpi("Pipeline nov–dic 2026 (hoy)", cop(pdic["abierto_nov_dic_2026"]),
                      f"{num(pdic['n_abiertas'])} cotizaciones abiertas", False, "📋",
                      f"Ponderado por probabilidad: {cop(pdic['ponderado_nov_dic_2026'])}."),
                  unsafe_allow_html=True)
    k[3].markdown(kpi("A esta fecha en 2025 había cotizado", cop(cobertura), icon="🗓️",
                      ayuda="Valor cotizado para nov–dic 2025 al 31 de agosto de 2025."),
                  unsafe_allow_html=True)

    st.markdown(espacio(14), unsafe_allow_html=True)
    g1, g2 = st.columns([1.3, 1], gap="medium")
    with g1:
        icm = datos.ingresos_canal_mes()
        icm["anio"] = icm["mes"].str[:4]
        icm["m"] = icm["mes"].str[5:].astype(int)
        fig = go.Figure()
        estilos = {"2024": (PALIDO, "dot"), "2025": (CLARO, "solid"), "2026": (PRIMARIO, "solid")}
        for anio, (color, dash) in estilos.items():
            s = icm[icm["anio"] == anio].groupby("m")["ingreso"].sum()
            fig.add_scatter(x=[MESES_ES[i - 1] for i in s.index], y=s.values, name=anio,
                            line=dict(color=color, width=3, dash=dash), mode="lines+markers")
        fig.add_annotation(x="ene", y=float(icm[(icm["mes"] == "2026-01")]["ingreso"].sum()) / 1e6,
                           text="IVA 19% (1–29 ene)", showarrow=True, arrowhead=2, ay=-50,
                           font=dict(color=ACENTO, size=11))
        st.plotly_chart(light(fig, 360, "La forma del año: ingresos por mes", moneda=True),
                        width="stretch", theme=None, config=PLOTLY_CONFIG)
    with g2:
        co = datos.corporativo()
        co25 = co[co["fecha_entrega"].dt.year == 2025]
        perd = co25[co25["estado"] == "Perdida"]["motivo_perdida"].value_counts()
        fig = go.Figure(go.Bar(y=perd.index, x=perd.values, orientation="h",
                               marker_color=[ACENTO if "entrega" in x.lower() or "Precio" in x else CLARO
                                             for x in perd.index],
                               text=perd.values, textposition="outside"))
        fig.update_layout(yaxis=dict(autorange="reversed"), hovermode="y unified")
        st.plotly_chart(light(fig, 360, "Por qué se perdieron cotizaciones corporativas en 2025"),
                        width="stretch", theme=None, config=PLOTLY_CONFIG)

    abiertas = co[co["estado"] == "Abierta"].sort_values("valor_cotizado", ascending=False)
    t = pd.DataFrame({
        "Cotización": abiertas["cotizacion_id"], "Empresa": abiertas["empresa"],
        "Sector": abiertas["sector"], "Tipo": abiertas["tipo"],
        "Entrega": abiertas["fecha_entrega"].dt.strftime("%d %b"),
        "Valor": abiertas["valor_cotizado"].map(cop),
        "Probabilidad": abiertas["probabilidad"].map(lambda x: pct(x * 100, 0)),
    })
    with st.expander(f"Las {len(abiertas)} cotizaciones abiertas, de la más grande a la más pequeña"):
        st.dataframe(t, hide_index=True, width="stretch")

    ene = f.set_index("mes")
    caida = (ene.loc["2026-01", "ingreso_store"] + ene.loc["2026-01", "ingreso_lounge"]) / \
            (ene.loc["2025-01", "ingreso_store"] + ene.loc["2025-01", "ingreso_lounge"]) - 1
    st.markdown(panel(
        "Lo que se decide en septiembre",
        f"<b>1 · El inventario.</b> Diciembre pesa {pct(peso_dic, 0)} del año y la compra se hace "
        f"en octubre, con la caja más apretada del año (ver <i>Caja y capital de trabajo</i>). "
        f"Comprar con base en el diciembre pasado más el crecimiento del año es la forma más "
        f"segura de quedar corto en whisky y largo en lo que no rota.<br><br>"
        f"<b>2 · El corporativo.</b> Hoy hay {cop(pdic['abierto_nov_dic_2026'])} cotizados para "
        f"noviembre y diciembre. Un año atrás, a esta misma fecha, había "
        f"{cop(cobertura)}. Las cotizaciones que se pierden por <b>tiempo de entrega</b> se "
        f"resuelven con capacidad, no con precio.<br><br>"
        f"<b>3 · La lección de enero.</b> Del 1 al 29 de enero de 2026 rigió el IVA del 19% a "
        f"licores (Decreto 1474 de 2025), hasta que la Corte lo suspendió; el 15 de abril lo "
        f"tumbó. La venta de enero en los canales digitales quedó {signo(caida*100, 0)} contra "
        f"enero de 2025 cuando venía creciendo mucho más. Un cambio de impuesto se puede "
        f"volver a proponer: tener listo el plan de precios para ese escenario cuesta poco.",
        "🎄", "naranja"), unsafe_allow_html=True)
    st.caption("IVA del 19%: Decreto 1474 de 2025, suspendido el 29-ene-2026 y declarado "
               "inexequible el 15-abr-2026. Cotizaciones y ventas simuladas.")
