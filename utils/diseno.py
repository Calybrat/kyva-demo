"""El sistema de diseño: tokens, tarjetas y ritmo vertical.

Nace de una investigación sobre cómo se diseñan hoy los paneles de primera
línea —Carbon de IBM, Atlassian, Polaris de Shopify, Radix, Geist de Vercel,
Linear— y de un diagnóstico que explica por qué el panel anterior se veía
condensado:

    «Un panel que se ve condensado casi siempre usa el mismo valor en todas
    partes. El aire no está en usar MÁS espacio: está en usar espacios
    DISTINTOS según el nivel jerárquico.»

Era exactamente el defecto. El panel usaba 14, 16 y 18 píxeles indistintamente
entre tarjetas, entre secciones y dentro de las tarjetas, así que todo pesaba
lo mismo y nada respiraba. Ninguna de las escalas reales es lineal: todas
saltan 16 → 24 → 32 → 48 → 64.

**La proporción que ordena el panel entero es 1 : 1 : 2.** Padding interno de la
tarjeta 24, separación entre tarjetas 24, separación entre secciones 48. Tres
valores y solo tres.

La otra corrección es la tarjeta de indicador. La anatomía canónica tiene
CUATRO cosas y ni una más: etiqueta, cifra, delta y —opcional— un visual
pequeño. Los párrafos explicativos que había dentro son, literalmente, «el
defecto que más abarata un panel». La explicación se va al tooltip.
"""
import streamlit as st

from utils.formatters import (PRIMARIO, TINTA, ACENTO, CLARO, PALIDO,
                              FONDO_SUAVE, SURF, GOOD, BAD)

# ── Espaciado ────────────────────────────────────────────────────────────────
# Escala casi geométrica, como todas las reales. No es decorativo: es lo que
# hace que un bloque se lea como hijo de otro y no como hermano.
S = {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24, "2xl": 32, "3xl": 48, "4xl": 64}

PAD_TARJETA = 24      # dentro de la tarjeta
GAP_TARJETAS = 24     # entre tarjetas hermanas
GAP_SECCION = 48      # entre bloques de distinto nivel — el que faltaba
MARGEN_PAGINA = 32
ANCHO_MAX = 1440

# ── Tipografía ───────────────────────────────────────────────────────────────
# Escala productiva de Carbon, que es la más documentada. Tres pesos y solo
# tres: 400 lectura, 500 énfasis, 600 titular. Un cuarto peso no aporta
# jerarquía, aporta ruido.
T = {
    "label":  "12px/16px",   # 500, +.02em, versalitas
    "meta":   "12.5px/18px", # 400
    "body":   "14px/20px",   # 400 — cuerpo de panel, no de blog
    "body_lg": "16px/24px",
    "h3":     "13px/18px",   # 600, +.08em, versalitas — encabezado de sección
    "kpi_sm": "22px/28px",   # 600
    "kpi":    "30px/36px",   # 600, -.02em
    "hero":   "44px/48px",   # 600, -.025em — una por pantalla
}

# Duraciones de Carbon. Nunca `linear`, nunca el `ease` por defecto.
RAPIDO, MODERADO = "110ms", "240ms"
CURVA = "cubic-bezier(.2,0,.38,.9)"


def tokens_css() -> str:
    """El CSS del sistema. Va DESPUÉS del resto para ganar por cascada."""
    return f"""
<style>
:root {{
  --s-xs:{S['xs']}px; --s-sm:{S['sm']}px; --s-md:{S['md']}px; --s-lg:{S['lg']}px;
  --s-xl:{S['xl']}px; --s-2xl:{S['2xl']}px; --s-3xl:{S['3xl']}px;
  --pad-tarjeta:{PAD_TARJETA}px; --gap-tarjetas:{GAP_TARJETAS}px;
  --gap-seccion:{GAP_SECCION}px;
  --radio:8px; --radio-sm:4px; --radio-lg:12px;
  --borde:#EBE8EE; --borde-fuerte:#DCD7E0;
  --sombra:0 1px 2px 0 rgba(14,17,58,.05);
  --sombra-hover:0 0 0 1px rgba(14,17,58,.08), 0 4px 12px rgba(14,17,58,.07);
  --rapido:{RAPIDO}; --moderado:{MODERADO}; --curva:{CURVA};
}}

/* ── Página ──────────────────────────────────────────────────────────────
   El contenido se topa a 1440 y respira 32 por los lados. Sin tope, en un
   monitor ancho las tarjetas se estiran hasta perder toda proporción. */
[data-testid="stMainBlockContainer"], .block-container {{
  max-width:{ANCHO_MAX}px !important;
  padding:{MARGEN_PAGINA}px {MARGEN_PAGINA}px 96px !important;
}}

/* ── El ritmo vertical, que es el arreglo de fondo ────────────────────────
   Streamlit mete el mismo hueco entre todos los elementos. Eso es justo lo
   que hace que un panel se sienta condensado: no hay diferencia entre dos
   cosas que van juntas y dos que no. */
[data-testid="stVerticalBlock"] {{ gap:{S['lg']}px; }}
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] {{
  gap:{S['xl']}px;
}}

/* ── Tarjetas ────────────────────────────────────────────────────────────
   Borde por defecto, sombra por excepción. Y el borde NO cambia de grosor
   al pasar por encima —solo de color— para que el contorno no tiemble. */
.ky-t {{
  background:{SURF}; border:1px solid var(--borde); border-radius:var(--radio);
  padding:var(--pad-tarjeta); height:100%;
  display:flex; flex-direction:column;
  box-shadow:var(--sombra);
  transition:border-color var(--rapido) var(--curva),
             box-shadow var(--rapido) var(--curva);
}}
.ky-t:hover {{ border-color:var(--borde-fuerte); box-shadow:var(--sombra-hover); }}

/* La cadena de altura, mirada en el DOM real en vez de adivinada.
   stColumn → stVerticalBlock → stElementContainer → stMarkdown llegan bien a
   la altura de la fila, pero DENTRO de stMarkdown hay un div sin testid con
   `align-items:center` que centra la tarjeta en lugar de estirarla. Ese es el
   único eslabón que rompía la igualdad, y no se ve sin inspeccionar. */
[data-testid="stMarkdown"] {{ align-items:stretch !important; }}
[data-testid="stMarkdown"] > div {{
  align-items:stretch !important; height:100%; width:100%;
}}
[data-testid="stMarkdownContainer"] {{ height:100%; width:100%; }}
[data-testid="stMarkdownContainer"] > .ky-t {{ flex:1 1 auto; }}
.ky-t--hero {{ background:{PRIMARIO}; border-color:{PRIMARIO}; }}

.ky-t .ky-lbl, .ky-lbl {{
  font:500 11.5px/15px Montserrat,sans-serif; letter-spacing:.04em;
  text-transform:uppercase; color:{CLARO}; margin:0;
  display:flex; align-items:center; gap:6px;
}}
.ky-t .ky-val, .ky-val {{
  font:600 30px/36px Montserrat,sans-serif; letter-spacing:-.02em;
  color:{TINTA}; margin:{S['sm']}px 0 0;
  font-variant-numeric:tabular-nums; font-feature-settings:"tnum";
}}
.ky-t .ky-val--sm, .ky-val--sm {{ font-size:22px; line-height:28px; }}
.ky-t .ky-val--hero, .ky-val--hero {{ font-size:44px; line-height:48px; letter-spacing:-.025em; color:#fff; }}
.ky-t .ky-dlt, .ky-dlt {{
  font:500 13px/18px Montserrat,sans-serif; margin:auto 0 0; padding-top:{S['sm']}px;
  font-variant-numeric:tabular-nums;
}}

/* El signo de interrogación que sustituye al párrafo dentro de la tarjeta. */
.ky-ayuda {{
  display:inline-flex; align-items:center; justify-content:center;
  width:14px; height:14px; border-radius:50%; flex:none;
  border:1px solid {PALIDO}; color:{CLARO};
  font:600 9px/1 Montserrat,sans-serif; cursor:help;
  transition:border-color var(--rapido), color var(--rapido);
}}
.ky-ayuda:hover {{ border-color:{ACENTO}; color:{ACENTO}; }}

/* ── Encabezado de sección ───────────────────────────────────────────────
   Lleva el aire ARRIBA, no abajo: es lo que separa un bloque del anterior. */
.ky-sec {{
  margin:var(--gap-seccion) 0 var(--s-lg) !important;
  padding-bottom:{S['md']}px;
  border-bottom:1px solid var(--borde);
  display:flex; align-items:baseline; justify-content:space-between; gap:{S['md']}px;
}}
.ky-t .ky-sec__t, .ky-sec__t {{
  font:600 13px/18px Montserrat,sans-serif; letter-spacing:.08em;
  text-transform:uppercase; color:{TINTA};
}}
.ky-t .ky-sec__n, .ky-sec__n {{ font:400 12.5px/18px 'Source Sans 3',sans-serif; color:{CLARO}; }}

/* ── Nota ────────────────────────────────────────────────────────────────
   Reemplaza al panel de colores. Un solo tratamiento neutro y uno de alerta:
   cuatro fondos teñidos distintos hacen que ninguno signifique nada. */
.ky-nota {{
  background:{FONDO_SUAVE}; border-left:3px solid {PALIDO};
  border-radius:0 var(--radio) var(--radio) 0;
  padding:{S['lg']}px {S['xl']}px; margin:{S['lg']}px 0;
}}
.ky-nota--alerta {{ border-left-color:{ACENTO}; background:#FCF4F4; }}
.ky-t .ky-nota__t, .ky-nota__t {{
  font:600 13px/18px Montserrat,sans-serif; color:{TINTA}; margin:0 0 {S['sm']}px;
}}
.ky-t .ky-nota__c, .ky-nota__c {{
  font:400 13.5px/1.65 'Source Sans 3',sans-serif; color:{TINTA};
  margin:0; max-width:72ch;
}}

/* Ancho de línea. Un párrafo de 110 caracteres no se lee dos veces. */
[data-testid="stMain"] [data-testid="stMarkdownContainer"] > p,
[data-testid="stMain"] [data-testid="stCaptionContainer"] p {{ max-width:72ch; }}
</style>"""


# ── Componentes ──────────────────────────────────────────────────────────────
def _ayuda(texto: str) -> str:
    """El icono de ayuda. La explicación va aquí, no dentro de la tarjeta."""
    if not texto:
        return ""
    t = texto.replace('"', "&quot;")
    return f'<span class="ky-ayuda" title="{t}">?</span>'


def tarjeta(label: str, valor: str, delta: str = "", bueno: bool = True,
            ayuda: str = "", hero: bool = False) -> str:
    """La anatomía canónica: etiqueta, cifra, delta. Nada más.

    La proporción cifra/etiqueta es 2,5× —30 sobre 12—. Por debajo de 2× la
    tarjeta no tiene jerarquía; por encima de 3× parece un cartel.

    `ayuda` NO se dibuja en la tarjeta: va al tooltip del icono. Los párrafos
    explicativos dentro de una tarjeta de indicador son el defecto que más
    abarata un panel, y el que tenía éste.
    """
    col = ("#7FD1A8" if bueno else "#F3A6A7") if hero else (GOOD if bueno else BAD)
    d = f'<p class="ky-dlt" style="color:{col}">{delta}</p>' if delta else ""
    cls_t = "ky-t ky-t--hero" if hero else "ky-t"
    cls_v = "ky-val ky-val--hero" if hero else "ky-val"
    cls_l = 'class="ky-lbl"' + (' style="color:rgba(229,225,230,.6)"' if hero else "")
    return (f'<div class="{cls_t}"><p {cls_l}>{label}{_ayuda(ayuda)}</p>'
            f'<p class="{cls_v}">{valor}</p>{d}</div>')


def fila(tarjetas: list, gap: int = GAP_TARJETAS, pesos=None) -> None:
    """Una fila de tarjetas con el hueco correcto entre ellas."""
    cols = st.columns(pesos or len(tarjetas), gap=gap)
    for c, html in zip(cols, tarjetas):
        c.markdown(html, unsafe_allow_html=True)


def fila_hero(hero_html: str, apoyos: list) -> None:
    """Un titular ancho y sus apoyos. Proporción 1,15 : 2,1.

    Cuatro columnas iguales se leen como una lista; así se leen como una
    respuesta y su contexto.
    """
    izq, der = st.columns([1.15, 2.1], gap=GAP_TARJETAS)
    izq.markdown(hero_html, unsafe_allow_html=True)
    with der:
        cols = st.columns(len(apoyos), gap=GAP_TARJETAS)
        for c, html in zip(cols, apoyos):
            c.markdown(html, unsafe_allow_html=True)


def seccion(titulo: str, nota: str = "") -> None:
    """Encabezado de sección. Trae los 48px de aire por arriba."""
    n = f'<span class="ky-sec__n">{nota}</span>' if nota else ""
    st.markdown(f'<div class="ky-sec"><span class="ky-sec__t">{titulo}</span>{n}</div>',
                unsafe_allow_html=True)


def nota(titulo: str, cuerpo: str, alerta: bool = False) -> None:
    """La conclusión de negocio. Un tratamiento neutro y uno de alerta."""
    cls = "ky-nota ky-nota--alerta" if alerta else "ky-nota"
    st.markdown(f'<div class="{cls}"><p class="ky-nota__t">{titulo}</p>'
                f'<p class="ky-nota__c">{cuerpo}</p></div>', unsafe_allow_html=True)
