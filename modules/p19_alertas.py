"""Alertas: lo que se disparó y qué pasó después.

Una lista de reglas no impresiona a nadie — cualquiera escribe reglas. Lo que
hace útil un módulo de alertas es la última columna: **qué cambió porque
alguien se enteró a tiempo.** Sin eso es otro informe, y KYVA ya tiene
informes.

Por eso la pantalla también muestra las alertas que NO se atendieron. Son las
que dicen cuánto cuesta el sistema actual, y son las que vuelven la
conversación concreta: no «le damos visibilidad» sino «estas cuatro se
ignoraron y una de ellas era un pedido perdido».
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.formatters import *
from utils import datos
from utils import operacion

TONO = {"Alta": "#8B1E1E", "Media": "#B5762F", "Baja": CLARO}
ICONO = {"Quiebre de stock": "📦", "Importación atrasada": "🚢",
         "Capital quieto": "🧊"}


def _fila(a):
    atendida = "Sin atender" not in a["desenlace"] and "Pendiente" not in a["desenlace"]
    color = TONO.get(a["gravedad"], CLARO)
    marca = ("✓" if atendida else "○")
    tono_des = "#2f7a48" if atendida else ACENTO
    return f"""
    <div style="border:1px solid {PALIDO};border-left:3px solid {color};
         border-radius:4px;padding:11px 15px;margin-bottom:8px;background:#fff">
      <div style="display:flex;justify-content:space-between;gap:12px;align-items:baseline">
        <div style="font-size:13.5px;font-weight:700;color:{TINTA}">
          {ICONO.get(a['tipo'], '•')}&nbsp; {a['que']}</div>
        <div style="font-size:10.5px;color:{CLARO};white-space:nowrap">
          {a['cuando']:%d %b}</div>
      </div>
      <div style="font-size:11px;color:{CLARO};margin:5px 0 0">
        <b style="color:{TINTA}">Regla:</b> {a['regla']} &nbsp;·&nbsp;
        <b style="color:{TINTA}">Avisa a:</b> {a['aviso']}</div>
      <div style="font-size:11.5px;color:{tono_des};font-weight:700;margin-top:4px">
        {marca} {a['desenlace']}</div>
    </div>"""


def render():
    st.markdown(HEADER_CSS, unsafe_allow_html=True)
    st.markdown(encabezado(
        "Alertas",
        "Lo que se salió de lo normal, a quién se le avisó y en qué terminó · últimos 45 días",
        "¿Qué necesita atención?"), unsafe_allow_html=True)

    ale = operacion.alertas()
    inv = operacion.inventario()
    r = operacion.resumen_operacion()

    sin_atender = ale["desenlace"].str.contains("Sin atender|Pendiente", case=False)
    altas = ale[ale["gravedad"] == "Alta"]

    k = st.columns(4, gap="small")
    k[0].markdown(kpi(
        "Alertas en 45 días", num(len(ale)),
        f"{len(altas)} de gravedad alta", True, "🔔",
        "Cada una es una regla que se cumplió sobre los datos reales."),
        unsafe_allow_html=True)
    k[1].markdown(kpi(
        "Se resolvieron", num(int((~sin_atender).sum())),
        pct((~sin_atender).mean() * 100, 0) + " de las que se dispararon",
        (~sin_atender).mean() > 0.75, "✓",
        "Alguien hizo algo: emitió la orden, trasladó, u ofreció el equivalente."),
        unsafe_allow_html=True)
    k[2].markdown(kpi(
        "Quedaron sin atender", num(int(sin_atender.sum())),
        "el costo de no tener quién mire", False, "○",
        "Aquí está el argumento: no es que falte el dato, es que falta quien reaccione."),
        unsafe_allow_html=True)
    quieto = float(inv.loc[inv["unidades_90d"] == 0, "valor_inventario"].sum())
    k[3].markdown(kpi(
        "Capital sin rotar", cop(quieto, 0),
        f"{pct(quieto / max(r['valor_inventario'], 1) * 100, 0)} del inventario", False, "🧊",
        "Referencias sin una sola venta en 90 días. Plata quieta en una bodega."),
        unsafe_allow_html=True)

    st.markdown(espacio(18), unsafe_allow_html=True)

    st.markdown(panel(
        "Por qué se muestran las que fallaron",
        f"De {len(ale)} alertas, <b>{int(sin_atender.sum())} se quedaron sin atender</b>. "
        f"Un panel que solo muestre las resueltas se ve mejor y sirve menos: lo que "
        f"convierte una alerta en valor no es que exista, es que alguien la reciba en "
        f"el canal donde trabaja y tenga claro qué hacer. Esa es la diferencia entre "
        f"esta pantalla y un reporte de excepciones del ERP, que también existe y que "
        f"tampoco abre nadie.",
        "○", "rojo"), unsafe_allow_html=True)

    st.markdown(espacio(6), unsafe_allow_html=True)

    # ── Las alertas ─────────────────────────────────────────────────────────
    c = st.columns([1, 1, 2])
    tipos = ["Todos"] + sorted(ale["tipo"].unique().tolist())
    tipo = c[0].selectbox("Tipo", tipos, key="al_tipo")
    solo = c[1].selectbox("Mostrar", ["Todas", "Solo sin atender", "Solo alta"], key="al_solo")

    sel = ale.copy()
    if tipo != "Todos":
        sel = sel[sel["tipo"] == tipo]
    if solo == "Solo sin atender":
        sel = sel[sel["desenlace"].str.contains("Sin atender|Pendiente", case=False)]
    elif solo == "Solo alta":
        sel = sel[sel["gravedad"] == "Alta"]

    if sel.empty:
        st.info("Nada con ese filtro.")
    else:
        for _, a in sel.iterrows():
            st.markdown(_fila(a), unsafe_allow_html=True)

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── Las reglas que están puestas ────────────────────────────────────────
    st.markdown('<div class="ky-sub">Las reglas que están corriendo</div>',
                unsafe_allow_html=True)
    reglas = (ale.groupby(["tipo", "regla", "aviso"])
              .agg(veces=("tipo", "size")).reset_index()
              .sort_values("veces", ascending=False))
    reglas.columns = ["Tipo", "Se dispara cuando", "Avisa a", "Veces en 45 días"]
    st.dataframe(reglas, hide_index=True, width="stretch")
    st.caption(
        "Los umbrales no son universales: se calibran con el cliente en las primeras "
        "semanas. Una regla que se dispara todos los días deja de leerse, y una que "
        "no se dispara nunca no está puesta — está decorando.")

    st.markdown(espacio(14), unsafe_allow_html=True)

    # ── Dónde llegan ────────────────────────────────────────────────────────
    st.markdown(panel(
        "Dónde llega cada alerta",
        "Una alerta que vive dentro de un panel espera a que alguien abra el panel, "
        "y eso la vuelve inútil justo cuando más sirve. Estas salen al canal donde "
        "la persona ya está: <b>correo</b> para lo de dirección, <b>WhatsApp</b> "
        "para compras y para los comerciales de cada ciudad, y una tarea en "
        "<b>Salesforce</b> cuando hay un cliente de por medio. El panel es donde se "
        "revisa después qué pasó, no donde uno se entera.",
        "📡", "azul"), unsafe_allow_html=True)
