"""Precio contra la competencia, con precios reales vistos el 10-sep-2026.

La promesa de KYVA es «precios especiales que solo encuentras aquí». Esta
pantalla no usa datos simulados: compara los precios públicos de kyva.co con
los de La Licorera, Dislicores y Éxito para las mismas botellas.
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.formatters import *
from utils import datos


def render():
    st.markdown(HEADER_CSS, unsafe_allow_html=True)
    st.markdown(encabezado(
        "Precio vs. competencia",
        "Precios públicos reales, observados el 10 de septiembre de 2026",
        "¿Qué vendemos y a qué precio?"), unsafe_allow_html=True)

    p = datos.precios_competencia()
    caro_c = (p["dif_classic_pct"] > 0).sum()
    caro_e = (p["dif_elite_pct"] > 0).sum()

    st.markdown(panel(
        "Esta pantalla usa precios reales, no simulados",
        "Cada fila es un precio publicado en kyva.co y en la tienda de un competidor el mismo "
        "día. Cuando la presentación no es la misma (un litro contra 700 ml, o una botella "
        "con estuche), la comparación se hace por litro y se marca. Las fuentes están en la "
        "tabla y en el README.", "🔎", "azul"), unsafe_allow_html=True)
    st.markdown(espacio(8), unsafe_allow_html=True)

    k = st.columns(4, gap="small")
    k[0].markdown(kpi("Comparaciones", num(len(p)), icon="🏷️",
                      ayuda="Botellas con precio público en KYVA y en un competidor."),
                  unsafe_allow_html=True)
    k[1].markdown(kpi("Precio Classic más caro", f"{caro_c} de {len(p)}",
                      "Lo que ve cualquiera que entra a The Store", caro_c == 0, "🛍️",
                      "Botellas donde KYVA cobra más que el competidor, por litro."),
                  unsafe_allow_html=True)
    k[2].markdown(kpi("Precio Elite más caro", f"{caro_e} de {len(p)}",
                      "El precio de miembro gana en todas" if caro_e == 0 else "Ni con precio de miembro",
                      caro_e == 0, "🥂",
                      "Botellas donde ni el precio de miembro le gana al competidor."),
                  unsafe_allow_html=True)
    md = p[p["producto"].str.contains("Mil Demonios")]
    k[3].markdown(kpi("Mil Demonios en La Licorera", cop(md["precio_competidor"].min()),
                      f"KYVA Classic {cop(md['kyva_classic'].iloc[0])}", False, "🔥",
                      "La marca que KYVA distribuye en exclusiva desde 2026."),
                  unsafe_allow_html=True)

    st.markdown(espacio(12), unsafe_allow_html=True)
    etiqueta = [f"{a} · {b}" for a, b in zip(p["producto"], p["competidor"])]
    fig = go.Figure()
    fig.add_bar(y=etiqueta, x=p["dif_classic_pct"], orientation="h", name="Precio Classic",
                marker_color=PRIMARIO, text=[signo(v) for v in p["dif_classic_pct"]],
                textposition="outside")
    fig.add_bar(y=etiqueta, x=p["dif_elite_pct"], orientation="h", name="Precio Elite",
                marker_color=ACENTO, text=[signo(v) for v in p["dif_elite_pct"]],
                textposition="outside")
    fig.add_vline(x=0, line_color=MUTED, line_width=1)
    fig.update_layout(barmode="group", xaxis=dict(ticksuffix="%", title="KYVA frente al competidor"),
                      yaxis=dict(autorange="reversed"), hovermode="y unified")
    st.plotly_chart(light(fig, 430, "Diferencia de precio por litro (positivo = KYVA más caro)"),
                    use_container_width=True)

    tabla = pd.DataFrame({
        "Producto": p["producto"],
        "KYVA Classic": p["kyva_classic"].map(cop),
        "KYVA Elite": p["kyva_elite"].map(cop),
        "Competidor": p["competidor"],
        "Precio competidor": p["precio_competidor"].map(cop),
        "Comparación": ["por litro" if x else "misma botella" for x in p["por_litro"]],
        "Fuente": p["fuente"],
    })
    st.dataframe(tabla, hide_index=True, width="stretch",
                 column_config={"Fuente": st.column_config.LinkColumn("Fuente")})

    st.markdown(panel(
        "El punto débil que un cliente descubre en dos clics",
        "La promesa de KYVA es el precio. Pero el precio <b>Classic</b> —el que ve el público "
        "de The Store, que hoy es casi la mitad de la venta— no siempre gana: el Old Parr 12 de "
        "500 ml cuesta <b>$110.200</b> en KYVA y <b>$105.990</b> en Dislicores, y el precio Elite "
        "apenas le gana por 1,5%.<br><br>"
        "El caso más delicado es <b>Mil Demonios</b>: KYVA es su distribuidor exclusivo desde "
        "2026 y la vende a <b>$111.000</b> Classic, mientras La Licorera la tiene a "
        "<b>$100.990</b>. El distribuidor está siendo más caro que su propio cliente — un "
        "conflicto de canal que conviene resolver antes de diciembre.<br><br>"
        "Donde KYVA sí gana es en las botellas de las grandes casas con precio de miembro "
        "(Chivas 12 de litro a $155.600 Elite contra $186.700 en Éxito). <b>Propuesta:</b> "
        "monitorear cada semana las 50 referencias más vendidas contra tres competidores, y "
        "fijar la regla de que ninguna referencia visible en The Store quede por encima del "
        "mercado.", "🏷️", "alerta"), unsafe_allow_html=True)
    st.caption("Precios públicos vistos el 10-sep-2026; pueden cambiar. The Glenlivet 12: "
               "precio de KYVA calculado del combo de dos botellas en promoción.")
