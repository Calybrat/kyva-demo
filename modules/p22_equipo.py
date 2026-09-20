"""Equipo comercial: margen por vendedor, no venta.

El informe de ventas que ya existe en cualquier ERP premia al que más factura, y
en una distribuidora eso casi siempre premia al que más descuento regala. Es el
incentivo invertido más común del sector: el vendedor que cierra a 27% aparece
primero, y el que sostuvo el 19% aparece último aunque haya traído más plata.

Aquí el ranking es por **margen después de servir**, que es lo que de verdad
entra. Y la comisión se simula sobre esa base para que la conversación sea
concreta: no «vendan con más margen» sino «así te habría quedado el mes».

La otra cosa que este módulo hace y un ranking no: separa lo que el vendedor
controla de lo que no. La mezcla de canales de su zona no la eligió él —en
Medellín todavía no hay clubes sociales—, así que compararlo contra alguien de
Bogotá sin corregir por eso es injusto y se nota.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.formatters import *
from utils import b2b

# Dos esquemas para poder comparar en pantalla. El punto del módulo es que el
# de la izquierda es el que casi todas las distribuidoras usan, y es el que
# produce el comportamiento que después nadie entiende.
ESQUEMAS = {
    "Sobre venta (el de hoy)": {"base": "neto", "tasa": 0.018},
    "Sobre margen servido": {"base": "servido", "tasa": 0.085},
}


def render():
    st.markdown(HEADER_CSS, unsafe_allow_html=True)
    st.markdown(encabezado(
        "Equipo comercial",
        "Quién trae margen, no quién factura más · último trimestre",
        "¿Quién nos deja plata?"), unsafe_allow_html=True)

    r = b2b.rentabilidad()
    v = b2b.vendedores()

    g = r.groupby("vendedor").agg(
        cuentas=("cuenta_id", "size"), neto=("neto", "sum"),
        bruto=("bruto", "sum"), descuento=("descuento", "sum"),
        margen=("margen", "sum"), logistica=("logistica", "sum"),
        servido=("servido", "sum"), entregas=("entregas", "sum")).reset_index()
    g = g.merge(v[["vendedor", "ciudad", "desde", "cuota_mes", "estilo"]],
                on="vendedor", how="left")
    g["desc_pct"] = g["descuento"] / g["bruto"] * 100
    g["margen_pct"] = g["margen"] / g["neto"] * 100
    g["servido_pct"] = g["servido"] / g["neto"] * 100
    g["cumplimiento"] = g["neto"] / (g["cuota_mes"] * 3) * 100
    g["ticket"] = g["neto"] / g["entregas"].clip(lower=1)

    por_venta = g.sort_values("neto", ascending=False)["vendedor"].tolist()
    por_tasa = g.sort_values("servido_pct", ascending=False)["vendedor"].tolist()
    invertidos = [x for x in por_venta if por_venta.index(x) != por_tasa.index(x)]
    # Cuánto costaría el descuento extra del que más regala, medido contra el
    # que menos: es el número que vuelve concreta la conversación.
    mas, menos = g.nlargest(1, "desc_pct").iloc[0], g.nsmallest(1, "desc_pct").iloc[0]
    costo_descuento = (mas["desc_pct"] - menos["desc_pct"]) / 100 * mas["bruto"]

    k = st.columns(4, gap="small")
    k[0].markdown(kpi(
        "Vendedores", num(len(g)),
        f"{int(g['cuentas'].sum())} cuentas atendidas", True, "👥",
        "Dos ciudades. Medellín abrió en marzo."), unsafe_allow_html=True)
    k[1].markdown(kpi(
        "Descuento promedio", pct(g["descuento"].sum() / g["bruto"].sum() * 100),
        f"de {pct(g['desc_pct'].min())} a {pct(g['desc_pct'].max())} según quién venda",
        False, "🏷️",
        "La diferencia entre el que menos y el que más regala, sobre la misma lista."),
        unsafe_allow_html=True)
    k[2].markdown(kpi(
        "Cumplimiento de cuota", pct(g["neto"].sum() / (g["cuota_mes"].sum() * 3) * 100),
        f"{int((g['cumplimiento'] >= 100).sum())} de {len(g)} en meta",
        g["neto"].sum() / (g["cuota_mes"].sum() * 3) >= 1, "🎯",
        "Cuota medida en venta neta, como está hoy."), unsafe_allow_html=True)
    k[3].markdown(kpi(
        "Lo que cuesta el descuento extra", cop(costo_descuento, 0),
        f"{mas['vendedor'].split()[0]} regala {pct(mas['desc_pct'] - menos['desc_pct'])} "
        f"más que {menos['vendedor'].split()[0]}", False, "",
        "Sobre su propia venta del trimestre. No es un reproche: es el precio "
        "de un incentivo que premia facturar.",
        f"{len(invertidos)} vendedores cambian de puesto al ordenar por tasa "
        f"de margen"), unsafe_allow_html=True)

    st.markdown(espacio(18), unsafe_allow_html=True)

    # ── El vuelco del ranking ───────────────────────────────────────────────
    st.markdown('<div class="ky-sub">El que más vende no es el que mejor vende</div>',
                unsafe_allow_html=True)
    izq = g.sort_values("neto", ascending=True)
    der = g.sort_values("servido", ascending=True)

    # Antes esto eran dos barras en la misma escala, y como el margen servido es
    # una fracción de la venta, la segunda barra no se veía. El parche fue
    # multiplicarla por cuatro y CONFESARLO en la leyenda: «Margen servido (×4
    # para verlo)». Una auditoría de diseño lo señaló y tenía razón — ningún
    # producto serio expone un factor de deformación en la leyenda, porque le
    # está diciendo al lector que el gráfico miente un poco.
    #
    # La solución no es un eje secundario: es cambiar la pregunta. Lo que
    # importa no son dos magnitudes sino el CONTRASTE entre posición por venta
    # y posición por margen, y eso se ve mejor con la venta como barra y el
    # margen como porcentaje sobre ella.
    orden = g.sort_values("servido", ascending=True)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=orden["vendedor"], x=orden["neto"], orientation="h",
        name="Venta neta", marker_color=PALIDO,
        text=[f"{v:.1f}% margen" for v in orden["servido_pct"]],
        textposition="inside", insidetextanchor="end",
        textfont=dict(size=11, color=TINTA),
        customdata=np.stack([orden["servido"], orden["desc_pct"]], -1),
        hovertemplate="<b>%{y}</b><br>Venta: %{x:,.0f}"
                      "<br>Margen servido: %{customdata[0]:,.0f}"
                      "<br>Descuento: %{customdata[1]:.1f}%<extra></extra>"))
    fig.add_trace(go.Bar(
        y=orden["vendedor"], x=orden["servido"], orientation="h",
        name="De eso, lo que queda", marker_color=PRIMARIO,
        hovertemplate="%{y}<br>Queda: %{x:,.0f}<extra></extra>"))
    # Superpuestas, no agrupadas: la barra oscura DENTRO de la clara muestra
    # qué proporción de lo que vendió sobrevive al descuento y al reparto.
    fig.update_layout(barmode="overlay")
    st.plotly_chart(light(fig, 300, moneda=True), width="stretch", theme=None, config=PLOTLY_CONFIG)

    top_venta = g.nlargest(1, "neto").iloc[0]
    top_margen = g.nlargest(1, "servido").iloc[0]
    if top_venta["vendedor"] != top_margen["vendedor"]:
        dif = top_margen["servido"] - top_venta["servido"]
        st.markdown(panel(
            "El número uno depende de qué se mida",
            f"<b>{top_venta['vendedor']}</b> es primero en venta "
            f"({cop(top_venta['neto'], 0)}) con {pct(top_venta['desc_pct'])} de "
            f"descuento promedio. <b>{top_margen['vendedor']}</b> vendió "
            f"{cop(top_margen['neto'], 0)} con {pct(top_margen['desc_pct'])}, "
            f"y dejó <b>{cop(dif, 0)} más</b> en el trimestre. "
            f"Con el esquema de comisión actual —sobre venta— el primero cobra "
            f"más. Eso no es un problema de las personas: es el diseño del "
            f"incentivo, y se arregla cambiando la base, no pidiendo esfuerzo.",
            "🔄", "rojo"), unsafe_allow_html=True)

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── Simulador de comisión ───────────────────────────────────────────────
    st.markdown('<div class="ky-sub">Qué pasa si se cambia la base de la comisión</div>',
                unsafe_allow_html=True)
    c = st.columns([1, 1, 2])
    esquema = c[0].selectbox("Esquema", list(ESQUEMAS), index=1, key="eq_esq")
    cfg = ESQUEMAS[esquema]
    tasa = c[1].slider("Tasa (%)", 0.5, 12.0, float(cfg["tasa"] * 100), 0.1,
                       key="eq_tasa") / 100

    sim = g.copy()
    sim["com_hoy"] = sim["neto"] * ESQUEMAS["Sobre venta (el de hoy)"]["tasa"]
    sim["com_nueva"] = sim[cfg["base"]] * tasa
    sim["delta"] = sim["com_nueva"] - sim["com_hoy"]
    sim = sim.sort_values("servido", ascending=False)

    # La tabla recibe NÚMEROS, no texto ya formateado.
    #
    # Con `cop()` y `pct()` aplicados antes, el grid recibe strings: ordenar por
    # «Venta neta» ordena alfabéticamente, las cifras se alinean a la izquierda
    # y comparar dos filas obliga a leer dígito por dígito. Con column_config
    # Streamlit ordena bien, alinea a la derecha y formatea solo.
    t = sim[["vendedor", "ciudad", "estilo", "cuentas", "neto", "desc_pct",
             "servido_pct", "servido", "com_hoy", "com_nueva", "delta"]].copy()
    for col in ("neto", "servido", "com_hoy", "com_nueva", "delta"):
        t[col] = (t[col] / 1e6).round(1)
    t.columns = ["Vendedor", "Ciudad", "Estilo", "Cuentas", "Venta neta", "Descuento",
                 "Margen servido %", "Margen servido", "Comisión hoy",
                 "Comisión nueva", "Diferencia"]
    tope = float(t["Margen servido %"].max()) * 1.15
    st.dataframe(t, hide_index=True, width="stretch", row_height=40,
                 column_config={
        "Venta neta": st.column_config.NumberColumn(format="$%.0f M"),
        "Descuento": st.column_config.NumberColumn(format="%.1f%%"),
        # La barra hace visible de un vistazo el cruce que la pantalla entera
        # quiere demostrar, sin necesidad de otro gráfico.
        "Margen servido %": st.column_config.ProgressColumn(
            format="%.1f%%", min_value=0, max_value=tope),
        "Margen servido": st.column_config.NumberColumn(format="$%.0f M"),
        "Comisión hoy": st.column_config.NumberColumn(format="$%.1f M"),
        "Comisión nueva": st.column_config.NumberColumn(format="$%.1f M"),
        "Diferencia": st.column_config.NumberColumn(format="$%+.1f M"),
    })

    costo_hoy = sim["com_hoy"].sum()
    costo_nuevo = sim["com_nueva"].sum()
    st.caption(md(
        f"Costo total de comisiones: **{cop(costo_hoy, 0)}** hoy contra "
        f"**{cop(costo_nuevo, 0)}** con este esquema. "
        f"La tasa se puede calibrar para que el costo total no cambie —lo que "
        f"cambia es **quién cobra qué**— y esa es la única forma de que el equipo "
        f"acepte la conversación."))

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── Lo que el vendedor no controla ──────────────────────────────────────
    st.markdown('<div class="ky-sub">Qué parte es mérito y qué parte es la zona</div>',
                unsafe_allow_html=True)
    mix = (r.groupby(["vendedor", "canal"])["neto"].sum().reset_index())
    tot = mix.groupby("vendedor")["neto"].transform("sum")
    mix["peso"] = mix["neto"] / tot * 100

    fig2 = go.Figure()
    for canal, color in b2b.COLOR_CANAL.items():
        d = mix[mix["canal"] == canal]
        if d.empty:
            continue
        fig2.add_trace(go.Bar(x=d["vendedor"], y=d["peso"], name=canal,
                              marker_color=color,
                              hovertemplate="%{x} · " + canal + ": %{y:.0f}%<extra></extra>"))
    fig2.update_layout(barmode="stack")
    fig2.update_yaxes(title="% de su venta")
    st.plotly_chart(light(fig2, 300), width="stretch", theme=None, config=PLOTLY_CONFIG)
    st.caption(
        "La mezcla de canales de cada zona no la eligió el vendedor. En Medellín "
        "todavía no hay clubes sociales, que es el canal de mejor margen. "
        "Comparar cumplimiento sin corregir por esto castiga a quien abrió la "
        "ciudad — y es la queja que hunde cualquier esquema de comisión nuevo "
        "antes de que arranque.")
