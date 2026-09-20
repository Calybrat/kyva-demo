"""
Paleta e identidad visual de KYVA.

Los colores NO se eligieron a ojo: son las variables globales que declara el
tema de kyva.co (Elementor) y coinciden con los dos rellenos del logo SVG que
sirve el propio sitio:

  --e-global-color-primary    #0E113A   azul noche (el círculo del logo)
  --e-global-color-secondary  #CE6264   coral
  --e-global-color-accent     #9193A1   gris lila
  --e-global-color-7a6928a    #E5E1E6   lavanda (las letras del logo)

Tipografías del sitio: Montserrat (títulos), Source Sans Pro (texto) y
DM Serif Display (acento, es la serifa del logotipo).

El motivo de la marca es el CÍRCULO: el logo es un círculo, el lema es
«join the circle» y el programa de referidos se llama «Mi Círculo». Por eso los
encabezados llevan círculos concéntricos y no un adorno genérico.
"""
import base64
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

# ── Paleta de marca ──────────────────────────────────────────────────────────
PRIMARIO   = "#0E113A"   # --e-global-color-primary (círculo del logo)
TINTA      = "#0E113A"   # la barra lateral ES el círculo del logo
CLARO      = "#9193A1"   # --e-global-color-accent
PALIDO     = "#E5E1E6"   # --e-global-color-7a6928a (letras del logo)
FONDO_SUAVE = "#F4F2F5"
ACENTO     = "#CE6264"   # --e-global-color-secondary
ACENTO_LT  = "#F6DEDE"
# ── fin de la paleta ──

# Alias para no reescribir los módulos cuando cambia la marca.
AZUL, AZUL_DEEP, AZUL_LT, AZUL_PALE, AZUL_BG = (
    PRIMARIO, TINTA, CLARO, PALIDO, FONDO_SUAVE)
NARANJA, NARANJA_LT = ACENTO, ACENTO_LT
CORAL, LAVANDA, LILA = ACENTO, PALIDO, CLARO
TINTA_SOFT = "#2B2F5E"

# Roles de superficie (tema claro, como el sitio)
BG      = "#FAF9FB"
SURF    = "#FFFFFF"
SURF2   = "#F4F2F5"
BORDER  = "#E4E0E8"
TEXT    = TINTA
MUTED   = "#69727D"   # gris de texto que declara el CSS de kyva.co
DIM     = "#A9A6B2"

# Semánticos
GOOD  = "#1E9E74"
WARN  = "#D99A2B"
BAD   = "#C94A4C"
INFO  = "#4F5BB5"
GREEN, AMBER, RED, SKY = GOOD, WARN, BAD, "#4F5BB5"
MORADO = "#6A5A9E"
TEAL   = "#3E8E8A"

PALETTE = [PRIMARIO, ACENTO, CLARO, "#4F5BB5", "#D9A7A8", TEAL, "#C9C4D3", GOOD]

# Un color por canal, el MISMO en todas las gráficas del panel.
PALETTE_SEGMENTO = {
    "The Store": PRIMARIO,
    "The Lounge": ACENTO,
    "Corporativo": "#4F5BB5",
    "Distribución": CLARO,
}
ICONOS = {"The Store": "🛍️", "The Lounge": "🥂", "Corporativo": "🎁", "Distribución": "🚚"}

_ASSETS = Path(__file__).parent.parent / "assets"
_DATA = Path(__file__).parent.parent / "data"


def leer_csv(nombre: str, **kw) -> pd.DataFrame:
    """Lee un archivo de data/, esté comprimido (.csv.gz) o no."""
    kw.setdefault("low_memory", False)
    for candidato in (_DATA / nombre, _DATA / f"{nombre}.gz"):
        if candidato.exists():
            return pd.read_csv(candidato, **kw)
    raise FileNotFoundError(f"No se encontró {nombre} en {_DATA}")


def asset_b64(nombre: str) -> str:
    """Devuelve un asset de marca como data URI listo para <img src=...>."""
    ruta = _ASSETS / nombre
    if not ruta.exists():
        return ""
    mime = "image/svg+xml" if ruta.suffix == ".svg" else "image/png"
    return f"data:{mime};base64,{base64.b64encode(ruta.read_bytes()).decode()}"


# ── Formato de cifras (a la colombiana: punto de miles, coma decimal) ────────
def _co(texto: str) -> str:
    return texto.replace(",", "§").replace(".", ",").replace("§", ".")


def num(v, decimals=0) -> str:
    try:
        return _co(f"{float(v):,.{decimals}f}")
    except (TypeError, ValueError):
        return "—"


def cop(v, decimals=None) -> str:
    """Pesos, legible para quien no es analista.

    $10.585 M (millones, sin decimales desde mil millones) · $456,3 M · $265.900
    """
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "—"
    s = "-" if v < 0 else ""
    a = abs(v)
    if a >= 1_000_000_000:
        return f"{s}${_co(f'{a/1e6:,.0f}')} M"
    if a >= 1_000_000:
        d = 1 if decimals is None else decimals
        return f"{s}${_co(f'{a/1e6:,.{d}f}')} M"
    return f"{s}${_co(f'{a:,.0f}')}"


usd = cop   # compatibilidad con la plantilla: en KYVA todo se reporta en pesos


def miles(v) -> str:
    try:
        return _co(f"{float(v):,.0f}")
    except (TypeError, ValueError):
        return "—"


def pct(v, decimals=1) -> str:
    try:
        return _co(f"{float(v):.{decimals}f}") + "%"
    except (TypeError, ValueError):
        return "—"


def signo(v, decimals=1) -> str:
    try:
        return ("+" if float(v) >= 0 else "") + pct(v, decimals)
    except (TypeError, ValueError):
        return "—"


MESES_ES = ["ene", "feb", "mar", "abr", "may", "jun",
            "jul", "ago", "sep", "oct", "nov", "dic"]
DIAS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def mes_es(m: str) -> str:
    """'2026-08' → 'ago 2026'"""
    try:
        a, b = str(m).split("-")[:2]
        return f"{MESES_ES[int(b)-1]} {a}"
    except Exception:
        return str(m)


# ── Plotly ───────────────────────────────────────────────────────────────────
def light(fig: go.Figure, height: int = 340, title: str = "", moneda: bool = False) -> go.Figure:
    """Tema claro de KYVA para una figura de Plotly.

    La leyenda nunca va arriba: pelea el espacio del título. Va debajo (barras
    y líneas) o a la derecha (donas), con margen reservado según el largo de
    las etiquetas del eje X, para que no se les monte encima.

    `moneda=True` pasa el eje Y principal a millones de pesos ("$1.500 M").
    Sin esto Plotly escribe "1,5B" — y en español una B se lee como BILLÓN,
    mil veces más de lo que es.
    """
    if moneda:
        # El eje del VALOR no siempre es el Y. En una barra horizontal el Y son
        # las categorías, y aplicarle el formato de moneda produce etiquetas
        # como «$Julián Mora M». Salió publicado y lo cazó una auditoría de
        # diseño: un error así hace que el lector deje de creerle a las cifras
        # de al lado, que es un daño mucho mayor que el del propio eje.
        horizontal = any(getattr(tr, "orientation", None) == "h" for tr in fig.data)
        eje = "x" if horizontal else "y"
        for tr in fig.data:
            if getattr(tr, f"{eje}axis", None) not in (None, eje):
                continue
            vals = getattr(tr, eje, None)
            if vals is not None:
                setattr(tr, eje, [v / 1e6 if v is not None else None for v in vals])
                tr.hovertemplate = ("$%{" + eje + ":,.1f} M<extra>"
                                    + (tr.name or "") + "</extra>")
        fig.update_layout(**{f"{eje}axis": dict(tickprefix="$", ticksuffix=" M",
                                                tickformat=",.0f")})
    is_pie = any(getattr(tr, "type", None) == "pie" for tr in fig.data)
    n_cat = 0
    n_entries = 0
    for tr in fig.data:
        if getattr(tr, "type", None) == "pie":
            labels = tr.labels
            n_entries += len(labels) if labels is not None else 0
        elif getattr(tr, "name", None) and getattr(tr, "showlegend", None) is not False:
            n_entries += 1
    show_legend = is_pie or n_entries > 1

    if is_pie:
        legend = dict(orientation="v", x=1.02, y=0.5, xanchor="left",
                      yanchor="middle", font=dict(color=MUTED, size=11))
        margin = dict(l=6, r=150, t=44 if title else 16, b=16)
    else:
        etiquetas = []
        for tr in fig.data:
            xs = getattr(tr, "x", None)
            if xs is not None and getattr(tr, "orientation", None) != "h":
                etiquetas += [str(v) for v in xs if isinstance(v, str)]
        largo = max((len(e) for e in etiquetas), default=0)
        n_cat = len(set(etiquetas))
        alto_ticks = int(min(58, largo * 5.6)) if largo > 4 and n_cat > 8 else 0

        if show_legend:
            rows = 1 if n_entries <= 4 else (2 if n_entries <= 8 else 3)
            base_b = 46 + 26 * rows + alto_ticks
            legend = dict(orientation="h",
                          y=-0.20 - 0.11 * (rows - 1) - alto_ticks / 420,
                          x=0.5, xanchor="center", yanchor="top",
                          font=dict(color=MUTED, size=11))
        else:
            base_b = 20 + alto_ticks
            legend = dict()
        margin = dict(l=6, r=30, t=44 if title else 16, b=base_b)

    # `hovermode="x unified"` estaba puesto para todo, y en una barra horizontal
    # agrupa por el eje equivocado: junta valores que no tienen nada que ver.
    # En una dona directamente no significa nada.
    horizontal = any(getattr(tr, "orientation", None) == "h" for tr in fig.data)
    modo_hover = "closest" if is_pie else ("y unified" if horizontal else "x unified")

    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color=TINTA,
                                         family="Montserrat, sans-serif"),
                   x=0, xanchor="left"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        # La familia que SÍ está cargada. Antes decía 'Source Sans Pro' pero el
        # @import trae 'Source Sans 3': los ejes se renderizaban con una fuente
        # de reserva distinta a la de la interfaz, y se notaba en cada gráfico.
        font=dict(family="'Source Sans 3', -apple-system, system-ui, sans-serif",
                  color=MUTED, size=12),
        separators=",.",
        height=height, margin=margin, legend=legend, showlegend=show_legend,
        hovermode=modo_hover, colorway=PALETTE,
        # Barras delgadas: la barra nunca llena su ranura. Es la diferencia
        # entre un gráfico de hoja de cálculo y uno compuesto.
        bargap=0.42, bargroupgap=0.12,
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=BORDER, align="left",
                        font=dict(family="'Source Sans 3', sans-serif",
                                  size=12.5, color=TINTA)),
        dragmode=False,
    )
    fig.update_xaxes(showgrid=False, showline=False, zeroline=False,
                     ticks="outside", ticklen=4, tickcolor="rgba(0,0,0,0)",
                     tickfont=dict(color=MUTED, size=11.5), automargin=True)
    if not is_pie and n_cat > 14:
        fig.update_xaxes(nticks=9)
    fig.update_yaxes(showgrid=True, gridcolor="#EFEDF2", gridwidth=1,
                     showline=False, zeroline=False,
                     tickfont=dict(color=MUTED, size=11.5), automargin=True)
    # El hueco de 2px entre segmentos apilados no es un borde decorativo: es una
    # línea del color de la superficie, que es como se consigue en Plotly.
    fig.update_traces(cliponaxis=False, marker_line_color=SURF,
                      marker_line_width=1.5, selector=dict(type="bar"))
    if is_pie:
        fig.update_traces(hole=0.62, marker_line_color=SURF, marker_line_width=2,
                          selector=dict(type="pie"))
    return fig


# La barra flotante de Plotly es la firma visual más delatora que tiene un
# panel: aparece al pasar el mouse con el logo, el zoom y «download plot as
# png». Ningún producto real la muestra.
PLOTLY_CONFIG = {"displayModeBar": False, "displaylogo": False,
                 "scrollZoom": False, "doubleClick": False,
                 "showTips": False}


def grafico(fig, altura=340, moneda=False, titulo=""):
    """Dibuja una figura ya tematizada. Úsese en vez de st.plotly_chart.

    Dos cosas que hace y que a mano se olvidan siempre:

      · `theme=None` — sin esto Streamlit repinta su propio tema ENCIMA del que
        acabamos de aplicar, y el resultado es una mezcla de los dos.
      · `config` — esconde la modebar.

    El título va como encabezado de sección ANTES del gráfico, no dentro de la
    figura: dentro usa la tipografía de Plotly y no la del producto.
    """
    import streamlit as st
    if titulo:
        st.markdown(f'<div class="ky-sub">{titulo}</div>', unsafe_allow_html=True)
    return st.plotly_chart(light(fig, altura, moneda=moneda), width="stretch",
                           theme=None, config=PLOTLY_CONFIG)


dark = light


# ── Componentes de UI ────────────────────────────────────────────────────────
def kpi(label: str, value: str, delta: str = "", delta_good: bool = True,
        icon: str = "", ayuda: str = "", referencia: str = "") -> str:
    """Tarjeta de KPI.

    `referencia` dice contra qué comparar ("Sano en retail: 20–25%") y `ayuda`
    explica en una línea qué significa. Un número solo no le sirve a nadie.
    """
    # `icon` se conserva por compatibilidad pero no se dibuja: un emoji por
    # tarjeta viene de una familia tipográfica distinta y mete color fuera de
    # la paleta.
    #
    # Y el cambio de fondo: `ayuda` y `referencia` YA NO van dentro de la
    # tarjeta. Un párrafo explicativo dentro de un indicador es, según la
    # investigación de sistemas de diseño, el defecto que más abarata un panel
    # —y este tenía hasta tres líneas de texto en cada una de las cuatro—.
    # Van al tooltip de un icono de 14px. La anatomía canónica es: etiqueta,
    # cifra, delta. Nada más.
    color = GOOD if delta_good else BAD
    tip = " · ".join(x for x in (ayuda, referencia) if x).replace('"', "&quot;")
    ayuda_html = (f'<span class="ky-ayuda" title="{tip}">?</span>' if tip else "")
    delta_html = (f'<p class="ky-dlt" style="color:{color}">{delta}</p>'
                  if delta else "")
    return (f'<div class="ky-t ky-kpi"><p class="ky-lbl">{label}{ayuda_html}</p>'
            f'<p class="ky-val">{value}</p>{delta_html}</div>')


def panel(titulo: str, cuerpo_html: str, icono: str = "", tono: str = "azul") -> str:
    """Panel de lectura del dato: qué dice y qué habría que decidir.

    El `<p>` del encabezado se había quedado vacío y con eso las 27 pantallas
    perdían el titular del panel —justo la frase en la que cada módulo apuesta
    su tesis— y mostraban el cuerpo empezando en el aire. `icono` sigue sin
    dibujarse, por la misma razón que en `kpi`: veintisiete emoji distintos son
    veintisiete familias tipográficas peleando entre sí.
    """
    borde = {"azul": PALIDO, "alerta": "#EFC3C4", "ok": "#BFE3D5",
             "naranja": "#F1D3B0"}.get(tono, PALIDO)
    fondo = {"azul": FONDO_SUAVE, "alerta": "#FBF0F0", "ok": "#EEF8F4",
             "naranja": "#FDF6EC"}.get(tono, FONDO_SUAVE)
    return f"""
    <div style="background:{fondo};border:1px solid {borde};border-radius:16px;
      padding:16px 19px;margin:6px 0 2px">
      <p style="font-size:13.5px;font-weight:700;color:{TINTA};margin:0 0 8px;
        font-family:Montserrat,sans-serif">{titulo}</p>
      <div style="font-size:13.5px;color:#3E4260;margin:0;line-height:1.7">
        {cuerpo_html}</div>
    </div>"""


def chip(texto: str, tono: str = "azul") -> str:
    c = {"azul": (FONDO_SUAVE, TINTA, PALIDO),
         "ok": ("#EEF8F4", "#16724F", "#BFE3D5"),
         "alerta": ("#FBF0F0", "#A53A3C", "#EFC3C4"),
         "naranja": ("#FDF6EC", "#9A6414", "#F1D3B0"),
         "neutro": (SURF2, MUTED, BORDER)}.get(tono, (FONDO_SUAVE, TINTA, PALIDO))
    return (f'<span style="display:inline-block;background:{c[0]};color:{c[1]};'
            f'border:1px solid {c[2]};border-radius:999px;padding:3px 11px;'
            f'font-size:11px;font-weight:700;margin:2px 4px 2px 0">{texto}</span>')


def semaforo(valor: float, bueno: float, malo: float, invertido: bool = False) -> str:
    if invertido:
        return GOOD if valor <= bueno else (WARN if valor <= malo else BAD)
    return GOOD if valor >= bueno else (WARN if valor >= malo else BAD)


def estado_color(estado: str) -> str:
    m = {"Activo": GOOD, "En riesgo": WARN, "Dormido": BAD, "Cancelado": BAD,
         "Ganada": GOOD, "Perdida": BAD, "Abierta": WARN, "Entregado": GOOD}
    return m.get(estado, MUTED)


def espacio(px: int = 16) -> str:
    return f"<div style='height:{px}px'></div>"


# ── Motivo de marca: el círculo ──────────────────────────────────────────────
def motivo_svg(color: str = PRIMARIO, ancho: int = 26, opacidad: float = 1.0) -> str:
    """Tres círculos: el logo, «join the circle», Mi Círculo."""
    r = ancho / 2
    return (f'<svg width="{ancho}" height="{ancho}" viewBox="0 0 {ancho} {ancho}" '
            f'fill="none" style="opacity:{opacidad};vertical-align:middle">'
            f'<circle cx="{r}" cy="{r}" r="{r-1}" stroke="{color}" stroke-width="1.2"/>'
            f'<circle cx="{r}" cy="{r}" r="{r*.62}" stroke="{color}" stroke-width="1.2"/>'
            f'<circle cx="{r}" cy="{r}" r="{r*.26}" fill="{color}"/></svg>')


CSS = f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&family=Source+Sans+3:wght@400;600;700&family=DM+Serif+Display&display=swap');
  html, body, [class*="css"] {{ font-family:'Source Sans 3','Source Sans Pro',-apple-system,system-ui,sans-serif; }}
  .stApp {{ background:{BG}; color:{TEXT}; }}

  section[data-testid="stSidebar"] {{
      background:linear-gradient(180deg,{TINTA} 0%,#080A28 100%); border-right:none; }}
  section[data-testid="stSidebar"] * {{ color:{PALIDO}; }}
  section[data-testid="stSidebar"] .stButton button {{
      background:rgba(229,225,230,.04); color:{PALIDO} !important;
      border:1px solid rgba(229,225,230,.12); border-radius:999px;
      text-align:left; font-weight:600; font-size:12.5px; padding:6px 14px;
      font-family:Montserrat,sans-serif; transition:all .15s ease; }}
  section[data-testid="stSidebar"] .stButton button:hover {{
      background:{ACENTO}33; border-color:{ACENTO}; color:#fff !important; }}

  .block-container {{ padding-top:1.5rem !important; max-width:1500px; }}
  h1,h2,h3,h4,h5 {{ color:{TINTA} !important; font-family:Montserrat,sans-serif !important;
      font-weight:700 !important; letter-spacing:-.2px; }}
  div[data-testid="stMetricValue"] {{ color:{TINTA}; }}

  .stDataFrame {{ border-radius:12px; overflow:hidden; border:1px solid {BORDER}; }}
  div[data-baseweb="select"] > div {{ background:{SURF} !important;
      border-color:{BORDER} !important; border-radius:10px !important; }}
  div[data-baseweb="select"] span {{ color:{TINTA} !important; }}
  .stMultiSelect span[data-baseweb="tag"] {{ background:{PRIMARIO} !important; color:#fff !important; }}
  .stMultiSelect span[data-baseweb="tag"] span {{ color:#fff !important;
      -webkit-text-fill-color:#fff !important; }}
  button[kind="primary"] {{ background:{PRIMARIO} !important; border:none !important;
      border-radius:999px !important; font-weight:600 !important; }}

  .stTabs [data-baseweb="tab"] {{ background:{SURF2}; border-radius:11px 11px 0 0;
      font-weight:600; color:{MUTED}; font-size:13px; font-family:Montserrat,sans-serif; }}
  .stTabs [aria-selected="true"] {{ background:{SURF} !important; color:{TINTA} !important;
      border-bottom:2px solid {ACENTO}; }}
  div[data-testid="stExpander"] {{ border:1px solid {BORDER} !important;
      background:{SURF} !important; border-radius:13px !important; }}
  div[data-testid="stExpander"] summary {{ font-weight:700; color:{TINTA} !important; }}
  label, .stSelectbox label, .stSlider label {{ color:{MUTED} !important;
      font-weight:600 !important; font-size:12px !important; }}
  hr {{ border-color:{BORDER}; }}
  .stProgress > div > div > div > div {{ background:{ACENTO}; }}
</style>
"""

HEADER_CSS = f"""
<style>
  .ky-header {{ display:flex;align-items:center;gap:18px;padding:2px 0 }}
  .ky-logo {{ height:54px;width:54px }}
  .ky-title {{ font-family:'DM Serif Display',Georgia,serif;font-size:29px;color:{TINTA};
      letter-spacing:.1px;line-height:1.1 }}
  .ky-sub {{ font-size:13.5px;color:{MUTED};margin-top:4px;font-weight:500 }}
  .ky-rule {{ height:2px;border-radius:99px;
      background:linear-gradient(90deg,{PRIMARIO} 0%,{CLARO} 45%,{ACENTO} 75%,transparent);
      margin:14px 0 20px }}
  .ky-eyebrow {{ font-size:10px;font-weight:700;letter-spacing:.18em;font-family:Montserrat,sans-serif;
      text-transform:uppercase;color:{ACENTO};margin-bottom:3px }}
</style>
"""


def encabezado(titulo: str, subtitulo: str, eyebrow: str = "Panel de negocio") -> str:
    """Encabezado de módulo con el logo real de KYVA (el SVG de kyva.co)."""
    logo = asset_b64("logo_color.svg")
    logo_html = (f'<img src="{logo}" class="ky-logo" alt="KYVA">' if logo
                 else f'<div class="ky-title">KYVA</div>')
    return f"""
    <div class="ky-header">
      {logo_html}
      <div style="border-left:1px solid {PALIDO};padding-left:18px">
        <div class="ky-eyebrow">{eyebrow}</div>
        <div class="ky-title">{titulo}</div>
        <div class="ky-sub">{subtitulo}</div>
      </div>
      <div style="margin-left:auto;display:flex;gap:6px;align-items:center">
        {motivo_svg(PALIDO, 38)}{motivo_svg(CLARO, 26)}{motivo_svg(ACENTO, 16)}
      </div>
    </div><div class="ky-rule"></div>"""

# ── Correcciones de diseño ───────────────────────────────────────────────────
# Sale de una auditoría de dirección de diseño. Va al final del CSS a propósito:
# gana por orden en la cascada sin tener que subir especificidad a golpe de
# !important en las reglas de arriba.
CSS_PRODUCTO = f"""
<style>
:root {{ --t:120ms cubic-bezier(.2,0,.2,1); --linea:#E9E5EE; --linea-fuerte:#D9D3DF; }}

/* Las cuatro tarjetas de KPI quedaban con el borde inferior desparejo cuando
   los textos de ayuda tenían largos distintos. `height:100%` en la tarjeta no
   basta: los hijos de stColumn no se estiran si no se les dice. */
[data-testid="stHorizontalBlock"] {{ align-items:stretch !important; }}
[data-testid="stColumn"] {{ display:flex !important; }}
[data-testid="stColumn"] > div {{ width:100%; display:flex; flex-direction:column; }}
[data-testid="stColumn"] [data-testid="stVerticalBlock"],
[data-testid="stColumn"] [data-testid="stElementContainer"],
[data-testid="stColumn"] [data-testid="stMarkdown"],
[data-testid="stColumn"] [data-testid="stMarkdownContainer"] {{
  height:100%; display:flex; flex-direction:column;
}}
/* Columnas ANIDADAS —el titular y sus tres apoyos— necesitan su propia regla:
   el stretch del bloque exterior no llega al interior y las tres de apoyo
   volvían a quedar con el borde inferior desparejo. */
[data-testid="stColumn"] [data-testid="stHorizontalBlock"] {{
  align-items:stretch !important; height:100%;
}}
[data-testid="stColumn"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{
  display:flex !important;
}}
.ky-kpi, .ky-hero-card {{ flex:1 1 auto; }}

/* El foco de teclado era el azul por defecto de Streamlit, que no es de la
   marca. Y nunca outline:none — deja la app inutilizable sin ratón. */
:focus-visible {{ outline:2px solid {ACENTO}; outline-offset:2px; border-radius:4px; }}
::selection {{ background:rgba(206,98,100,.2); color:{TINTA}; }}

/* ── Navegación ───────────────────────────────────────────────────────────
   El selector `button[kind="primary"]` que había en el CSS es código muerto
   desde Streamlit 1.35: el DOM ahora usa data-testid. Se ponen los dos para
   cubrir ambas versiones. */
section[data-testid="stSidebar"] [data-testid="stButton"] > button {{
  background:transparent !important; border:none !important;
  border-left:2px solid transparent !important; border-radius:0 7px 7px 0 !important;
  padding:6px 12px 6px 14px !important; min-height:0 !important;
  justify-content:flex-start !important;
  font:500 12.5px/1.35 Montserrat,sans-serif !important; letter-spacing:-.01em;
  color:rgba(229,225,230,.62) !important; box-shadow:none !important;
  transition:background var(--t), color var(--t), border-color var(--t);
}}
section[data-testid="stSidebar"] [data-testid="stButton"] > button p,
section[data-testid="stSidebar"] [data-testid="stButton"] > button div,
section[data-testid="stSidebar"] [data-testid="stButton"] > button span,
section[data-testid="stSidebar"] [data-testid="stButton"] > button * {{
  text-align:left !important; width:100% !important; margin:0 !important;
  justify-content:flex-start !important;
}}
section[data-testid="stSidebar"] [data-testid="stButton"] > button:hover {{
  background:rgba(229,225,230,.07) !important; color:#F3F1F4 !important;
  border-left-color:rgba(229,225,230,.3) !important;
}}
section[data-testid="stSidebar"] button[kind="primary"],
section[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] {{
  background:rgba(206,98,100,.16) !important;
  border-left:2px solid {ACENTO} !important;
  color:#FFFFFF !important; font-weight:600 !important;
}}

/* ── Botones del cuerpo ──────────────────────────────────────────────────── */
[data-testid="stMain"] button[kind="primary"],
[data-testid="stMain"] button[data-testid="stBaseButton-primary"] {{
  background:{ACENTO} !important; border:1px solid {ACENTO} !important;
  color:#fff !important; border-radius:999px !important;
  font:600 12.5px Montserrat,sans-serif !important; box-shadow:none !important;
  transition:background var(--t), transform var(--t);
}}
[data-testid="stMain"] button[kind="primary"]:hover,
[data-testid="stMain"] button[data-testid="stBaseButton-primary"]:hover {{
  background:#BC5052 !important; transform:translateY(-1px);
}}
[data-testid="stMain"] button[kind="secondary"],
[data-testid="stMain"] button[data-testid="stBaseButton-secondary"] {{
  background:transparent !important; border:1px solid var(--linea-fuerte) !important;
  color:{TINTA} !important; border-radius:999px !important;
  font:600 12.5px Montserrat,sans-serif !important;
}}

/* ── Controles ──────────────────────────────────────────────────────────── */
div[data-baseweb="select"] > div {{
  border-color:var(--linea) !important; border-radius:8px !important;
  min-height:36px; transition:border-color var(--t);
}}
div[data-baseweb="select"]:focus-within > div {{
  border-color:{ACENTO} !important;
  box-shadow:0 0 0 3px rgba(206,98,100,.12) !important;
}}
label, .stSelectbox label, .stSlider label {{
  font:700 10px/1.3 Montserrat,sans-serif !important; letter-spacing:.13em !important;
  text-transform:uppercase; color:{CLARO} !important; margin-bottom:5px !important;
}}

/* ── Cifras en columna ──────────────────────────────────────────────────── */
/* Sin esto el ojo tiene que recalcular en cada fila: los dígitos de distinto
   ancho desalinean la coma y comparar dos filas deja de ser instantáneo. */
[data-testid="stDataFrame"], .ky-num, .ky-tabla .num {{
  font-variant-numeric:tabular-nums; font-feature-settings:"tnum";
}}

/* La toolbar de cada elemento (los tres puntos, descargar, pantalla completa)
   flotaba siempre visible. Aparece solo al pasar por encima. */
[data-testid="stElementToolbar"] {{ opacity:0; transition:opacity var(--t); }}
[data-testid="stElementContainer"]:hover [data-testid="stElementToolbar"] {{ opacity:1; }}

/* Tarjetas: una sola elevación en todo el producto, apenas perceptible. */
.ky-card, .ky-kpi {{ transition:box-shadow var(--t), border-color var(--t),
                     transform var(--t); }}
.ky-card:hover, .ky-kpi:hover {{
  box-shadow:0 2px 6px rgba(14,17,58,.07), 0 1px 2px rgba(14,17,58,.04);
  border-color:var(--linea-fuerte); transform:translateY(-1px);
}}

/* Ancho de línea. Un párrafo de 110 caracteres no se lee dos veces. */
[data-testid="stMain"] [data-testid="stMarkdownContainer"] > p,
[data-testid="stMain"] [data-testid="stCaptionContainer"] p {{ max-width:70ch; }}

/* Encabezado de sección: versalitas con hairline, no un <b> suelto. */
.ky-sub {{
  font:600 13px/18px Montserrat,sans-serif !important; letter-spacing:.08em !important;
  text-transform:uppercase; color:{TINTA} !important;
  /* 48px de aire ARRIBA: es lo que separa una sección de la anterior, y lo
     que faltaba para que el panel dejara de verse condensado. */
  margin:48px 0 16px !important; padding-bottom:12px;
  border-bottom:1px solid #EBE8EE;
}}
/* La primera sección de la pantalla no necesita el aire de arriba. */
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"]
  > [data-testid="stElementContainer"]:nth-of-type(-n+4) .ky-sub {{ margin-top:24px !important; }}
</style>
"""


def anillo(p: float, color=ACENTO, ancho: int = 22, fondo=PALIDO) -> str:
    """El círculo del logo, convertido en medidor.

    «Join the circle» deja de ser una frase del sidebar y pasa a ser el lenguaje
    de estado del producto: el anillo se llena con el avance y se cierra cuando
    la bandeja queda en cero. Es gratis, es de la marca, y ningún otro panel lo
    tiene.
    """
    r = ancho / 2 - 2
    c = 2 * 3.14159265 * r
    p = max(0.0, min(1.0, float(p)))
    return (f'<svg width="{ancho}" height="{ancho}" viewBox="0 0 {ancho} {ancho}" '
            f'style="vertical-align:middle;transform:rotate(-90deg);flex:none">'
            f'<circle cx="{ancho/2}" cy="{ancho/2}" r="{r:.1f}" fill="none" '
            f'stroke="{fondo}" stroke-width="2.5"/>'
            f'<circle cx="{ancho/2}" cy="{ancho/2}" r="{r:.1f}" fill="none" '
            f'stroke="{color}" stroke-width="2.5" stroke-linecap="round" '
            f'stroke-dasharray="{c*p:.1f} {c:.1f}"/></svg>')


def md(texto: str) -> str:
    r"""Escapa el signo de peso para texto de Markdown plano.

    Streamlit interpreta `$...$` como LaTeX. Una frase con DOS importes
    —«de $384 M en juego, $0 están asignados»— se renderiza como una fórmula
    matemática y el texto sale ilegible. Pasó en producción y se ve feo de
    inmediato.

    Solo hace falta en `st.caption`, `st.write` y `st.markdown` SIN
    `unsafe_allow_html`. Dentro de HTML el `\$` saldría literal, así que ahí
    NO se usa.
    """
    return str(texto).replace("$", r"\$")


def kpi_hero(label: str, value: str, delta: str = "", delta_good: bool = True,
             apoyo: str = "", ayuda: str = "") -> str:
    """El titular. Misma anatomía que los demás, en navy y al doble de tamaño.

    La cifra manda por TAMAÑO y por fondo, no por llevar más texto. La versión
    anterior metía un párrafo de cinco líneas dentro y eso hacía dos cosas
    malas a la vez: abarataba la tarjeta y la estiraba al doble de alto que sus
    apoyos, dejando un vacío enorme al lado. Todo eso va al tooltip.
    """
    col = "#7FD1A8" if delta_good else "#F3A6A7"
    tip = " · ".join(x for x in (apoyo, ayuda) if x).replace('"', "&quot;")
    a = (f'<span class="ky-ayuda" title="{tip}" '
         f'style="border-color:rgba(229,225,230,.35);color:rgba(229,225,230,.7)">?</span>'
         if tip else "")
    d = f'<p class="ky-dlt" style="color:{col}">{delta}</p>' if delta else ""
    return (f'<div class="ky-t ky-t--hero">'
            f'<p class="ky-lbl" style="color:rgba(229,225,230,.6)">{label}{a}</p>'
            f'<p class="ky-val ky-val--hero">{value}</p>{d}</div>')


def fila_kpi(titular_kpi: str, apoyos: list) -> None:
    """Un titular ancho a la izquierda y tres de apoyo a la derecha.

    La proporción 1,15 : 2,1 es la que hace que el titular domine sin ahogar a
    los otros tres. Con cuatro columnas iguales el ojo los lee como una lista;
    así los lee como una respuesta y su contexto.
    """
    import streamlit as st
    izq, der = st.columns([1.15, 2.1], gap="medium")
    with izq:
        st.markdown(titular_kpi, unsafe_allow_html=True)
    with der:
        cols = st.columns(len(apoyos), gap="small")
        for c, html in zip(cols, apoyos):
            c.markdown(html, unsafe_allow_html=True)
