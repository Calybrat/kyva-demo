"""Componentes de interfaz: lo que convierte un informe en una herramienta.

El panel estaba escrito con el vocabulario de Streamlit 1.25 corriendo sobre un
runtime 1.60. Treinta y cinco gráficos estáticos, ciento noventa y ocho
tarjetas de KPI armadas a mano en HTML, cero mapas, y ni un solo gráfico en el
que se pudiera hacer clic.

Esa brecha es la diferencia entre «demo» y «software», y casi todo se cierra
con APIs que ya estaban instaladas:

  · `st.plotly_chart(on_select="rerun")` — **el mayor golpe.** Hacer clic en la
    barra de una cuenta y que se abra su ficha es lo que hace que alguien deje
    de ver un informe y empiece a ver un sistema.
  · `st.metric(chart_data=...)` — tarjetas nativas con tendencia dentro, que
    además heredan el tema. Las de HTML a mano se rompen en modo oscuro.
  · `st.column_config.ButtonColumn` — la tabla deja de ser una lista y se
    vuelve una bandeja de trabajo: se aprueba en la propia fila.
  · `bind="query-params"` — el filtro va en la URL, así que la vista se puede
    mandar por WhatsApp y el botón «atrás» del navegador funciona.

Todo lo de aquí está verificado contra la versión instalada. `st.echarts_chart`
y `st.metric(icon=...)` existen en 1.64 pero NO en 1.60, así que no se usan.
"""
import numpy as np
import pandas as pd
import streamlit as st

from utils.formatters import (PRIMARIO, TINTA, ACENTO, ACENTO_LT, CLARO, PALIDO,
                              FONDO_SUAVE, cop, num, pct, signo)

# Las mismas de config.toml. Se repiten aquí porque los objetos de Plotly que se
# construyen a mano no leen el tema.
SERIE = ["#0E113A", "#CE6264", "#2B7A9B", "#B5762F",
         "#7D5BA6", "#2f7a48", "#8B1E1E", "#9193A1"]
VERDE, AMBAR, ROJO = "#2f7a48", "#B5762F", "#8B1E1E"


# ── Tarjetas de indicador ────────────────────────────────────────────────────
def fila_metricas(items, gap="medium"):
    """Una fila de indicadores nativos, con tendencia dentro de cada uno.

    `items` es una lista de dicts:
        {"label", "value", "delta", "ayuda", "serie", "tipo", "bueno"}

    La ventaja sobre las tarjetas de HTML no es estética: `st.metric` hereda el
    tema, así que el día que alguien abra el panel en modo oscuro sigue
    legible. Las de HTML tienen los colores quemados y se ven rotas.
    """
    fila = st.container(horizontal=True, gap=gap)
    with fila:
        for it in items:
            st.metric(
                label=it["label"],
                value=it["value"],
                delta=it.get("delta"),
                delta_color=("normal" if it.get("bueno", True) else "inverse"),
                help=it.get("ayuda"),
                chart_data=it.get("serie"),
                chart_type=it.get("tipo", "area"),
                border=True,
                width="stretch",
            )


# ── Gráficos en los que se puede hacer clic ──────────────────────────────────
def grafico_seleccionable(fig, clave, altura=380, modo=("points",)):
    """Un gráfico de Plotly que devuelve lo que el usuario seleccionó.

    Devuelve la lista de `customdata` de los puntos elegidos, que es la forma
    práctica de llevar una identidad —el nombre de la cuenta, el SKU— desde la
    traza hasta el código que abre el detalle.

    Para que funcione, la traza tiene que llevar `customdata` con el
    identificador en la primera posición.
    """
    ev = st.plotly_chart(fig, key=clave, on_select="rerun",
                         selection_mode=modo, width="stretch", height=altura)
    try:
        puntos = ev["selection"]["points"]
    except (KeyError, TypeError):
        return []
    fuera = []
    for p in puntos:
        cd = p.get("customdata")
        if cd is None:
            continue
        fuera.append(cd[0] if isinstance(cd, (list, tuple)) else cd)
    return fuera


def pista_clic(texto="Haz clic en cualquier punto para abrir su ficha"):
    """El aviso de que el gráfico es interactivo.

    Hace falta decirlo: nadie hace clic en un gráfico por su cuenta, porque
    veinte años de informes le enseñaron que los gráficos no hacen nada.
    """
    st.markdown(
        f'<div style="display:inline-flex;align-items:center;gap:6px;'
        f'background:{FONDO_SUAVE};border:1px solid {PALIDO};border-radius:99px;'
        f'padding:4px 12px;font-size:11px;color:{CLARO};margin:-4px 0 10px;'
        f'font-family:Montserrat,sans-serif">'
        f'<span style="width:5px;height:5px;border-radius:50%;'
        f'background:{ACENTO};display:inline-block"></span>{texto}</div>',
        unsafe_allow_html=True)


# ── Tablas que son bandejas de trabajo ───────────────────────────────────────
def tabla(df, config=None, altura_fila=38, clave=None, seleccionable=False):
    """`st.dataframe` con los tipos de columna que ya existen y no se usaban.

    Una tabla con barras de progreso y minigráficos dentro no es decoración:
    deja leer cincuenta filas de un vistazo sin tener que comparar números
    mentalmente, que es exactamente lo que un gerente hace a las siete de la
    mañana.
    """
    kw = dict(hide_index=True, width="stretch", row_height=altura_fila)
    if config:
        kw["column_config"] = config
    if seleccionable:
        kw.update(on_select="rerun", selection_mode="single-row", key=clave)
    elif clave:
        kw["key"] = clave
    return st.dataframe(df, **kw)


def col_progreso(label, maximo, formato="percent"):
    return st.column_config.ProgressColumn(label, min_value=0, max_value=maximo,
                                           format=formato)


def col_tendencia(label, tipo="bar"):
    C = {"bar": st.column_config.BarChartColumn,
         "line": st.column_config.LineChartColumn,
         "area": st.column_config.AreaChartColumn}[tipo]
    return C(label)


def col_semaforo(label):
    """Columna de texto con insignia de color. El estado se lee sin leer."""
    return st.column_config.MarkdownColumn(label)


def badge(texto, tono="gray"):
    """Insignia de color para meter dentro de una MarkdownColumn."""
    return f":{tono}-badge[{texto}]"


# ── Fichas de detalle ────────────────────────────────────────────────────────
def ficha(titulo, ancho="large", icono=None):
    """Decorador para abrir un detalle sin salir de la pantalla.

    Sirve para lo que el revisor pedía: *«si no puedo bajar hasta la factura,
    yo no puedo pelear con ese número y entonces no sirve para decidir nada»*.
    """
    return st.dialog(titulo, width=ancho, icon=icono)


# ── Encabezado de sección ────────────────────────────────────────────────────
def seccion(titulo, ayuda=""):
    """Separador de sección con jerarquía real, no un <b> suelto."""
    extra = (f'<span style="font-size:11px;color:{CLARO};font-weight:500;'
             f'margin-left:10px">{ayuda}</span>' if ayuda else "")
    st.markdown(
        f'<div style="display:flex;align-items:baseline;gap:4px;'
        f'margin:22px 0 10px;padding-bottom:7px;'
        f'border-bottom:1px solid {PALIDO}">'
        f'<span style="font-family:Montserrat,sans-serif;font-size:11px;'
        f'font-weight:800;letter-spacing:.14em;text-transform:uppercase;'
        f'color:{TINTA}">{titulo}</span>{extra}</div>',
        unsafe_allow_html=True)


# ── El número grande ─────────────────────────────────────────────────────────
def titular(etiqueta, valor, apoyo="", tono=PRIMARIO):
    """Un solo número, grande, cuando la pantalla tiene una sola conclusión.

    Cuatro tarjetas iguales no tienen jerarquía: el ojo no sabe cuál mirar
    primero. Cuando una pantalla contesta una pregunta, el número va solo.
    """
    st.markdown(
        f'<div style="background:{tono};color:#fff;border-radius:8px;'
        f'padding:22px 26px;margin-bottom:16px">'
        f'<div style="font-family:Montserrat,sans-serif;font-size:10px;'
        f'letter-spacing:.17em;text-transform:uppercase;opacity:.65">{etiqueta}</div>'
        f'<div style="font-family:\'DM Serif Display\',Georgia,serif;'
        f'font-size:42px;line-height:1.08;margin:5px 0 3px">{valor}</div>'
        f'<div style="font-size:12.5px;opacity:.78">{apoyo}</div></div>',
        unsafe_allow_html=True)


# ── Mapa de zonas ────────────────────────────────────────────────────────────
# Coordenadas reales de las zonas donde opera KYVA. No son polígonos: son los
# centroides, que es lo honesto sin descargar cartografía y alcanza de sobra
# para ver dónde está la plata y dónde cuesta repartir.
ZONAS_GEO = {
    "Zona G":        (4.6486, -74.0630), "Zona T":      (4.6668, -74.0540),
    "Parque 93":     (4.6769, -74.0490), "Usaquén":     (4.6950, -74.0310),
    "Chapinero":     (4.6420, -74.0630), "Chicó":       (4.6830, -74.0450),
    "Macarena":      (4.6150, -74.0660), "Candelaria":  (4.5970, -74.0740),
    "Cedritos":      (4.7160, -74.0350), "Salitre":     (4.6580, -74.1060),
    "El Poblado":    (6.2090, -75.5710), "Provenza":    (6.2090, -75.5670),
    "Laureles":      (6.2450, -75.5920), "Envigado":    (6.1690, -75.5830),
    "Las Palmas":    (6.1930, -75.5330), "Centro":      (6.2510, -75.5670),
}


def mapa_zonas(df, col_zona="zona", col_valor="neto", col_ciudad="ciudad",
               ciudad="Bogotá", altura=440, etiqueta="Venta"):
    """Las zonas en un mapa, con la altura de cada columna según su valor.

    Sin proveedor de teselas (`map_provider=None`): no hace falta llave de API
    ni que ningún servicio externo esté disponible, que es lo que importa en un
    panel que tiene que abrir siempre.
    """
    try:
        import pydeck as pdk
    except ImportError:
        st.info("El mapa necesita pydeck, que viene con Streamlit.")
        return

    d = df[df[col_ciudad] == ciudad] if col_ciudad in df.columns else df
    g = d.groupby(col_zona)[col_valor].sum().reset_index()
    g["lat"] = g[col_zona].map(lambda z: ZONAS_GEO.get(z, (None, None))[0])
    g["lon"] = g[col_zona].map(lambda z: ZONAS_GEO.get(z, (None, None))[1])
    g = g.dropna(subset=["lat", "lon"])
    if g.empty:
        st.info(f"Sin zonas ubicadas en {ciudad}.")
        return

    tope = float(g[col_valor].max()) or 1.0
    g["altura"] = (g[col_valor] / tope * 2600).clip(lower=120)
    g["radio"] = 165
    g["etiqueta"] = g[col_valor].map(lambda v: cop(v, 0))
    # Del pálido de marca al navy, según cuánto pesa la zona.
    g["color"] = g[col_valor].map(
        lambda v: [int(229 - 215 * v / tope), int(225 - 208 * v / tope),
                   int(230 - 172 * v / tope), 205])

    centro = (4.66, -74.06) if ciudad == "Bogotá" else (6.21, -75.57)
    capa = pdk.Layer(
        "ColumnLayer", data=g, get_position=["lon", "lat"],
        get_elevation="altura", elevation_scale=1, radius=180,
        get_fill_color="color", pickable=True, auto_highlight=True, extruded=True)
    st.pydeck_chart(pdk.Deck(
        layers=[capa],
        initial_view_state=pdk.ViewState(latitude=centro[0], longitude=centro[1],
                                         zoom=11.4 if ciudad == "Bogotá" else 12.2,
                                         pitch=48, bearing=-12),
        map_provider=None, map_style=None,
        tooltip={"html": "<b>{" + col_zona + "}</b><br>" + etiqueta + ": {etiqueta}",
                 "style": {"backgroundColor": "#0E113A", "color": "#fff",
                           "fontSize": "12px", "borderRadius": "4px"}},
    ), height=altura)
