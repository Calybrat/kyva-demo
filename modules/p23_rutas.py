"""Rutas y costo de servir: dónde se va la plata que el margen esconde.

En una distribuidora el margen bruto se decide una vez, al negociar la lista.
El costo de servir se decide **todos los días**, sin que nadie lo note: cada vez
que un vendedor promete entrega para mañana, cada vez que un bar pide medio
pedido dos veces en la semana, cada vez que hay que cruzar la ciudad por una
sola caja.

La aritmética que manda es una sola: **una entrega cuesta casi lo mismo lleve
cuatro botellas o cuarenta.** De ahí salen las tres cosas que esta pantalla
busca:

  · Zonas donde el costo por entrega se dispara porque hay pocas cuentas.
  · Cuentas con ticket por entrega tan bajo que ningún margen las cubre.
  · Días de la semana donde se concentra —o no— el reparto.

Y la palanca: **agrupar por zona y día**. No es un ahorro teórico; es la
diferencia entre seis paradas en una mañana en la Zona G y seis viajes a
Envigado en seis días distintos.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.formatters import *
from utils import b2b


def render():
    st.markdown(HEADER_CSS, unsafe_allow_html=True)
    st.markdown(encabezado(
        "Rutas y costo de servir",
        "Cuánto cuesta cada entrega, por zona y por cuenta · último trimestre",
        "¿Llegamos a tiempo?"), unsafe_allow_html=True)

    r = b2b.rentabilidad()
    e = b2b.entregas()
    res = b2b.resumen_b2b()

    zonas = r.groupby(["ciudad", "zona"]).agg(
        cuentas=("cuenta_id", "size"), neto=("neto", "sum"),
        entregas=("entregas", "sum"), logistica=("logistica", "sum"),
        margen=("margen", "sum"), servido=("servido", "sum")).reset_index()
    zonas["costo_entrega"] = zonas["logistica"] / zonas["entregas"].clip(lower=1)
    zonas["ticket"] = zonas["neto"] / zonas["entregas"].clip(lower=1)
    zonas["carga_pct"] = zonas["logistica"] / zonas["neto"] * 100
    zonas = zonas.sort_values("carga_pct", ascending=False)

    total_log = float(r["logistica"].sum())
    total_neto = float(r["neto"].sum())
    peor = zonas.iloc[0]

    k = st.columns(4, gap="small")
    k[0].markdown(kpi(
        "Costo de servir", cop(total_log, 0),
        f"{pct(total_log / total_neto * 100)} de la venta", False, "🚚",
        "Lo que cuesta llevar la mercancía, en el trimestre."),
        unsafe_allow_html=True)
    k[1].markdown(kpi(
        "Entregas", num(int(r["entregas"].sum())),
        f"{cop(total_log / max(r['entregas'].sum(), 1), 0)} cada una", True, "📍",
        "Cada parada cuesta casi lo mismo lleve poco o mucho."),
        unsafe_allow_html=True)
    k[2].markdown(kpi(
        "La zona más cara", peor["zona"],
        f"{pct(peor['carga_pct'])} de su venta se va en repartir", False, "📌",
        f"{int(peor['cuentas'])} cuentas en {peor['ciudad']}. "
        f"Pocas cuentas dispersas cuestan más por parada."),
        unsafe_allow_html=True)
    ahorro = _ahorro_agrupando(zonas)
    k[3].markdown(kpi(
        "Si se agrupa por zona y día", cop(ahorro, 0),
        "al año, sin tocar el precio", True, "🗓️",
        "Consolidar visitas de la misma zona en un día. La palanca más grande "
        "y la que el cliente menos siente."), unsafe_allow_html=True)

    st.markdown(espacio(18), unsafe_allow_html=True)

    # ── Mapa de zonas: densidad contra costo ────────────────────────────────
    st.markdown('<div class="ky-sub">Por qué unas zonas cuestan el doble</div>',
                unsafe_allow_html=True)
    fig = go.Figure()
    for ciudad, color in (("Bogotá", PRIMARIO), ("Medellín", ACENTO)):
        d = zonas[zonas["ciudad"] == ciudad]
        if d.empty:
            continue
        fig.add_trace(go.Scatter(
            x=d["cuentas"], y=d["costo_entrega"], mode="markers+text",
            name=ciudad, text=d["zona"], textposition="top center",
            textfont=dict(size=9, color=CLARO),
            marker=dict(size=np.clip(d["entregas"] / 2.2, 10, 40), color=color,
                        opacity=.75, line=dict(width=1, color="#fff")),
            customdata=np.stack([d["entregas"], d["ticket"], d["carga_pct"]], -1),
            hovertemplate="<b>%{text}</b><br>%{x} cuentas · %{customdata[0]:.0f} entregas"
                          "<br>Costo por entrega: %{y:,.0f}"
                          "<br>Ticket por entrega: %{customdata[1]:,.0f}"
                          "<br>Se lleva el %{customdata[2]:.1f}% de la venta<extra></extra>"))
    fig.update_xaxes(title="Cuentas en la zona")
    fig.update_yaxes(title="Costo por entrega (COP)")
    st.plotly_chart(light(fig, 400), use_container_width=True)
    st.caption(
        "La relación es la que uno esperaría y casi nadie cuantifica: **entre más "
        "cuentas hay en una zona, más barato sale cada parada**, porque el "
        "recorrido se reparte. Una zona con dos cuentas paga el viaje completo dos "
        "veces. Eso decide dónde conviene abrir la próxima cuenta, y hoy esa "
        "decisión se toma por dónde apareció el cliente.")

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── La tabla de zonas ───────────────────────────────────────────────────
    t = zonas.copy()
    t["semaforo"] = np.where(t["carga_pct"] > 6, "🔴",
                             np.where(t["carga_pct"] > 3.5, "🟠", "🟢"))
    v = t[["semaforo", "ciudad", "zona", "cuentas", "entregas", "neto",
           "ticket", "costo_entrega", "logistica", "carga_pct"]].copy()
    for c in ("neto", "ticket", "costo_entrega", "logistica"):
        v[c] = v[c].map(lambda x: cop(x, 0))
    v["carga_pct"] = t["carga_pct"].map(lambda x: pct(x))
    v["entregas"] = t["entregas"].astype(int)
    v.columns = ["", "Ciudad", "Zona", "Cuentas", "Entregas", "Venta neta",
                 "Ticket/entrega", "Costo/entrega", "Costo total", "% de la venta"]
    st.dataframe(v, hide_index=True, width="stretch")

    st.markdown(espacio(14), unsafe_allow_html=True)

    # ── Las cuentas que no pagan el viaje ───────────────────────────────────
    st.markdown('<div class="ky-sub">Las cuentas que no pagan el viaje</div>',
                unsafe_allow_html=True)
    malas = r[r["ticket_entrega"] < r["costo_por_entrega"] * 8].nsmallest(12, "ticket_entrega")
    if malas.empty:
        st.success("Todas las cuentas mueven al menos ocho veces el costo de su entrega.")
    else:
        m = malas[["nombre", "canal", "ciudad", "zona", "entregas", "ticket_entrega",
                   "costo_por_entrega", "servido_pct"]].copy()
        m["veces"] = (malas["ticket_entrega"] / malas["costo_por_entrega"]).round(1)
        for c in ("ticket_entrega", "costo_por_entrega"):
            m[c] = m[c].map(lambda x: cop(x, 0))
        m["servido_pct"] = malas["servido_pct"].map(lambda x: pct(x))
        m["entregas"] = malas["entregas"].astype(int)
        m.columns = ["Cuenta", "Canal", "Ciudad", "Zona", "Entregas",
                     "Valor por entrega", "Costo de la entrega", "Margen servido", "Veces"]
        st.dataframe(m, hide_index=True, width="stretch")
        st.caption(
            "«Veces» es cuántas veces el valor de la entrega cubre su costo. "
            "**Por debajo de 8 no alcanza** para pagar el costo de la mercancía "
            "más el reparto. La solución casi nunca es dejar la cuenta: es subir "
            "el pedido mínimo o bajar la frecuencia.")

    st.markdown(espacio(14), unsafe_allow_html=True)
    st.markdown(panel(
        "La regla que resuelve la mayoría de estos casos",
        f"Un pedido mínimo igual a <b>ocho veces el costo de la entrega</b> "
        f"—hoy serían unos {cop(r['costo_por_entrega'].mean() * 8, 0)}— hace que "
        f"cada viaje se pague solo sin tocar precios ni descuentos. "
        f"Es una sola regla, se aplica en el sistema de pedidos, y no obliga a "
        f"ninguna conversación incómoda con el cliente: el que quiera menos, "
        f"espera al siguiente despacho de su zona.",
        "📏", "azul"), unsafe_allow_html=True)


def _ahorro_agrupando(zonas: pd.DataFrame) -> float:
    """Cuánto se ahorra si cada zona se visita en días consolidados.

    El supuesto es conservador y conviene decirlo: se asume que agrupar reduce
    el costo por parada hasta el de la zona más densa de esa ciudad, con un tope
    del 30%. Es lo que gana la ruta al no tener que rehacer el recorrido — no
    incluye ahorros de personal, que dependen de decisiones que no son nuestras.
    """
    total = 0.0
    for ciudad in zonas["ciudad"].unique():
        d = zonas[zonas["ciudad"] == ciudad]
        piso = float(d["costo_entrega"].min())
        for _, z in d.iterrows():
            mejora = min(z["costo_entrega"] - piso, z["costo_entrega"] * 0.30)
            total += max(mejora, 0) * z["entregas"]
    return total * 4          # el trimestre, anualizado
