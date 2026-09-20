"""Automatizaciones: lo que el sistema HACE, no lo que muestra.

Javier ya tiene BI interno. Decirle «le damos visibilidad» no le sirve — él ya
ve. Lo que preguntó en la reunión fue lo que sigue: pedidos, consulta de
inventario, listas de precio por canal, integración con el ERP y despacho
automático al operador logístico.

Esta pantalla es esa respuesta. Y tiene dos decisiones de diseño que importan
más que los gráficos:

1. **Ningún flujo que mueva plata o comprometa inventario corre solo.** La
   columna de aprobación no es un detalle de cumplimiento: es lo que hace que
   un director de operaciones pueda decir que sí. Un agente que emite órdenes
   de compra sin que nadie mire es la forma más rápida de que a un cliente le
   lleguen 600 botellas que no pidió.
2. **Las fallas se muestran.** Javier preguntó por el nivel de error y por
   alucinaciones. Un panel que reporta 100% de acierto contesta esa pregunta
   con una mentira, y él lo nota. Lo que da confianza no es no fallar: es que
   la falla quede registrada, diga por qué, y se vea quién la atendió.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.formatters import *
from utils import datos
from utils import operacion

SISTEMA_COLOR = {"Loggro": PRIMARIO, "WooCommerce": "#6A4C93",
                 "Salesforce": "#2B7A9B", "Operador logístico": "#B5762F",
                 "Google Workspace": "#4a7c59"}


def _tarjeta_flujo(a, corridas, ok_pct, horas):
    """Un flujo, contado como un proceso y no como una funcionalidad."""
    sellos = "".join(
        f'<span style="display:inline-block;background:{PALIDO};color:{TINTA};'
        f'font-size:10px;font-weight:700;padding:3px 8px;border-radius:3px;'
        f'margin:0 5px 4px 0">{s.strip()}</span>'
        for s in a["sistemas"].split("·"))
    if a["aprueba"]:
        sello_ap = (f'<span style="background:{ACENTO_LT};color:{ACENTO};font-size:10px;'
                    f'font-weight:800;padding:3px 8px;border-radius:3px;letter-spacing:.04em">'
                    f'✋ REQUIERE APROBACIÓN</span>')
    else:
        sello_ap = (f'<span style="background:#E3F0E8;color:#2f7a48;font-size:10px;'
                    f'font-weight:800;padding:3px 8px;border-radius:3px;letter-spacing:.04em">'
                    f'⚡ CORRE SOLO</span>')
    return f"""
    <div style="border:1px solid {PALIDO};border-left:3px solid {PRIMARIO};
         border-radius:4px;padding:15px 18px;margin-bottom:12px;background:#fff">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:14px">
        <div style="flex:1">
          <div style="font-size:9.5px;font-weight:800;letter-spacing:.14em;
               text-transform:uppercase;color:{CLARO}">{a['id']} · {a['area']}</div>
          <div style="font-size:15.5px;font-weight:800;color:{TINTA};margin:3px 0 7px">
            {a['nombre']}</div>
        </div>
        <div style="text-align:right;white-space:nowrap">
          <div style="font-size:19px;font-weight:800;color:{TINTA};line-height:1">
            {corridas:,}</div>
          <div style="font-size:10px;color:{CLARO}">corridas · 30 días</div>
        </div>
      </div>
      <div style="font-size:12px;color:{CLARO};margin-bottom:4px">
        <b style="color:{TINTA}">Se dispara cuando:</b> {a['disparador']}</div>
      <div style="font-size:12px;color:{CLARO};line-height:1.6;margin-bottom:9px">
        <b style="color:{TINTA}">Qué hace:</b> {a['pasos']}</div>
      <div style="font-size:11.5px;color:{TINTA};font-style:italic;
           border-left:2px solid {PALIDO};padding-left:10px;margin-bottom:10px">
        {a['porque']}</div>
      <div>{sellos}{sello_ap}
        <span style="float:right;font-size:11px;color:{CLARO};padding-top:3px">
          {ok_pct:.0f}% sin intervención · {horas:.0f} h/mes</span></div>
    </div>"""


def render():
    st.markdown(HEADER_CSS, unsafe_allow_html=True)
    st.markdown(encabezado(
        "Automatizaciones",
        "Los procesos que el sistema ejecuta sobre Loggro, WooCommerce y Salesforce · últimos 30 días",
        "¿Qué se hace solo?"), unsafe_allow_html=True)

    aut = operacion.automatizaciones()
    eje = operacion.ejecuciones()
    r = operacion.resumen_operacion()

    k = st.columns(4, gap="small")
    k[0].markdown(kpi(
        "Procesos automatizados", num(len(aut)),
        f"{int(aut['aprueba'].sum())} piden aprobación humana", True, "⚙️",
        "Cada uno reemplaza una tarea que hoy hace una persona a mano."),
        unsafe_allow_html=True)
    k[1].markdown(kpi(
        "Corridas en 30 días", num(r["corridas_mes"]),
        f"{r['corridas_mes']/30:.0f} al día", True, "🔁",
        "Cada corrida es una tarea que nadie tuvo que hacer."),
        unsafe_allow_html=True)
    k[2].markdown(kpi(
        "Resueltas sin intervención", pct(r["acierto_pct"], 1),
        f"{num(r['para_revisar'])} pasaron a revisión humana",
        r["acierto_pct"] >= 90, "🎯",
        "El resto NO se ejecuta mal: se detiene y pide que alguien mire.",
        "Un proceso que nunca falla es un proceso que no se está midiendo"),
        unsafe_allow_html=True)
    k[3].markdown(kpi(
        "Horas que devuelve al mes", num(r["horas_mes"]),
        f"≈ {r['horas_mes']/160:.1f} personas de tiempo completo", True, "⏳",
        "Tiempo de gente que hoy transcribe pedidos y arma guías."),
        unsafe_allow_html=True)

    st.markdown(espacio(18), unsafe_allow_html=True)

    st.markdown(panel(
        "Lo que no se automatiza, y por qué",
        f"Los cinco flujos que mueven plata o comprometen inventario "
        f"—pedidos, compras, despacho, traslados y cartera— <b>preparan la acción "
        f"pero no la ejecutan</b>. Alguien confirma. "
        f"Es una decisión de diseño, no una limitación técnica: la diferencia entre "
        f"un asistente que ahorra tiempo y uno que un lunes despacha 600 botellas "
        f"a la dirección equivocada es exactamente esta casilla.",
        "✋", "rojo"), unsafe_allow_html=True)

    st.markdown(espacio(6), unsafe_allow_html=True)

    # ── El catálogo de flujos ───────────────────────────────────────────────
    areas = ["Todas"] + sorted(aut["area"].unique().tolist())
    c1, c2 = st.columns([1, 3])
    area = c1.selectbox("Área", areas, key="au_area")
    sel = aut if area == "Todas" else aut[aut["area"] == area]

    por_flujo = eje.groupby("id").agg(
        corridas=("id", "size"),
        ok=("resultado", lambda s: (s == "ok").mean() * 100),
        horas=("minutos_ahorrados", lambda s: s.sum() / 60)).to_dict("index")

    for _, a in sel.iterrows():
        m = por_flujo.get(a["id"], {"corridas": 0, "ok": 0, "horas": 0})
        st.markdown(_tarjeta_flujo(a, m["corridas"], m["ok"], m["horas"]),
                    unsafe_allow_html=True)

    st.markdown(espacio(10), unsafe_allow_html=True)

    # ── Ritmo por hora: dónde está el valor real ────────────────────────────
    st.markdown('<div class="ky-sub">Cuándo trabaja</div>', unsafe_allow_html=True)
    eje2 = eje.copy()
    eje2["hora"] = eje2["momento"].dt.hour
    por_hora = eje2.groupby("hora").size().reindex(range(0, 24), fill_value=0)
    fuera = int(por_hora[list(range(0, 8)) + list(range(19, 24))].sum())

    fig = go.Figure(go.Bar(
        x=por_hora.index, y=por_hora.values,
        marker_color=[ACENTO if (h < 8 or h >= 19) else PRIMARIO for h in por_hora.index],
        hovertemplate="%{x}:00 · %{y} corridas<extra></extra>"))
    fig.update_xaxes(title="Hora del día", dtick=2)
    st.plotly_chart(light(fig, 250), width="stretch", theme=None, config=PLOTLY_CONFIG)
    st.caption(
        f"En rojo, las {num(fuera)} corridas fuera del horario de oficina "
        f"({pct(fuera / max(len(eje2), 1) * 100, 0)} del total). Un bar que pide a las "
        f"11 de la noche hoy espera a mañana; aquí su pedido ya está armado "
        f"cuando alguien abre el computador.")

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── La bitácora, con las fallas adelante ────────────────────────────────
    st.markdown('<div class="ky-sub">Bitácora · lo que pidió revisión</div>',
                unsafe_allow_html=True)
    fallas = eje[eje["resultado"] != "ok"].copy()
    if fallas.empty:
        st.info("Nada pendiente de revisión en los últimos 30 días.")
    else:
        motivos = fallas["motivo"].value_counts()
        st.markdown(
            f'<p style="font-size:12.5px;color:{CLARO};margin:0 0 10px">'
            f'<b style="color:{TINTA}">{len(fallas)} de {len(eje):,}</b> corridas se '
            f'detuvieron y pidieron que alguien mirara. Ninguna se ejecutó mal: el '
            f'flujo para antes de actuar. El motivo más común '
            f'—<i>{motivos.index[0].lower()}</i>— aparece {motivos.iloc[0]} veces, y es '
            f'un dato que se arregla una vez, no un error que se repite.</p>',
            unsafe_allow_html=True)
        t = fallas.head(14)[["momento", "flujo", "cliente", "motivo"]].copy()
        t["momento"] = t["momento"].dt.strftime("%d %b · %H:%M")
        t.columns = ["Cuándo", "Flujo", "Cliente", "Por qué se detuvo"]
        st.dataframe(t, hide_index=True, width="stretch")

    st.markdown(espacio(14), unsafe_allow_html=True)
    st.markdown(panel(
        "Lo que esto NO es todavía",
        "Lo que se ve aquí corre sobre datos simulados con la estructura de KYVA. "
        "Montarlo de verdad es una implementación aparte del panel y más extensa: "
        "hay que mapear las listas de precio por canal, acordar cómo se identifica "
        "un cliente que escribe desde un celular nuevo, y definir qué pasa cuando el "
        "operador logístico no cubre una zona. Nada de eso es investigación — es "
        "trabajo de integración, y hay que cotizarlo como tal.",
        "🧭", "azul"), unsafe_allow_html=True)
