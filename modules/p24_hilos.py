"""Hilos: discutir un número donde está el número.

Hoy la discusión sobre una cifra pasa en WhatsApp, y ahí se pierde. En enero
nadie recuerda por qué en septiembre se le bajó el descuento a una discoteca,
quién lo autorizó ni contra qué número se decidió. Se vuelve a discutir de cero,
con opiniones en vez de datos.

Un hilo aquí está **anclado al dato que lo provocó**. No es un chat con una
pestaña de reportes al lado: es la conversación pegada a la cifra, con un dueño,
un estado y —lo único que de verdad importa— **un desenlace**.

Sin la columna de desenlace esto sería un chat corporativo más, y de esos
sobran. Con ella se convierte en la memoria de por qué la empresa hace lo que
hace, que es lo que en la práctica se pierde cada vez que alguien renuncia.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.formatters import *
from utils import b2b

INICIALES_COLOR = [PRIMARIO, ACENTO, "#2B7A9B", "#B5762F", "#7D5BA6"]


def _avatar(nombre, i):
    ini = "".join(p[0] for p in str(nombre).split()[:2]).upper()
    c = INICIALES_COLOR[i % len(INICIALES_COLOR)]
    return (f'<span style="display:inline-flex;align-items:center;justify-content:center;'
            f'width:26px;height:26px;border-radius:50%;background:{c};color:#fff;'
            f'font-size:10.5px;font-weight:800;letter-spacing:.02em;'
            f'font-family:Montserrat,sans-serif;flex:none">{ini}</span>')


def _hilo(h, i):
    cerrado = h["estado"] == "Resuelto"
    color = "#2f7a48" if cerrado else "#B5762F"
    sello = ("✓ Resuelto" if cerrado else "● En curso")
    return f"""
    <div style="border:1px solid {PALIDO};border-radius:6px;padding:14px 17px;
         margin-bottom:10px;background:#fff">
      <div style="display:flex;gap:11px;align-items:flex-start">
        {_avatar(h['abierto_por'], i)}
        <div style="flex:1">
          <div style="display:flex;justify-content:space-between;gap:12px;align-items:baseline">
            <div style="font-size:14px;font-weight:700;color:{TINTA}">{h['asunto']}</div>
            <div style="font-size:10px;font-weight:800;color:{color};white-space:nowrap">
              {sello}</div>
          </div>
          <div style="font-size:10.5px;color:{CLARO};margin-top:2px">
            {h['abierto_por']} &nbsp;·&nbsp; {h['abierto']:%d de %B} &nbsp;·&nbsp;
            {h['mensajes']} mensajes &nbsp;·&nbsp;
            <span style="background:{FONDO_SUAVE};padding:2px 7px;border-radius:3px;
              font-weight:700;color:{TINTA}">📌 {h['ancla']}</span></div>
          <div style="font-size:12px;color:{TINTA};margin-top:8px;
               border-left:2px solid {PALIDO};padding-left:10px">
            <b style="color:{CLARO};font-size:10px;letter-spacing:.1em;
               text-transform:uppercase">En qué quedó</b><br>{h['desenlace']}</div>
        </div>
      </div>
    </div>"""


def render():
    st.markdown(HEADER_CSS, unsafe_allow_html=True)
    st.markdown(encabezado(
        "Hilos del equipo",
        "Las conversaciones sobre los números, pegadas al número que las provocó",
        "Cómo se decide aquí"), unsafe_allow_html=True)

    h = b2b.hilos().sort_values("abierto", ascending=False)
    abiertos = h[h["estado"] != "Resuelto"]
    gente = h["abierto_por"].nunique()

    k = st.columns(4, gap="small")
    k[0].markdown(kpi(
        "Hilos abiertos", num(len(abiertos)),
        f"de {len(h)} en los últimos 45 días", len(abiertos) < 5, "💬",
        "Conversaciones sobre una cifra concreta que todavía no cierran."),
        unsafe_allow_html=True)
    k[1].markdown(kpi(
        "Decisiones con memoria", num(int((h["estado"] == "Resuelto").sum())),
        "quedan con su porqué y su número", True, "🧠",
        "En enero se puede reconstruir por qué se tomó cada una."),
        unsafe_allow_html=True)
    k[2].markdown(kpi(
        "Personas participando", num(gente),
        "dirección, comercial y compras", True, "👥",
        "Un hilo sirve cuando lo lee quien no estuvo en la reunión."),
        unsafe_allow_html=True)
    k[3].markdown(kpi(
        "Módulos con conversación", num(h["modulo"].nunique()),
        "el dato y la discusión en el mismo sitio", True, "📌",
        "Cada hilo está anclado a la pantalla donde vive la cifra."),
        unsafe_allow_html=True)

    st.markdown(espacio(18), unsafe_allow_html=True)

    st.markdown(panel(
        "Por qué esto no es un chat más",
        "El equipo ya tiene WhatsApp. Lo que no tiene es <b>memoria de por qué "
        "hace lo que hace</b>. Un hilo aquí nace anclado a una cifra, tiene dueño "
        "y termina en un desenlace escrito. Dentro de cuatro meses, cuando alguien "
        "pregunte por qué esta cuenta paga a 15 días y no a 30, la respuesta está "
        "donde está el número — no en el teléfono de alguien que ya no trabaja acá.",
        "🧠", "azul"), unsafe_allow_html=True)

    st.markdown(espacio(6), unsafe_allow_html=True)

    c = st.columns([1, 1, 2])
    estado = c[0].selectbox("Estado", ["Todos", "En curso", "Resuelto"], key="hl_est")
    quien = c[1].selectbox("Abierto por", ["Todos"] + sorted(h["abierto_por"].unique().tolist()),
                           key="hl_q")
    sel = h
    if estado != "Todos":
        sel = sel[sel["estado"] == estado]
    if quien != "Todos":
        sel = sel[sel["abierto_por"] == quien]

    for i, (_, x) in enumerate(sel.iterrows()):
        st.markdown(_hilo(x, i), unsafe_allow_html=True)

    st.markdown(espacio(14), unsafe_allow_html=True)

    # ── Abrir uno nuevo ─────────────────────────────────────────────────────
    st.markdown('<div class="ky-sub">Abrir un hilo</div>', unsafe_allow_html=True)
    with st.form("nuevo_hilo", clear_on_submit=True):
        f = st.columns([2, 1])
        asunto = f[0].text_input("¿Sobre qué?",
                                 placeholder="Ej.: Envigado nos está costando más de lo que deja")
        ancla = f[1].selectbox("Anclar a", [
            "Rentabilidad por cuenta", "Rutas y costo de servir", "Equipo comercial",
            "Reposición y compras", "Precio vs. competencia", "Caja y capital de trabajo"])
        nota = st.text_area("Qué viste", height=80,
                            placeholder="El número que te llamó la atención y por qué")
        g = st.columns([1, 1, 3])
        duenio = g[0].selectbox("Dueño", ["Javier", "Andrea Restrepo", "Julián Mora",
                                          "Paola Cárdenas", "Santiago Ospina", "Valentina Ríos"])
        if g[1].form_submit_button("Abrir hilo", width="stretch"):
            if asunto.strip():
                st.session_state.setdefault("hilos_nuevos", []).append(
                    {"asunto": asunto, "ancla": ancla, "duenio": duenio, "nota": nota})
                st.success(f"Hilo abierto y anclado a «{ancla}». Se le notificó a {duenio}.")
            else:
                st.warning("Falta el asunto.")

    for n in st.session_state.get("hilos_nuevos", []):
        st.markdown(
            f'<div style="border:1px dashed {ACENTO};border-radius:6px;padding:12px 16px;'
            f'margin-bottom:8px;background:{ACENTO_LT}33">'
            f'<div style="font-size:13.5px;font-weight:700;color:{TINTA}">{n["asunto"]}</div>'
            f'<div style="font-size:10.5px;color:{CLARO};margin-top:3px">'
            f'Nuevo · anclado a {n["ancla"]} · dueño {n["duenio"]}</div></div>',
            unsafe_allow_html=True)

    st.markdown(espacio(12), unsafe_allow_html=True)
    st.markdown(panel(
        "Dónde llega la notificación",
        "Al abrir un hilo, al dueño le llega por <b>WhatsApp</b> si es de campo y por "
        "<b>correo</b> si es de dirección, con el número y el enlace directo a la "
        "pantalla. Responder desde ahí escribe en el hilo sin tener que entrar. "
        "Un sistema que exige entrar al panel para enterarse ya perdió: la gente "
        "vive en su bandeja, no en nuestro producto.",
        "📡", "rojo"), unsafe_allow_html=True)
