"""Centro de decisiones: lo único que de verdad necesita a un gerente hoy.

**Este es el módulo que separa un panel de una herramienta de gerencia.**

Un tablero dice «esta cuenta deja -2%». Eso no es una decisión: es un dato que
alguien tiene que interpretar, convertir en opciones, estimar y ejecutar. Aquí
eso ya viene hecho. Cada fila trae cuatro cosas y por eso se puede resolver en
veinte segundos:

  1. **El número que la justifica**, no una alerta genérica.
  2. **Las opciones concretas**, redactadas como se dirían en una reunión.
  3. **Lo que cuesta no hacer nada**, anualizado. Es lo que ordena la bandeja:
     no por gravedad declarada sino por plata en juego.
  4. **Quién decide.** Una decisión sin dueño vuelve a aparecer el lunes.

La bandeja junta lo que hoy vive en cinco lugares distintos: el ERP, el informe
del operador logístico, el Excel de cartera, el WhatsApp del vendedor y la
cabeza de quien compra. Ese reparto es la razón por la que nada se decide: cada
pieza sola no alcanza para actuar.

**Nada de aquí se ejecuta solo.** Decidir deja registro y dispara el flujo; la
acción la confirma una persona. Es la misma regla del módulo de
automatizaciones y es lo que permite que un director de operaciones diga que sí.
"""
import numpy as np
import pandas as pd
import streamlit as st

from utils.formatters import *
from utils import b2b, operacion, datos

TONO = {"Alta": "#8B1E1E", "Media": "#B5762F", "Baja": CLARO}
ICONO = {"Condiciones comerciales": "🤝", "Cuenta apagada": "🔌",
         "Riesgo de crédito": "🏦", "Compra": "📦", "Excepción": "⚠️",
         "Precio": "🏷️"}


# ── Construcción de la bandeja ───────────────────────────────────────────────
def _bandeja() -> pd.DataFrame:
    """Reúne en una sola cola lo que hoy vive repartido en cinco sistemas.

    El orden lo fija la PLATA EN JUEGO, no la gravedad que declare cada fuente.
    Una alerta «alta» de 400 mil pesos no puede ir encima de una «media» de
    catorce millones — y en los sistemas que las producen por separado eso pasa
    todos los días, que es por lo que nadie las lee.
    """
    filas = []

    # 1. Lo que sale del análisis de cuentas (gen_b2b lo calcula con su costo real)
    d = b2b.decisiones()
    for _, r in d.iterrows():
        plata = _a_pesos(r.get("si_nadie_hace_nada", ""))
        filas.append({
            "tipo": r["tipo"], "urgencia": r["urgencia"], "titulo": r["titulo"],
            "dato": r["dato"], "opciones": r["accion"],
            "costo_inaccion": abs(plata), "costo_txt": r["si_nadie_hace_nada"],
            "decide": r["decide"], "quien": r.get("cuenta", ""),
            "origen": "Análisis de cuentas",
        })

    # 2. Compras cuya ventana de importación se cierra
    inv = operacion.inventario()
    urge = inv[(inv["urgencia"].isin(["Ventana cerrada", "Pedir esta semana"])) &
               (inv["faltante_pico"] > 0)]
    if len(urge):
        por_prov = urge.groupby("proveedor").agg(
            refs=("sku", "nunique"), plata=("valor_faltante", "sum"),
            limite=("fecha_limite_pedido", "min")).reset_index()
        for _, r in por_prov.nlargest(4, "plata").iterrows():
            filas.append({
                "tipo": "Compra", "urgencia": "Alta",
                "titulo": f"Orden a {r['proveedor']} antes del {r['limite']:%d de %B}",
                "dato": f"{r['refs']} referencias · {cop(r['plata'], 0)} de faltante para la temporada",
                "opciones": "Emitir la orden sugerida · pedir solo el top 10 · "
                            "asumir el quiebre y comprar a un mayorista local en diciembre",
                "costo_inaccion": float(r["plata"]) * 0.45,
                "costo_txt": f"{cop(r['plata'] * 0.45, 0)} de venta perdida estimada",
                "decide": "Compras", "quien": r["proveedor"],
                "origen": "Reposición",
            })

    # 3. Lo que la automatización no pudo resolver sola
    eje = operacion.ejecuciones()
    fallas = eje[eje["resultado"] != "ok"]
    if len(fallas):
        por_motivo = fallas["motivo"].value_counts().head(2)
        for motivo, n in por_motivo.items():
            filas.append({
                "tipo": "Excepción", "urgencia": "Media",
                "titulo": f"{n} pedidos detenidos: {motivo.lower()}",
                "dato": f"{n} corridas en 30 días se pararon por lo mismo",
                "opciones": "Corregir el dato de origen una vez · dejar la regla como está "
                            "y seguir revisando a mano",
                "costo_inaccion": n * 11 * 12 * 60_000 / 60,
                "costo_txt": f"≈{n * 11 * 12 / 60:,.0f} horas al año de revisión manual",
                "decide": "Operaciones", "quien": "",
                "origen": "Automatizaciones",
            })

    # 4. Precio contra competencia
    try:
        pc = datos.precios_competencia()
        caras = pc[pc["kyva_classic"] > pc["precio_competidor"] * 1.06]
        if len(caras):
            filas.append({
                "tipo": "Precio", "urgencia": "Media",
                "titulo": f"{len(caras)} referencias por encima del competidor",
                "dato": "  ·  ".join(f"{r['producto'][:26]} +"
                                     f"{(r['kyva_classic']/r['precio_competidor']-1)*100:.0f}%"
                                     for _, r in caras.head(3).iterrows()),
                "opciones": "Igualar el precio · sostenerlo y argumentar servicio · "
                            "bajar solo en las cuentas donde compiten de frente",
                "costo_inaccion": 0,
                "costo_txt": "riesgo de perder la referencia en licitación",
                "decide": "Dirección comercial", "quien": "",
                "origen": "Precios",
            })
    except Exception:
        pass

    b = pd.DataFrame(filas)
    if b.empty:
        return b
    return b.sort_values("costo_inaccion", ascending=False).reset_index(drop=True)


def _a_pesos(txt: str) -> float:
    """«14 M al año» → 14.000.000. Sirve para ordenar por plata, no por texto."""
    import re
    m = re.search(r"(-?[\d.,]+)\s*M", str(txt))
    if not m:
        return 0.0
    try:
        return float(m.group(1).replace(".", "").replace(",", ".")) * 1e6
    except ValueError:
        return 0.0


# ── Presentación ─────────────────────────────────────────────────────────────
def _tarjeta(i, r, resuelta):
    color = TONO.get(r["urgencia"], CLARO)
    opciones = "".join(
        f'<li style="margin-bottom:3px">{o.strip()}</li>'
        for o in str(r["opciones"]).split("·"))
    apagado = "opacity:.45;" if resuelta else ""
    sello = ('<span style="background:#E3F0E8;color:#2f7a48;font-size:10px;'
             'font-weight:800;padding:2px 8px;border-radius:3px">✓ DECIDIDA</span>'
             if resuelta else "")
    return f"""
    <div style="{apagado}border:1px solid {PALIDO};border-left:4px solid {color};
         border-radius:5px;padding:15px 18px;margin-bottom:11px;background:#fff">
      <div style="display:flex;justify-content:space-between;gap:14px;align-items:flex-start">
        <div style="flex:1">
          <div style="font-size:9.5px;font-weight:800;letter-spacing:.13em;
               text-transform:uppercase;color:{CLARO}">
            {ICONO.get(r['tipo'],'•')} &nbsp;{r['tipo']} &nbsp;·&nbsp; {r['origen']}</div>
          <div style="font-size:15.5px;font-weight:800;color:{TINTA};margin:4px 0 6px">
            {r['titulo']} {sello}</div>
          <div style="font-size:12px;color:{CLARO};margin-bottom:9px">{r['dato']}</div>
        </div>
        <div style="text-align:right;white-space:nowrap;padding-left:10px">
          <div style="font-size:9px;font-weight:800;letter-spacing:.1em;
               text-transform:uppercase;color:{CLARO}">Si nadie hace nada</div>
          <div style="font-size:17px;font-weight:800;color:{color};line-height:1.2">
            {r['costo_txt']}</div>
        </div>
      </div>
      <div style="font-size:11.5px;color:{TINTA};background:{FONDO_SUAVE};
           border-radius:4px;padding:9px 14px 9px 26px;margin-bottom:8px">
        <b style="margin-left:-12px">Opciones:</b>
        <ul style="margin:4px 0 0;padding-left:14px">{opciones}</ul></div>
      <div style="font-size:11px;color:{CLARO}">
        Decide: <b style="color:{TINTA}">{r['decide']}</b>
        {f" &nbsp;·&nbsp; {r['quien']}" if r['quien'] else ""}</div>
    </div>"""


def render():
    st.markdown(HEADER_CSS, unsafe_allow_html=True)
    st.markdown(encabezado(
        "Centro de decisiones",
        "Lo que espera que alguien decida, ordenado por la plata que cuesta no decidirlo",
        "El lunes a las 7"), unsafe_allow_html=True)

    b = _bandeja()
    if "decididas" not in st.session_state:
        st.session_state.decididas = set()
    pendientes = b[~b.index.isin(st.session_state.decididas)]

    total = float(b["costo_inaccion"].sum())
    abierto = float(pendientes["costo_inaccion"].sum())
    altas = int((pendientes["urgencia"] == "Alta").sum())

    k = st.columns(4, gap="small")
    k[0].markdown(kpi(
        "Esperando decisión", num(len(pendientes)),
        f"{altas} no pueden esperar a la otra semana", altas == 0, "📋",
        "Cada una trae el número, las opciones y quién decide."),
        unsafe_allow_html=True)
    k[1].markdown(kpi(
        "En juego", cop(abierto, 0),
        "anualizado, si nadie las toca", False, "💰",
        "La suma de lo que cuesta no decidir cada una.",
        "Es lo que ordena la bandeja — no la gravedad declarada"),
        unsafe_allow_html=True)
    k[2].markdown(kpi(
        "Decididas en esta sesión", num(len(st.session_state.decididas)),
        cop(total - abierto, 0) + " resueltos",
        len(st.session_state.decididas) > 0, "✓",
        "Queda registro de quién decidió qué y cuándo."),
        unsafe_allow_html=True)
    fuentes = b["origen"].nunique()
    k[3].markdown(kpi(
        "Sistemas que se consultan", num(fuentes),
        "en una sola bandeja", True, "🔗",
        "ERP, logística, cartera, compras y precios. Hoy son cinco pestañas "
        "distintas y por eso nada se decide."), unsafe_allow_html=True)

    st.markdown(espacio(18), unsafe_allow_html=True)

    st.markdown(panel(
        "Por qué esto no es una lista de alertas",
        "Una alerta dice que algo pasó. Una decisión trae <b>el número que la "
        "justifica, las opciones redactadas como se dirían en una reunión, lo que "
        "cuesta no hacer nada, y quién decide</b>. La diferencia se nota en el "
        "orden: aquí manda la plata en juego, no la gravedad que declare cada "
        "sistema. Una alerta «alta» de cuatrocientos mil pesos no puede ir encima "
        "de una «media» de catorce millones — y en sistemas separados eso pasa "
        "todos los días, que es exactamente por lo que nadie las lee.",
        "📋", "azul"), unsafe_allow_html=True)

    st.markdown(espacio(6), unsafe_allow_html=True)

    c = st.columns([1, 1, 1, 2])
    tipos = ["Todos"] + sorted(b["tipo"].unique().tolist())
    tipo = c[0].selectbox("Tipo", tipos, key="dc_tipo")
    quien = c[1].selectbox("Decide", ["Todos"] + sorted(b["decide"].unique().tolist()),
                           key="dc_quien")
    ver = c[2].selectbox("Mostrar", ["Pendientes", "Todas"], key="dc_ver")

    sel = b if ver == "Todas" else pendientes
    if tipo != "Todos":
        sel = sel[sel["tipo"] == tipo]
    if quien != "Todos":
        sel = sel[sel["decide"] == quien]

    if sel.empty:
        st.success("Nada pendiente con ese filtro. La bandeja en cero es el objetivo, "
                   "no la excepción.")
    for i, r in sel.iterrows():
        resuelta = i in st.session_state.decididas
        st.markdown(_tarjeta(i, r, resuelta), unsafe_allow_html=True)
        if not resuelta:
            bot = st.columns([1, 1, 1, 3])
            if bot[0].button("Decidir", key=f"ok_{i}", width="stretch"):
                st.session_state.decididas.add(i)
                st.rerun()
            if bot[1].button("Delegar", key=f"dl_{i}", width="stretch"):
                st.session_state.decididas.add(i)
                st.rerun()
            bot[2].button("Aplazar", key=f"ap_{i}", width="stretch")

    st.markdown(espacio(14), unsafe_allow_html=True)
    st.markdown(panel(
        "Qué pasa al pulsar «Decidir»",
        "En el demo, marcar la tarjeta. Conectado de verdad: queda el registro de "
        "quién decidió, cuándo y con qué número a la vista —eso es lo que permite "
        "revisar en enero por qué se le bajó el descuento a una cuenta en "
        "septiembre— y se dispara el flujo correspondiente en Loggro o Salesforce, "
        "que <b>prepara la acción y espera confirmación</b>. El sistema nunca "
        "ejecuta solo lo que mueve plata.",
        "✓", "rojo"), unsafe_allow_html=True)
