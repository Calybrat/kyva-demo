"""Simulador: mover una palanca y ver el efecto antes de tomarla.

Un panel contesta «qué pasó». Un gerente necesita «qué pasa si». La diferencia
entre las dos preguntas es la diferencia entre revisar y decidir.

Las cinco palancas de abajo no son genéricas: son las que un distribuidor de
licores mueve de verdad, y cada una tiene un efecto secundario que la hace
incómoda. Ese efecto secundario es lo importante — subir el pedido mínimo
mejora el margen y **cuesta cuentas**, y un simulador que solo muestre la mejora
está mintiendo.

Por eso cada palanca aquí declara su costo: cuentas que se pierden, volumen que
se cae, capital que se inmoviliza. Un escenario sin contrapartida es una
presentación de ventas, no una herramienta de decisión.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.formatters import *
from utils import b2b

# Elasticidades. Son supuestos, y la pantalla lo dice: sin datos de un cambio
# real solo se puede acotar el orden de magnitud. Lo honesto es dejarlas
# visibles y editables, no esconderlas dentro del cálculo.
ELASTICIDAD_PRECIO = -1.15      # 1% más caro → 1,15% menos volumen
FUGA_POR_MINIMO = 0.38          # fracción de cuentas bajo el mínimo que se van


def render():
    st.markdown(HEADER_CSS, unsafe_allow_html=True)
    st.markdown(encabezado(
        "Simulador",
        "Mover una palanca y ver el efecto —y la contrapartida— antes de tomarla",
        "¿Qué pasa si…?"), unsafe_allow_html=True)

    r = b2b.rentabilidad().copy()
    base_neto = float(r["neto"].sum())
    base_margen = float(r["margen"].sum())
    base_log = float(r["logistica"].sum())
    base_servido = base_margen - base_log

    st.markdown(panel(
        "Cómo leer esto",
        "Todo se calcula sobre el <b>último trimestre real</b> y se muestra "
        "anualizado. Cada palanca trae su contrapartida a la vista: no existe "
        "subir el margen sin perder algo. Un simulador que solo enseñe la mejora "
        "es una presentación de ventas.",
        "🎛️", "azul"), unsafe_allow_html=True)

    st.markdown(espacio(10), unsafe_allow_html=True)

    c = st.columns(2, gap="large")
    with c[0]:
        st.markdown('<div class="ky-sub">Las palancas</div>', unsafe_allow_html=True)
        desc_baja = st.slider(
            "Bajar el descuento promedio (puntos)", 0.0, 6.0, 0.0, 0.5, key="sim_desc",
            help="Sube el margen de inmediato. Cuesta discusiones y algunas cuentas.")
        minimo = st.slider(
            "Pedido mínimo por entrega (millones)", 0.0, 6.0, 0.0, 0.25, key="sim_min",
            help="La palanca más grande sobre el costo de servir. Se pierden las "
                 "cuentas chicas que no alcanzan.")
        frec = st.slider(
            "Reducir frecuencia de entrega (%)", 0, 45, 0, 5, key="sim_frec",
            help="Agrupar por zona y día. No toca el precio.")
        precio = st.slider(
            "Subir la lista (%)", 0.0, 6.0, 0.0, 0.5, key="sim_precio",
            help=f"Con elasticidad {ELASTICIDAD_PRECIO}: cada punto de precio "
                 f"cuesta {abs(ELASTICIDAD_PRECIO):.2f} puntos de volumen.")
        cerrar = st.checkbox(
            "Soltar las cuentas que cuestan plata", key="sim_cerrar",
            help="Dejar de atender las que dan margen servido negativo.")

    # ── El cálculo ──────────────────────────────────────────────────────────
    s = r.copy()
    perdidas, motivo = [], {}

    if cerrar:
        fuera = s[s["servido"] < 0]
        perdidas += fuera["nombre"].tolist()
        for n in fuera["nombre"]:
            motivo[n] = "soltada por margen negativo"
        s = s[s["servido"] >= 0]

    if minimo > 0:
        umbral = minimo * 1e6
        bajo = s[s["ticket_entrega"] < umbral]
        n_fuera = int(round(len(bajo) * FUGA_POR_MINIMO))
        if n_fuera:
            fuera = bajo.nsmallest(n_fuera, "ticket_entrega")
            perdidas += fuera["nombre"].tolist()
            for n in fuera["nombre"]:
                motivo[n] = f"no alcanza el mínimo de {cop(umbral, 0)}"
            s = s[~s["cuenta_id"].isin(fuera["cuenta_id"])]
        # Las que se quedan consolidan pedidos: menos entregas, mismo valor
        sube = s["ticket_entrega"] < umbral
        s.loc[sube, "entregas"] = np.ceil(
            s.loc[sube, "neto"] / umbral).clip(lower=1)
        s["logistica"] = s["entregas"] * s["costo_por_entrega"]

    if frec > 0:
        s["entregas"] = np.ceil(s["entregas"] * (1 - frec / 100)).clip(lower=1)
        s["logistica"] = s["entregas"] * s["costo_por_entrega"]

    if desc_baja > 0:
        # Menos descuento entra directo al margen; una parte del volumen se va.
        gana = s["bruto"] * (desc_baja / 100)
        fuga = s["neto"] * (desc_baja / 100) * 0.35
        s["margen"] = s["margen"] + gana - fuga * 0.75
        s["neto"] = s["neto"] - fuga

    if precio > 0:
        vol = 1 + ELASTICIDAD_PRECIO * (precio / 100)
        s["neto"] = s["neto"] * (1 + precio / 100) * vol
        s["margen"] = s["margen"] * (1 + precio / 100 * 2.6) * vol

    s["servido"] = s["margen"] - s["logistica"]
    n_neto, n_margen, n_log = s["neto"].sum(), s["margen"].sum(), s["logistica"].sum()
    n_servido = n_margen - n_log

    with c[1]:
        st.markdown('<div class="ky-sub">El resultado, anualizado</div>',
                    unsafe_allow_html=True)
        filas = [
            ("Venta neta", base_neto * 4, n_neto * 4),
            ("Margen bruto", base_margen * 4, n_margen * 4),
            ("Costo de servir", -base_log * 4, -n_log * 4),
            ("Margen después de servir", base_servido * 4, n_servido * 4),
        ]
        cuerpo = ""
        for nombre, antes, despues in filas:
            d = despues - antes
            col = "#2f7a48" if d > 0 else ("#8B1E1E" if d < 0 else CLARO)
            flecha = "▲" if d > 0 else ("▼" if d < 0 else "—")
            fuerte = "font-weight:800;" if "después" in nombre else ""
            cuerpo += (
                f'<tr style="border-bottom:1px solid {PALIDO}">'
                f'<td style="padding:9px 0;font-size:12.5px;color:{TINTA};{fuerte}">{nombre}</td>'
                f'<td style="padding:9px 0;font-size:12px;color:{CLARO};text-align:right">'
                f'{cop(antes, 0)}</td>'
                f'<td style="padding:9px 8px;font-size:13px;color:{TINTA};text-align:right;'
                f'{fuerte}">{cop(despues, 0)}</td>'
                f'<td style="padding:9px 0;font-size:12px;color:{col};text-align:right;'
                f'font-weight:700;white-space:nowrap">{flecha} {cop(abs(d), 0)}</td></tr>')
        st.markdown(
            f'<table style="width:100%;border-collapse:collapse">'
            f'<tr><th style="text-align:left;font-size:9.5px;letter-spacing:.12em;'
            f'text-transform:uppercase;color:{CLARO};padding-bottom:6px"></th>'
            f'<th style="text-align:right;font-size:9.5px;letter-spacing:.12em;'
            f'text-transform:uppercase;color:{CLARO}">Hoy</th>'
            f'<th style="text-align:right;font-size:9.5px;letter-spacing:.12em;'
            f'text-transform:uppercase;color:{CLARO};padding-right:8px">Escenario</th>'
            f'<th style="text-align:right;font-size:9.5px;letter-spacing:.12em;'
            f'text-transform:uppercase;color:{CLARO}">Δ</th></tr>{cuerpo}</table>',
            unsafe_allow_html=True)

        delta = (n_servido - base_servido) * 4
        pct_delta = (n_servido / max(base_servido, 1) - 1) * 100
        st.markdown(espacio(14), unsafe_allow_html=True)
        st.markdown(
            f'<div style="background:{PRIMARIO};color:#fff;border-radius:7px;'
            f'padding:18px 22px;text-align:center">'
            f'<div style="font-size:10px;letter-spacing:.16em;text-transform:uppercase;'
            f'opacity:.7;font-family:Montserrat,sans-serif">Efecto anual</div>'
            f'<div style="font-family:\'DM Serif Display\',Georgia,serif;font-size:36px;'
            f'line-height:1.1;margin:4px 0">{cop(delta, 0)}</div>'
            f'<div style="font-size:12px;opacity:.75">{signo(pct_delta)} sobre el margen '
            f'después de servir</div></div>', unsafe_allow_html=True)

        if perdidas:
            venta_perdida = float(r[r["nombre"].isin(perdidas)]["neto"].sum()) * 4
            st.markdown(espacio(12), unsafe_allow_html=True)
            st.markdown(
                f'<div style="border:1px solid {ACENTO};border-radius:6px;padding:12px 16px;'
                f'background:{ACENTO_LT}55">'
                f'<div style="font-size:11px;font-weight:800;letter-spacing:.1em;'
                f'text-transform:uppercase;color:{ACENTO}">La contrapartida</div>'
                f'<div style="font-size:13px;color:{TINTA};margin-top:5px">'
                f'<b>{len(perdidas)} cuentas</b> se pierden · '
                f'{cop(venta_perdida, 0)} de venta anual</div></div>',
                unsafe_allow_html=True)

    st.markdown(espacio(18), unsafe_allow_html=True)

    # ── De dónde sale la diferencia ─────────────────────────────────────────
    st.markdown('<div class="ky-sub">De dónde sale la diferencia</div>',
                unsafe_allow_html=True)
    efectos = [
        ("Hoy", base_servido * 4, "absolute"),
        ("Menos descuento", (n_margen - base_margen) * 4 if desc_baja or precio else 0, "relative"),
        ("Menos costo de servir", (base_log - n_log) * 4, "relative"),
        ("Cuentas perdidas", -abs(float(r[r["nombre"].isin(perdidas)]["servido"].sum())) * 4
         if perdidas else 0, "relative"),
    ]
    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=[e[2] for e in efectos] + ["total"],
        x=[e[0] for e in efectos] + ["Escenario"],
        y=[e[1] for e in efectos] + [0],
        text=[cop(abs(e[1]), 0) for e in efectos] + [cop(n_servido * 4, 0)],
        textposition="outside", textfont=dict(size=10),
        connector=dict(line=dict(color=PALIDO, width=1)),
        increasing=dict(marker=dict(color="#2f7a48")),
        decreasing=dict(marker=dict(color=ACENTO)),
        totals=dict(marker=dict(color=PRIMARIO))))
    st.plotly_chart(light(fig, 340, moneda=True), width="stretch", theme=None, config=PLOTLY_CONFIG)

    if perdidas:
        st.markdown('<div class="ky-sub">Qué cuentas se van y por qué</div>',
                    unsafe_allow_html=True)
        p = r[r["nombre"].isin(perdidas)][
            ["nombre", "canal", "ciudad", "neto", "entregas",
             "ticket_entrega", "servido_pct"]].copy()
        p["motivo"] = p["nombre"].map(motivo)
        for col in ("neto", "ticket_entrega"):
            p[col] = p[col].map(lambda x: cop(x, 0))
        p["servido_pct"] = r[r["nombre"].isin(perdidas)]["servido_pct"].map(lambda x: pct(x))
        p["entregas"] = r[r["nombre"].isin(perdidas)]["entregas"].astype(int)
        p.columns = ["Cuenta", "Canal", "Ciudad", "Venta trimestre", "Entregas",
                     "Valor por entrega", "Margen servido", "Por qué se pierde"]
        st.dataframe(p, hide_index=True, width="stretch")

    st.markdown(espacio(14), unsafe_allow_html=True)
    st.markdown(panel(
        "Los supuestos, a la vista",
        f"<b>Elasticidad de precio {ELASTICIDAD_PRECIO}</b>: cada punto que sube la "
        f"lista cuesta {abs(ELASTICIDAD_PRECIO):.2f} puntos de volumen. "
        f"<b>Fuga por pedido mínimo {FUGA_POR_MINIMO*100:.0f}%</b>: de las cuentas "
        f"que quedan por debajo del mínimo, esa fracción se va en vez de "
        f"consolidar.<br><br>"
        f"Los dos son supuestos y hay que decirlo: sin haber hecho el cambio no se "
        f"puede saber, solo acotar el orden de magnitud. La forma de volverlos "
        f"datos es <b>probar con un canal durante un trimestre</b> y medir. "
        f"Un simulador que esconde sus supuestos dentro del cálculo es un truco.",
        "📐", "rojo"), unsafe_allow_html=True)
