"""Marcas: cuota, bonificación y rebate. Donde está la utilidad de verdad.

De la revisión adversaria, y es el hueco más caro que tenía el panel:

    «Soy distribuidor exclusivo de Mil Demonios. Eso significa un compromiso de
    sell-in firmado: tantas cajas al trimestre, o me quitan la exclusiva o
    pierdo el rebate de fin de año. Esa plata es, en muchos meses, toda mi
    utilidad. El panel no lo sabe.»

Tres mecánicas que esta pantalla hace visibles y que hoy no las mira nadie:

**1. El rebate es escalonado.** No se gana por vender más: se gana por *cruzar
un umbral*. Estar en 97% a quince días del cierre y no darse cuenta cuesta el
tramo entero, y el tramo casi siempre vale más que el margen de esas unidades.

**2. La bonificación es descuento invisible.** Las botellas que se regalan para
cerrar un pedido no aparecen en ninguna lista de precios, no bajan el precio
unitario en ningún reporte, y se comen el margen del año sin que nadie las
sume.

**3. El contador corre contra el calendario.** Un trimestre no se recupera en
la última semana si el producto tarda sesenta días en llegar. Por eso la
pantalla muestra días restantes, no solo porcentaje.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.formatters import *
from utils import gerencia

TRIMESTRE_ACTUAL = "2026-T3"
# Agosto 31 es el corte; el trimestre cierra el 30 de septiembre.
DIAS_RESTANTES = 30


def _semaforo(c):
    return "#2f7a48" if c >= 100 else ("#B5762F" if c >= 90 else ACENTO)


def render():
    st.markdown(HEADER_CSS, unsafe_allow_html=True)
    st.markdown(encabezado(
        "Marcas y rebate",
        "El compromiso con cada proveedor, lo que va del trimestre y lo que está en juego",
        "¿Estamos cumpliendo?"), unsafe_allow_html=True)

    r = gerencia.rebates()
    mm = gerencia.marcas_mes()
    res = gerencia.resumen_gerencia()

    act = r[r["trimestre"] == TRIMESTRE_ACTUAL].copy()
    # Lo que va del trimestre son dos meses de tres: se proyecta el cierre.
    act["proyectado"] = act["unidades"] / 2 * 3
    act["cumpl_proy"] = act["proyectado"] / act["cuota"] * 100
    act["faltan_real"] = (act["cuota"] - act["proyectado"]).clip(lower=0).round(0)

    completos = r[r["trimestre"].isin(["2025-T4", "2026-T1", "2026-T2"])]

    k = st.columns(4, gap="small")
    k[0].markdown(kpi(
        "Rebate ganado 12 meses", cop(res["rebate_12m"], 0),
        f"{len(completos['trimestre'].unique())} trimestres cerrados", True, "🎁",
        "Lo que devolvieron los proveedores por cumplir cuota.",
        "En muchos meses esto ES la utilidad"), unsafe_allow_html=True)
    k[1].markdown(kpi(
        "Rebate que se dejó ir", cop(res["rebate_perdido"], 0),
        "por quedarse corto de tramo", False, "🩸",
        "Trimestres donde faltó menos del 8% de la cuota para el siguiente "
        "escalón. Nadie estaba mirando el contador."), unsafe_allow_html=True)
    k[2].markdown(kpi(
        "Bonificación 12 meses", cop(res["bonificacion"], 0),
        "producto regalado para cerrar", False, "🫗",
        "Descuento que no aparece en ninguna lista de precios y que nadie suma "
        "al año."), unsafe_allow_html=True)
    en_riesgo = float((act.loc[act["cumpl_proy"] < 100, "compra"] / 2 * 3 *
                       act.loc[act["cumpl_proy"] < 100, "siguiente_tramo"].fillna(0)).sum())
    k[3].markdown(kpi(
        "En juego este trimestre", cop(en_riesgo, 0),
        f"{int((act['cumpl_proy'] < 100).sum())} marcas no llegan al ritmo actual",
        False, "⏳", f"Quedan {DIAS_RESTANTES} días para cerrar el trimestre."),
        unsafe_allow_html=True)

    st.markdown(espacio(18), unsafe_allow_html=True)

    # ── El tablero de cuotas ────────────────────────────────────────────────
    st.markdown('<div class="ky-sub">Cómo va el trimestre en curso</div>',
                unsafe_allow_html=True)
    st.caption(f"Van 2 de 3 meses. La barra clara es lo que se proyecta al "
               f"cierre con el ritmo de hoy. Quedan **{DIAS_RESTANTES} días**.")

    for _, m in act.sort_values("cumpl_proy").iterrows():
        color = _semaforo(m["cumpl_proy"])
        ancho = min(m["cumpl_proy"], 130)
        ancho_hoy = min(m["unidades"] / m["cuota"] * 100, 130)
        excl = ('<span style="background:%s;color:#fff;font-size:9px;font-weight:800;'
                'padding:2px 7px;border-radius:3px;margin-left:7px;letter-spacing:.06em">'
                'EXCLUSIVA</span>' % PRIMARIO) if m["exclusiva"] else ""
        falta_txt = (f"faltan <b>{int(m['faltan_real'])} u</b> para la cuota"
                     if m["faltan_real"] > 0 else "cuota asegurada")
        valor_tramo = m["compra"] / 2 * 3 * (m["siguiente_tramo"] or 0)
        st.markdown(f"""
        <div style="margin-bottom:15px">
          <div style="display:flex;justify-content:space-between;align-items:baseline;
               margin-bottom:5px">
            <div style="font-size:14px;font-weight:700;color:{TINTA}">
              {m['marca']}{excl}</div>
            <div style="font-size:12px;color:{CLARO}">
              {int(m['unidades']):,} de {int(m['cuota']):,} u &nbsp;·&nbsp;
              <b style="color:{color}">{m['cumpl_proy']:.0f}%</b> proyectado</div>
          </div>
          <div style="position:relative;height:22px;background:{FONDO_SUAVE};
               border-radius:3px;overflow:hidden">
            <div style="position:absolute;left:0;top:0;height:100%;width:{ancho}%;
                 background:{color};opacity:.28"></div>
            <div style="position:absolute;left:0;top:0;height:100%;width:{ancho_hoy}%;
                 background:{color}"></div>
            <div style="position:absolute;left:100%;top:0;height:100%;width:2px;
                 background:{TINTA}"></div>
          </div>
          <div style="font-size:11px;color:{CLARO};margin-top:4px">
            {falta_txt} &nbsp;·&nbsp; el tramo siguiente vale
            <b style="color:{TINTA}">{cop(valor_tramo, 0)}</b></div>
        </div>""", unsafe_allow_html=True)

    st.markdown(espacio(10), unsafe_allow_html=True)

    peor = act.nsmallest(1, "cumpl_proy").iloc[0]
    st.markdown(panel(
        "La decisión que hay que tomar esta semana",
        f"<b>{peor['marca']}</b> va en {peor['cumpl_proy']:.0f}% proyectado. Le "
        f"faltan <b>{int(peor['faltan_real'])} unidades</b> y quedan "
        f"{DIAS_RESTANTES} días. "
        f"Comprar esas unidades cuesta {cop(peor['faltan_real'] * peor['costo_unit'] if 'costo_unit' in peor else peor['compra'] / max(peor['unidades'],1) * peor['faltan_real'], 0)} "
        f"y desbloquea {cop(peor['compra'] / 2 * 3 * (peor['siguiente_tramo'] or 0), 0)} "
        f"de rebate. "
        f"<br><br>La pregunta no es si se vende: es si <b>cabe en la bodega y si "
        f"el plazo de importación lo permite</b>. Un trimestre no se recupera en "
        f"la última semana cuando el producto tarda sesenta días en llegar — por "
        f"eso esta pantalla muestra días, no solo porcentaje.",
        "⏳", "rojo"), unsafe_allow_html=True)

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── El histórico: dónde se dejó plata ───────────────────────────────────
    st.markdown('<div class="ky-sub">Los trimestres cerrados</div>',
                unsafe_allow_html=True)
    h = completos.copy()
    h["perdido"] = np.where(
        (h["faltan_para_siguiente"] > 0) & (h["faltan_para_siguiente"] < h["cuota"] * 0.08),
        (h["siguiente_tramo"].fillna(0) - h["tasa_rebate"]) * h["compra"], 0)

    fig = go.Figure()
    for tri in sorted(h["trimestre"].unique()):
        d = h[h["trimestre"] == tri]
        fig.add_trace(go.Bar(x=d["marca"], y=d["cumplimiento"], name=tri,
                             hovertemplate="%{x} · " + tri +
                                           "<br>Cumplimiento: %{y:.0f}%<extra></extra>"))
    fig.add_hline(y=100, line_width=1.5, line_color=TINTA,
                  annotation_text="cuota", annotation_position="right")
    fig.update_yaxes(title="Cumplimiento (%)")
    st.plotly_chart(light(fig, 320), use_container_width=True)

    casi = h[h["perdido"] > 0].sort_values("perdido", ascending=False)
    if len(casi):
        st.markdown('<div class="ky-sub">Los que se quedaron a nada</div>',
                    unsafe_allow_html=True)
        t = casi[["trimestre", "marca", "cuota", "unidades", "cumplimiento",
                  "faltan_para_siguiente", "tasa_rebate", "siguiente_tramo",
                  "perdido"]].copy()
        t["cumplimiento"] = casi["cumplimiento"].map(lambda x: pct(x, 1))
        t["tasa_rebate"] = casi["tasa_rebate"].map(lambda x: pct(x * 100, 1))
        t["siguiente_tramo"] = casi["siguiente_tramo"].map(lambda x: pct((x or 0) * 100, 1))
        t["perdido"] = casi["perdido"].map(lambda x: cop(x, 0))
        for c in ("cuota", "unidades", "faltan_para_siguiente"):
            t[c] = casi[c].astype(int)
        t.columns = ["Trimestre", "Marca", "Cuota", "Vendidas", "Cumplió",
                     "Faltaron", "Rebate obtenido", "Rebate del tramo siguiente",
                     "Lo que costó"]
        st.dataframe(t, hide_index=True, width="stretch")
        peor_caso = casi.iloc[0]
        st.caption(
            f"El peor: **{peor_caso['marca']}** en {peor_caso['trimestre']} cerró en "
            f"{peor_caso['cumplimiento']:.1f}% y le faltaron "
            f"**{int(peor_caso['faltan_para_siguiente'])} unidades** para el siguiente "
            f"escalón. Esas unidades valían **{cop(peor_caso['perdido'], 0)}**. "
            f"Con una alerta a quince días del cierre eso no vuelve a pasar.")

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── La bonificación ─────────────────────────────────────────────────────
    st.markdown('<div class="ky-sub">La bonificación, que nadie suma</div>',
                unsafe_allow_html=True)
    b = mm.tail(72).groupby("marca").agg(
        unidades=("unidades", "sum"), bonificadas=("bonificadas", "sum"),
        costo=("costo_bonificacion", "sum")).reset_index()
    b["pct"] = b["bonificadas"] / b["unidades"] * 100
    b = b.sort_values("costo", ascending=False)

    fig2 = go.Figure(go.Bar(
        x=b["marca"], y=b["costo"], marker_color=ACENTO,
        customdata=np.stack([b["bonificadas"], b["pct"]], -1),
        hovertemplate="%{x}<br>%{customdata[0]:,.0f} unidades regaladas"
                      "<br>%{customdata[1]:.1f}% de lo vendido"
                      "<br>Costo: %{y:,.0f}<extra></extra>"))
    fig2.update_yaxes(title="Costo de la bonificación · 12 meses")
    st.plotly_chart(light(fig2, 280, moneda=True), use_container_width=True)

    st.markdown(panel(
        "Por qué esto no aparece en ningún informe",
        f"La bonificación no baja el precio de la factura: se entrega producto "
        f"aparte. En el sistema queda como salida de inventario sin venta, y en "
        f"el informe comercial simplemente no está. "
        f"Son <b>{cop(res['bonificacion'], 0)} en doce meses</b>, "
        f"{pct(b['bonificadas'].sum() / b['unidades'].sum() * 100)} de todo lo "
        f"vendido de estas marcas.<br><br>"
        f"El efecto secundario es peor que el costo: el ranking del equipo "
        f"comercial premia a quien más bonifica, porque su venta se ve igual y su "
        f"margen aparente también. <b>Descontarla del margen por vendedor cambia "
        f"el ranking</b> — y es la primera cosa que hay que hacer antes de "
        f"discutir cualquier esquema de comisión.",
        "🫗", "rojo"), unsafe_allow_html=True)
