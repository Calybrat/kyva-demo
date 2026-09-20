"""Filtros globales: ciudad, canal, vendedor y periodo, para todo el panel.

La objeción más dura de la revisión adversaria fue ésta:

    «En 23 módulos hay 6 controles interactivos en total. No puedo pedirle
    "muéstrame solo Medellín". No puedo pedirle "solo las cuentas de Julián".
    Eso no es un panel de gerencia — es un PDF con colores bonitos. Y ese es
    literalmente el motivo por el que dejé de abrir las dos herramientas
    anteriores: porque la pregunta que yo tenía nunca era exactamente la que la
    pantalla contestaba.»

Es la crítica correcta y es estructural, no cosmética. Un tablero contesta las
preguntas que su autor anticipó; una herramienta contesta la que tiene el
gerente en la cabeza a las siete de la mañana.

Tres decisiones de diseño que importan:

  · **El filtro es global y persiste entre pantallas.** Si alguien puso
    «Medellín» y salta de cuentas a rutas, sigue en Medellín. Un filtro que se
    reinicia al navegar obliga a reponerlo cada vez y se deja de usar.
  · **Siempre se ve qué está filtrado.** Un panel filtrado que parece completo
    es peor que no tener filtros: alguien toma una decisión sobre un tercio de
    la empresa creyendo que la vio entera.
  · **Los módulos no tienen que saber nada.** Piden `aplicar(df)` y listo.
"""
import pandas as pd
import streamlit as st

from utils.formatters import PRIMARIO, ACENTO, CLARO, PALIDO, TINTA, FONDO_SUAVE

CLAVE = "filtro_global"
VACIO = {"ciudad": "Todas", "canal": "Todos", "vendedor": "Todos", "periodo": "Trimestre"}

# Los periodos, con el mes desde el que cuentan. El corte del panel es agosto.
PERIODOS = {
    "Mes": "2026-08",
    "Trimestre": "2026-06",
    "Semestre": "2026-03",
    "12 meses": "2025-09",
    "Todo": "2024-09",
}


def _estado() -> dict:
    if CLAVE not in st.session_state:
        st.session_state[CLAVE] = dict(VACIO)
    return st.session_state[CLAVE]


def activo() -> bool:
    e = _estado()
    return any(e[k] != VACIO[k] for k in ("ciudad", "canal", "vendedor"))


def resumen() -> str:
    e = _estado()
    partes = [v for k, v in e.items()
              if k != "periodo" and v != VACIO[k]]
    return " · ".join(partes) if partes else "Toda la operación"


def barra(cuentas: pd.DataFrame) -> None:
    """La barra de filtros. Va arriba de todo, en la barra lateral."""
    e = _estado()
    ciudades = ["Todas"] + sorted(cuentas["ciudad"].dropna().unique().tolist())
    canales = ["Todos"] + sorted(cuentas["canal"].dropna().unique().tolist())
    vendedores = ["Todos"] + sorted(cuentas["vendedor"].dropna().unique().tolist())

    e["periodo"] = st.selectbox("Periodo", list(PERIODOS), key="f_per",
                                index=list(PERIODOS).index(e["periodo"]))
    e["ciudad"] = st.selectbox("Ciudad", ciudades, key="f_ciu",
                               index=ciudades.index(e["ciudad"])
                               if e["ciudad"] in ciudades else 0)
    e["canal"] = st.selectbox("Canal", canales, key="f_can",
                              index=canales.index(e["canal"])
                              if e["canal"] in canales else 0)
    e["vendedor"] = st.selectbox("Vendedor", vendedores, key="f_ven",
                                 index=vendedores.index(e["vendedor"])
                                 if e["vendedor"] in vendedores else 0)
    if activo() and st.button("Quitar filtros", width="stretch", key="f_clear"):
        st.session_state[CLAVE] = dict(VACIO)
        st.rerun()


def aviso() -> str:
    """La cinta que avisa que lo que se ve NO es toda la empresa.

    Es lo que impide el error caro: decidir sobre un tercio del negocio creyendo
    que se vio entero. Un panel filtrado que parece completo es peor que uno sin
    filtros.
    """
    if not activo():
        return ""
    e = _estado()
    return (
        f'<div style="background:{ACENTO};color:#fff;border-radius:5px;'
        f'padding:7px 15px;margin:0 0 14px;font-size:11.5px;font-weight:700;'
        f'font-family:Montserrat,sans-serif;letter-spacing:.02em;'
        f'display:flex;justify-content:space-between;align-items:center">'
        f'<span>⚠ Vista filtrada: <b>{resumen()}</b> · {e["periodo"].lower()}</span>'
        f'<span style="opacity:.8;font-weight:600">no es la operación completa</span>'
        f'</div>')


def desde() -> str:
    """El mes desde el que cuenta el periodo elegido."""
    return PERIODOS[_estado()["periodo"]]


def aplicar(df: pd.DataFrame, col_mes: str = "mes") -> pd.DataFrame:
    """Aplica lo que esté puesto. Los módulos no tienen que saber nada más.

    Solo filtra por las columnas que el DataFrame tenga: así sirve igual para
    ventas, facturas, quiebres o punto de venta, que traen combinaciones
    distintas de ciudad/canal/vendedor.
    """
    e = _estado()
    d = df
    if col_mes and col_mes in d.columns:
        d = d[d[col_mes] >= PERIODOS[e["periodo"]]]
    for col, val in (("ciudad", e["ciudad"]), ("canal", e["canal"]),
                     ("vendedor", e["vendedor"])):
        if val not in ("Todas", "Todos") and col in d.columns:
            d = d[d[col] == val]
    return d


def encabezado_filtro() -> None:
    """Pinta el aviso. Se llama al principio de cada módulo que filtra."""
    a = aviso()
    if a:
        st.markdown(a, unsafe_allow_html=True)
