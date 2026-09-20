"""Reposición y compras: qué pedir, cuánto y —sobre todo— antes de cuándo.

El hallazgo que ordena la pantalla no es que falte inventario. Es que **la
ventana de decisión de la compra de diciembre se está cerrando ahora mismo, y
se cierra en fechas distintas para cada categoría**.

Un whisky escocés tarda 69 días entre la orden y la bodega. Para tenerlo el 1
de diciembre hay que pedirlo a mediados de septiembre. Una cerveza nacional se
puede pedir el 20 de noviembre y llega. Hoy esa cuenta no la hace nadie
referencia por referencia, y el costo de equivocarse no se ve en agosto: se ve
el 15 de diciembre, cuando el producto que más deja margen se agotó.

Dos cosas que este módulo hace y una lista de faltantes no:

  · **Descuenta lo que ya viene en camino.** Sin eso el panel recomienda
    comprar 60 unidades que están en el barco. Comprar dos veces lo mismo es
    el error caro de un MRP mal hecho.
  · **Respeta el pedido mínimo del proveedor.** Si el importador exige 60 y
    faltan 12, la decisión real no es «pedir 12»: es esperar o inmovilizar
    capital. Eso se dice, no se esconde.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.formatters import *
from utils import datos
from utils import operacion

ORDEN_URGENCIA = ["Ventana cerrada", "Pedir esta semana", "Pedir este mes", "Hay tiempo"]
COLOR_URGENCIA = {"Ventana cerrada": "#8B1E1E", "Pedir esta semana": ACENTO,
                  "Pedir este mes": "#B5762F", "Hay tiempo": "#2f7a48"}


def render():
    st.markdown(HEADER_CSS, unsafe_allow_html=True)
    st.markdown(encabezado(
        "Reposición y compras",
        "Qué pedir para la temporada, cuánto, y la fecha límite de cada referencia · corte 31 de agosto",
        "¿Qué hay que comprar?"), unsafe_allow_html=True)

    inv = operacion.inventario()
    oc = operacion.ordenes_compra()
    prov = operacion.proveedores()
    r = operacion.resumen_operacion()
    falt = r["faltantes"]

    rota = inv[inv["demanda_dia"] > 0]
    urge = rota[rota["urgencia"].isin(["Ventana cerrada", "Pedir esta semana"])]

    k = st.columns(4, gap="small")
    k[0].markdown(kpi(
        "Compra de temporada", cop(r["compra_diciembre"], 0),
        "neto de lo que ya viene en camino", True, "🎄",
        "Lo que falta para aguantar seis semanas de pico, descontando el tránsito.",
        "Noviembre y diciembre valen 2,6× un mes normal"), unsafe_allow_html=True)
    k[1].markdown(kpi(
        "Hay que pedirlas esta semana", num(len(urge)),
        f"{cop(urge['valor_faltante'].sum(), 0)} en juego", False, "⏰",
        "Su plazo de reposición ya no cabe antes del 1 de diciembre."),
        unsafe_allow_html=True)
    k[2].markdown(kpi(
        "En tránsito hoy", cop(r["en_transito_valor"], 0),
        f"{r['ordenes_atrasadas']} órdenes con la fecha vencida",
        r["ordenes_atrasadas"] == 0, "🚢",
        "Mercancía comprada que todavía no llega. Se descuenta de lo que hay que pedir."),
        unsafe_allow_html=True)
    k[3].markdown(kpi(
        "Capital en bodega", cop(r["valor_inventario"], 0),
        f"{num(r['referencias_activas'])} referencias con rotación", True, "🏬",
        "Valor al costo de las dos bodegas."), unsafe_allow_html=True)

    st.markdown(espacio(18), unsafe_allow_html=True)

    # ── La ventana, por categoría ───────────────────────────────────────────
    st.markdown('<div class="ky-sub">Hasta cuándo se puede pedir cada cosa</div>',
                unsafe_allow_html=True)

    cat = (rota.groupby("categoria")
           .agg(plazo=("dias_reposicion", "mean"),
                limite=("fecha_limite_pedido", "min"),
                falta=("valor_faltante", "sum"),
                refs=("sku", "nunique"),
                nacional=("nacional", "max"))
           .reset_index().sort_values("plazo", ascending=True))
    cat["dias"] = (cat["limite"] - datos.CORTE.normalize()).dt.days

    fig = go.Figure(go.Bar(
        y=cat["categoria"], x=cat["dias"], orientation="h",
        marker_color=[("#2f7a48" if d > 60 else "#B5762F" if d > 21
                       else ACENTO if d > 0 else "#8B1E1E") for d in cat["dias"]],
        text=[f"{d} días" if d > 0 else "vencida" for d in cat["dias"]],
        textposition="outside", textfont=dict(size=10),
        customdata=np.stack([cat["plazo"].round(0), cat["refs"], cat["falta"] / 1e6], -1),
        hovertemplate="<b>%{y}</b><br>Plazo de reposición: %{customdata[0]:.0f} días<br>"
                      "%{customdata[1]} referencias<br>"
                      "Faltante para el pico: %{customdata[2]:,.0f} M<extra></extra>"))
    fig.update_xaxes(title="Días que quedan para poder pedir y que llegue antes del 1 de diciembre")
    st.plotly_chart(light(fig, 400), width="stretch", theme=None, config=PLOTLY_CONFIG)

    cerradas = cat[cat["dias"] <= 0]
    esta_sem = cat[(cat["dias"] > 0) & (cat["dias"] <= 21)]
    if len(cerradas) or len(esta_sem):
        nombres = ", ".join(cerradas["categoria"].tolist() + esta_sem["categoria"].tolist())
        plata = cat[cat["dias"] <= 21]["falta"].sum()
        st.markdown(panel(
            "La conversación que hay que tener esta semana",
            f"<b>{nombres}</b> son las categorías cuya ventana se cierra dentro de "
            f"tres semanas o ya se cerró. Entre todas hay <b>{cop(plata, 0)}</b> de "
            f"faltante para la temporada. No es que el inventario esté mal: es que "
            f"el plazo de importación no cabe si la decisión se toma en octubre, "
            f"como se toma normalmente.",
            "⏰", "rojo"), unsafe_allow_html=True)

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── La orden sugerida ───────────────────────────────────────────────────
    st.markdown('<div class="ky-sub">Orden sugerida</div>', unsafe_allow_html=True)
    c = st.columns([1, 1, 2])
    bod = c[0].selectbox("Bodega", ["Las dos", "Bogotá", "Medellín"], key="rp_bod")
    urgencias = [u for u in ORDEN_URGENCIA if u in rota["urgencia"].unique()]
    urg = c[1].selectbox("Urgencia", ["Todas"] + urgencias, key="rp_urg")

    sug = falt[falt["faltante_neto"] > 0].copy()
    if bod != "Las dos":
        sug = sug[sug["bodega"] == bod]
    if urg != "Todas":
        sug = sug[sug["urgencia"] == urg]
    sug = sug.sort_values(["dias_para_limite", "valor_neto"], ascending=[True, False])

    if sug.empty:
        st.info("Nada por pedir con ese filtro.")
    else:
        # El pedido mínimo del proveedor decide cuánto se pide de verdad.
        minimos = prov.set_index("proveedor")["pedido_minimo_u"].to_dict()
        sug["minimo"] = sug["proveedor"].map(minimos).fillna(24).astype(int)
        sug["a_pedir"] = np.maximum(sug["faltante_neto"], sug["minimo"])
        sug["sobra_por_minimo"] = sug["a_pedir"] - sug["faltante_neto"]
        sug["costo_orden"] = sug["a_pedir"] * sug["costo_unit"]

        exceso = sug[sug["sobra_por_minimo"] > 0]
        if len(exceso):
            st.caption(md(
                f"⚠ En {len(exceso)} referencias el pedido mínimo del proveedor obliga a "
                f"comprar más de lo que falta: {cop((exceso['sobra_por_minimo'] * exceso['costo_unit']).sum(), 0)} "
                f"de capital adicional inmovilizado. No es un error del cálculo — es la "
                f"decisión real que hay que tomar con cada importador."))

        t = sug.head(30)[["nombre", "categoria", "bodega", "unidades", "en_transito",
                          "faltante_neto", "minimo", "a_pedir", "costo_orden",
                          "fecha_limite_pedido", "urgencia"]].copy()
        t["fecha_limite_pedido"] = t["fecha_limite_pedido"].dt.strftime("%d %b")
        t["costo_orden"] = t["costo_orden"].map(lambda v: cop(v, 0))
        t.columns = ["Referencia", "Categoría", "Bodega", "En bodega", "En camino",
                     "Falta", "Mín. proveedor", "Pedir", "Costo", "Pedir antes de", "Urgencia"]
        st.dataframe(t, hide_index=True, width="stretch")
        st.caption(md(
            f"{len(sug)} referencias por pedir · {cop(sug['costo_orden'].sum(), 0)} en total. "
            f"«En camino» ya está descontado de «Falta»."))

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── Proveedores: quién cumple ───────────────────────────────────────────
    st.markdown('<div class="ky-sub">Con quién se está comprando</div>',
                unsafe_allow_html=True)
    atrasos = (oc[oc["dias_atraso"] > 0].groupby("proveedor")
               .agg(ordenes_tarde=("orden", "size"),
                    dias_promedio=("dias_atraso", "mean")).reset_index())
    p = prov.merge(atrasos, on="proveedor", how="left")
    p["ordenes_tarde"] = p["ordenes_tarde"].fillna(0).astype(int)
    p["dias_promedio"] = p["dias_promedio"].fillna(0).round(0).astype(int)

    t = p[["proveedor", "referencias", "valor_inventario", "dias_reposicion",
           "pedido_minimo_u", "cumplimiento_pct", "ordenes_tarde", "dias_promedio"]].copy()
    t["valor_inventario"] = t["valor_inventario"].map(lambda v: cop(v, 0))
    t.columns = ["Proveedor", "Referencias", "Inventario", "Plazo (días)",
                 "Pedido mínimo", "Cumplimiento", "Órdenes tarde", "Días de atraso"]
    st.dataframe(t, hide_index=True, width="stretch")

    peor = p.sort_values("cumplimiento_pct").iloc[0]
    st.caption(md(
        f"**{peor['proveedor']}** cumple el {peor['cumplimiento_pct']:.0f}% de sus fechas "
        f"y tiene {cop(peor['valor_inventario'], 0)} del inventario. Con un proveedor así "
        f"la respuesta no es comprarle más cantidad: es pedirle antes, porque el "
        f"riesgo no es el precio, es la fecha."))
