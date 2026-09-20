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
    por_margen = g.sort_values("servido", ascending=False)["vendedor"].tolist()
    invertidos = [x for x in por_venta if por_venta.index(x) != por_margen.index(x)]

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
        "Cambian de puesto", num(len(invertidos)),
        "al ordenar por margen en vez de venta", len(invertidos) == 0, "🔄",
        "Los que el informe de ventas premia o castiga al revés.",
        "Es el costo del incentivo, medido"), unsafe_allow_html=True)

    st.markdown(espacio(18), unsafe_allow_html=True)

    # ── El vuelco del ranking ───────────────────────────────────────────────
    st.markdown('<div class="ky-sub">El ranking se voltea</div>', unsafe_allow_html=True)
    izq = g.sort_values("neto", ascending=True)
    der = g.sort_values("servido", ascending=True)

    fig = go.Figure()
    fig.add_trace(go.Bar(y=izq["vendedor"], x=izq["neto"], orientation="h",
                         name="Venta neta", marker_color=PALIDO,
                         hovertemplate="%{y}<br>Venta: %{x:,.0f}<extra></extra>"))
    fig.add_trace(go.Bar(y=der["vendedor"], x=der["servido"] * 4, orientation="h",
                         name="Margen servido (×4 para verlo)",
                         marker_color=PRIMARIO,
                         customdata=der["servido"],
                         hovertemplate="%{y}<br>Margen servido: %{customdata:,.0f}<extra></extra>"))
    fig.update_layout(barmode="group")
    st.plotly_chart(light(fig, 300, moneda=True), use_container_width=True)

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
    esquema = c[0].selectbox("Esquema", list(ESQUEMAS), key="eq_esq")
    cfg = ESQUEMAS[esquema]
    tasa = c[1].slider("Tasa (%)", 0.5, 12.0, float(cfg["tasa"] * 100), 0.1,
                       key="eq_tasa") / 100

    sim = g.copy()
    sim["com_hoy"] = sim["neto"] * ESQUEMAS["Sobre venta (el de hoy)"]["tasa"]
    sim["com_nueva"] = sim[cfg["base"]] * tasa
    sim["delta"] = sim["com_nueva"] - sim["com_hoy"]
    sim = sim.sort_values("servido", ascending=False)

    t = sim[["vendedor", "ciudad", "estilo", "cuentas", "neto", "desc_pct",
             "servido_pct", "servido", "com_hoy", "com_nueva", "delta"]].copy()
    for col in ("neto", "servido", "com_hoy", "com_nueva", "delta"):
        t[col] = t[col].map(lambda x: cop(x, 0))
    for col in ("desc_pct", "servido_pct"):
        t[col] = t[col].map(lambda x: pct(x))
    t.columns = ["Vendedor", "Ciudad", "Estilo", "Cuentas", "Venta neta", "Descuento",
                 "Margen servido %", "Margen servido", "Comisión hoy",
                 "Comisión nueva", "Diferencia"]
    st.dataframe(t, hide_index=True, width="stretch")

    costo_hoy = sim["com_hoy"].sum()
    costo_nuevo = sim["com_nueva"].sum()
    st.caption(
        f"Costo total de comisiones: **{cop(costo_hoy, 0)}** hoy contra "
        f"**{cop(costo_nuevo, 0)}** con este esquema. "
        f"La tasa se puede calibrar para que el costo total no cambie —lo que "
        f"cambia es **quién cobra qué**— y esa es la única forma de que el equipo "
        f"acepte la conversación.")

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
    st.plotly_chart(light(fig2, 300), use_container_width=True)
    st.caption(
        "La mezcla de canales de cada zona no la eligió el vendedor. En Medellín "
        "todavía no hay clubes sociales, que es el canal de mejor margen. "
        "Comparar cumplimiento sin corregir por esto castiga a quien abrió la "
        "ciudad — y es la queja que hunde cualquier esquema de comisión nuevo "
        "antes de que arranque.")
