import importlib
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))
from utils.formatters import (CSS, HEADER_CSS, asset_b64, motivo_svg,
                              PRIMARIO, CLARO, PALIDO, ACENTO, TINTA)
from utils.visitas import registrar_visita, panel_solicitado, render_panel_visitas

st.set_page_config(
    page_title="KYVA · Panel de Negocio | Calybrat",
    page_icon="🥂",
    layout="wide",
)

# El demo es de acceso libre: solo se deja constancia de la visita.
registrar_visita()

st.markdown(CSS + HEADER_CSS, unsafe_allow_html=True)

# Agrupado por la PREGUNTA que se hace el equipo de KYVA, no por el área que
# produce el dato. KYVA gana plata por cuatro vías con márgenes muy distintos
# (The Store, The Lounge, corporativo y distribución), así que casi todo el
# panel gira alrededor de una sola pregunta: ¿crecer nos está dejando plata?
GRUPOS = [
    ("El lunes a las 7", [
        ("🏠  Tablero Ejecutivo", "p01_tablero"),
    ]),
    ("¿Crecer nos deja plata?", [
        ("💸  Dónde se va el margen", "p02_margen"),
        ("🧭  Los cuatro negocios", "p03_canales"),
        ("🏦  Caja y capital de trabajo", "p04_caja"),
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
    ("¿Qué se hace solo?", [
        ("⚙️  Automatizaciones", "p16_automatizaciones"),
        ("🔔  Alertas", "p19_alertas"),
    ]),
    ("Dirección", [
        ("📄  Reportes Automáticos", "p14_reportes"),
        ("🤖  Agente IA KYVA", "p15_agente"),
    ]),
]
PAGES = {label: mod for _, items in GRUPOS for label, mod in items}

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
      <div style="height:2px;border-radius:99px;margin:13px 0 2px;
        background:linear-gradient(90deg,{PALIDO} 0%,{CLARO} 50%,{ACENTO} 80%,transparent)"></div>
    </div>
    """, unsafe_allow_html=True)

    if "page" not in st.session_state:
        st.session_state.page = list(PAGES.keys())[0]

    for grupo, items in GRUPOS:
        st.markdown(
            f'<div style="font-size:9px;font-weight:700;letter-spacing:.16em;'
            f'text-transform:uppercase;color:{CLARO};margin:15px 0 5px 4px;'
            f'font-family:Montserrat,sans-serif">{grupo}</div>',
            unsafe_allow_html=True)
        for label, _mod in items:
            if st.button(label, key=f"nav_{label}", width="stretch"):
                st.session_state.page = label

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
