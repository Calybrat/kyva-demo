import importlib
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))
from utils.formatters import (CSS, CSS_PRODUCTO, HEADER_CSS, asset_b64, motivo_svg,
                              PRIMARIO, CLARO, PALIDO, ACENTO, TINTA)
from utils.visitas import registrar_visita, panel_solicitado, render_panel_visitas

st.set_page_config(
    page_title="KYVA · Panel de Negocio | Calybrat",
    page_icon="🥂",
    layout="wide",
)

# El demo es de acceso libre: solo se deja constancia de la visita.
registrar_visita()

st.markdown(CSS + HEADER_CSS + CSS_PRODUCTO, unsafe_allow_html=True)

# Agrupado por la PREGUNTA que se hace el equipo de KYVA, no por el área que
# produce el dato. KYVA gana plata por cuatro vías con márgenes muy distintos
# (The Store, The Lounge, corporativo y distribución), así que casi todo el
# panel gira alrededor de una sola pregunta: ¿crecer nos está dejando plata?
GRUPOS = [
    ("El lunes a las 7", [
        ("📋  Centro de decisiones", "p20_decisiones"),
        ("🏠  Tablero Ejecutivo", "p01_tablero"),
    ]),
    ("¿Crecer nos deja plata?", [
        ("💸  Dónde se va el margen", "p02_margen"),
        ("🧭  Los cuatro negocios", "p03_canales"),
        ("🏦  Caja y capital de trabajo", "p04_caja"),
    ]),
    ("¿Quién nos deja plata?", [
        ("🏪  Rentabilidad por cuenta", "p21_cuentas"),
        ("👥  Equipo comercial", "p22_equipo"),
        ("🚚  Rutas y costo de servir", "p23_rutas"),
    ]),
    ("¿Quién compra y vuelve?", [
        ("🔁  Recompra y cohortes", "p05_recompra"),
        ("🥂  Membresía Elite", "p06_elite"),
        ("🤝  Alianzas B2B2C", "p07_alianzas"),
        ("⭕  Mi Círculo", "p08_circulo"),
    ]),
    ("¿Qué vendemos y a qué precio?", [
        ("🍾  Surtido y rotación", "p09_surtido"),
        ("🏷️  Precio vs. competencia", "p10_precios"),
        ("🚚  Marcas en distribución", "p11_distribucion"),
    ]),
    ("¿Llegamos a tiempo?", [
        ("⏱️  Pide AM, recibe PM", "p12_entregas"),
    ]),
    ("¿Qué viene?", [
        ("🎄  Temporada de fin de año", "p13_temporada"),
        ("📈  Proyección de cierre", "p18_proyeccion"),
        ("📦  Reposición y compras", "p17_reposicion"),
    ]),
    ("¿Qué pasa si…?", [
        ("🎛️  Simulador", "p25_simulador"),
    ]),
    ("¿Qué se hace solo?", [
        ("⚙️  Automatizaciones", "p16_automatizaciones"),
        ("🔔  Alertas", "p19_alertas"),
    ]),
    ("Dirección", [
        ("💬  Hilos del equipo", "p24_hilos"),
        ("📄  Reportes Automáticos", "p14_reportes"),
        ("🤖  Agente IA KYVA", "p15_agente"),
    ]),
]
PAGES = {label: mod for _, items in GRUPOS for label, mod in items}


def _sin_emoji(texto: str) -> str:
    """Quita el emoji de una etiqueta de navegación, conservando el texto."""
    import re
    return re.sub(r"^[^\w¿¡]+", "", texto).strip()

with st.sidebar:
    logo = asset_b64("logo_blanco.svg")
    logo_html = (f'<img src="{logo}" style="height:64px;width:64px" alt="KYVA">'
                 if logo else
                 '<div style="font-size:24px;font-weight:900;color:#fff">KYVA</div>')
    st.markdown(f"""
    <div style="padding:14px 4px 4px">
      {logo_html}
      <div style="font-size:9.5px;color:{CLARO};margin-top:12px;font-weight:700;
        letter-spacing:.18em;text-transform:uppercase;font-family:Montserrat,sans-serif">
        Panel de negocio</div>
      <div style="font-family:'DM Serif Display',Georgia,serif;font-size:15px;
        color:{PALIDO};margin-top:2px;font-style:italic">join the circle</div>
      <div style="font-size:10.5px;color:{CLARO};margin-top:4px">corte 31 ago 2026</div>
      <div style="height:1px;margin:14px 0 2px;
        background:rgba(229,225,230,.16)"></div>
    </div>
    """, unsafe_allow_html=True)

    if "page" not in st.session_state:
        st.session_state.page = list(PAGES.keys())[0]

    # Filtros globales. Van ANTES de la navegación a propósito: la pregunta
    # («solo Medellín», «solo las cuentas de Julián») es anterior a la pantalla.
    from utils import b2b, filtros
    st.markdown(
        f'<div style="font-size:9px;font-weight:700;letter-spacing:.16em;'
        f'text-transform:uppercase;color:{CLARO};margin:4px 0 6px 4px;'
        f'font-family:Montserrat,sans-serif">Ver</div>', unsafe_allow_html=True)
    try:
        filtros.barra(b2b.cuentas())
    except Exception:
        pass
    st.markdown(f'<div style="height:1px;background:rgba(229,225,230,.14);'
                f'margin:16px 0 4px"></div>', unsafe_allow_html=True)

    # Buscador. Con veintisiete módulos se amortiza solo: escribir «cartera» es
    # más rápido que recorrer nueve grupos con la vista.
    q = st.text_input("Buscar", placeholder="Buscar pantalla…", key="nav_q",
                      label_visibility="collapsed").strip().lower()

    # El grupo de la pantalla actual, para abrirlo y dejar los demás cerrados.
    grupo_actual = next((g for g, items in GRUPOS
                         if any(l == st.session_state.page for l, _ in items)), None)

    for grupo, items in GRUPOS:
        visibles = [(l, m) for l, m in items if not q or q in l.lower()]
        if not visibles:
            continue
        st.markdown(
            f'<div style="font-size:9px;font-weight:700;letter-spacing:.17em;'
            f'text-transform:uppercase;color:rgba(145,147,161,.75);'
            f'margin:19px 0 5px 6px;font-family:Montserrat,sans-serif">{grupo}</div>',
            unsafe_allow_html=True)
        for label, _mod in visibles:
            # El estado activo NO existía: con treinta y tres filas idénticas
            # uno abre el panel y no sabe en qué pantalla está. `type="primary"`
            # es lo que el CSS engancha para pintar la barra coral izquierda.
            activo = (label == st.session_state.page)
            # Se muestra SIN el emoji pero la clave y el estado siguen usando
            # la etiqueta completa: veintisiete emoji distintos son veintisiete
            # familias tipográficas peleando en una columna de 240 px.
            visible = _sin_emoji(label)
            if st.button(visible, key=f"nav_{label}", width="stretch",
                         type="primary" if activo else "secondary"):
                st.session_state.page = label
                st.rerun()

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style="padding:16px 16px 10px;text-align:center;
      border-top:1px solid rgba(229,225,230,.12)">
      <div style="margin-bottom:9px;opacity:.85">
        {motivo_svg(PALIDO, 26)} {motivo_svg(ACENTO, 18)}
      </div>
      <div style="font-size:10.5px;color:{CLARO};margin-bottom:2px">Construido por</div>
      <div style="font-size:15px;font-weight:800;color:#fff;letter-spacing:.4px;
        font-family:Montserrat,sans-serif">Calybrat</div>
      <div style="font-size:9.5px;color:{CLARO};margin-top:5px;line-height:1.55">
        © 2026 · Demo con datos simulados<br>anclados a cifras públicas
      </div>
    </div>
    """, unsafe_allow_html=True)

# ── Panel interno de accesos (solo con ?accesos=… en la URL) ──────────────────
if panel_solicitado():
    render_panel_visitas()
    st.stop()

# ── Módulo activo ─────────────────────────────────────────────────────────────
# `__import__` cachea en sys.modules, y Streamlit Cloud no reinicia el proceso
# cuando llega código nuevo: re-ejecuta ESTE archivo —por eso un menú nuevo
# aparece de inmediato— pero deja los módulos ya importados en la versión con
# la que arrancó el contenedor. El 19-sep eso dejó cuatro pantallas caídas con
# «module 'utils.datos' has no attribute 'alertas'» aunque el código correcto
# llevaba horas en GitHub, y solo se arreglaba pulsando «Reboot app» a mano.
#
# Comparar la fecha del archivo en disco contra la del módulo cargado cierra
# ese hueco. Hay que recargar primero `utils`: los módulos guardan una
# referencia AL OBJETO módulo, así que recargarlo en el sitio les actualiza las
# funciones sin tener que recargarlos a ellos por dependencia.
def _al_dia(nombre: str) -> None:
    """Recarga un módulo si su archivo cambió en disco desde que se importó."""
    m = sys.modules.get(nombre)
    if m is None or not getattr(m, "__file__", None):
        return
    try:
        tocado = Path(m.__file__).stat().st_mtime
    except OSError:
        return
    if tocado > getattr(m, "_cargado_en", 0):
        importlib.reload(m)
        sys.modules[nombre]._cargado_en = tocado


module_name = PAGES[st.session_state.page]
try:
    for previo in ("utils.formatters", "utils.datos", "utils.operacion"):
        _al_dia(previo)
    mod = __import__(f"modules.{module_name}", fromlist=[module_name])
    _al_dia(f"modules.{module_name}")
    mod = sys.modules[f"modules.{module_name}"]
    mod.render()
except Exception as e:
    st.error(f"Error cargando módulo: {e}")
    import traceback
    st.code(traceback.format_exc())
