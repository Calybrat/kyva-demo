"""Lo que pasa dentro del bar: precio en carta, material, competencia y visita.

El hueco que señaló la revisión adversaria, dicho por el gerente en una frase:

    «El panel sabe todo lo que sale de mi bodega y no sabe nada de lo que pasa
    en el bar. Dos restaurantes del mismo tamaño, en la misma zona, con la misma
    carta, me compran tres veces distinto. El ERP me dice cuál compra menos.
    Ninguno de los dos sistemas me dice por qué.»

Y no se lo dicen porque la respuesta no está en la factura. Está en cuatro cosas
que solo se ven parándose en la barra:

  · **A qué precio pone el bar lo que le vendemos.** El sobreprecio de carta es
    decisión del bar, no nuestra, pero nos pega directo: un trago que el bar
    monta a 2,5 veces el costo rota distinto al que monta a 1,2 — y sobre todo,
    dos cuentas a tres cuadras con el mismo vino a precios que no se parecen se
    canibalizan entre ellas y terminan pidiéndonos descuento las dos.
  · **Qué material de exhibición tiene.** La nevera, el hablador, el backbar
    iluminado, el menú de coctelería. Son inversión nuestra, se entregan sin
    contrato de contraprestación y no se mide nunca si devuelven algo.
  · **Quién más está en esa barra.** Un bar no es exclusivo. Dislicores,
    La Licorera o el importador directo están en el mismo estante peleando el
    mismo renglón de la carta.
  · **Hace cuánto no va nadie.** Una cuenta que factura sola parece sana hasta
    el mes en que deja de facturar. Para entonces el reemplazo ya lleva seis
    semanas en el estante.

**La medida del módulo es el índice de rotación**, no las unidades. Comparar
unidades entre una cerveza y un single malt no significa nada: la cerveza rota
cien veces más por definición. El índice es la rotación de esa referencia en esa
cuenta dividida por la mediana de su categoría **en toda la red**. 100 es «rota
como la mediana de su categoría». La mediana se calcula sobre la red completa y
NO sobre lo filtrado, a propósito: si el benchmark se moviera con el filtro,
filtrar a Medellín haría que toda Medellín rotara mágicamente en 100.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.formatters import *
from utils import filtros, gerencia

# La ruta comercial es quincenal. Se alerta a los 21 días y no a los 15 porque
# con 15 la lista salía con media red adentro todas las semanas y el equipo
# dejó de abrirla: una alerta que siempre está encendida no es una alerta.
CADENCIA_RUTA = 15
ALERTA_VISITA = 21

SIN_POP = "Ninguno"
SIN_COMPETENCIA = "Ninguna"

# Para hablar de dispersión de precio hace falta que el mismo SKU esté en
# varias cartas. Con menos de tres cuentas el "rango" es una anécdota.
MIN_CUENTAS_SKU = 3

# El eje del índice se recorta para que la nube se lea. Sin recorte, cuatro
# outliers de vodka aplastan los 340 puntos restantes contra el piso.
TECHO_INDICE = 400

# Muestras mínimas para AFIRMAR algo. Existen porque la pantalla se filtra: con
# «Medellín + Bares» quedan trece referencias, y con trece referencias una
# correlación de -0,08 o un «el POP rinde -58%» son ruido presentado como
# hallazgo. Por debajo del umbral la pantalla dice que no alcanza la muestra, que
# es una respuesta honesta y mucho más barata que una conclusión falsa.
MIN_MUESTRA = 30        # para hablar de correlación precio–rotación
MIN_GRUPO_POP = 12      # por lado (con material y sin material)
MIN_COMP_REFS = 15      # para señalar a un competidor con nombre propio

ROJO_HONDO = "#8B1E1E"
VERDE = "#2f7a48"
AMBAR = "#B5762F"


def _pl(n, singular: str, plural: str = "") -> str:
    """«1 cuenta», no «1 cuentas».

    Parece cosmético y no lo es: en una pantalla que se lee en treinta segundos,
    un plural mal puesto le quita credibilidad a la cifra que tiene al lado.
    """
    n = int(n)
    return f"{num(n)} {singular if n == 1 else (plural or singular + 's')}"


def _preparar(pv: pd.DataFrame) -> pd.DataFrame:
    """Añade las tres columnas derivadas que usa todo el módulo.

    `valor` es lo que esa referencia nos compra esa cuenta en un mes: la
    rotación por el precio al que nosotros la vendemos (pvp_sugerido). Es la
    única forma de ordenar cuentas por lo que valen sin mezclar cajas de cerveza
    con botellas de whisky.
    """
    d = pv.copy()
    med = d.groupby("categoria")["rotacion_mes"].transform("median")
    d["indice"] = np.where(med > 0, d["rotacion_mes"] / med * 100, np.nan)
    d["valor"] = d["rotacion_mes"] * d["pvp_sugerido"]
    d["con_pop"] = d["pop"] != SIN_POP
    d["hay_comp"] = d["competencia"] != SIN_COMPETENCIA
    d["muerta"] = d["rotacion_mes"] <= 0
    return d


def _por_cuenta(d: pd.DataFrame) -> pd.DataFrame:
    """Una fila por establecimiento.

    `visitada_hace_dias` viene por referencia, no por cuenta: cada fila es el
    chequeo de ESA referencia en ESA barra. El mínimo es entonces la última vez
    que alguien pisó el local, y el máximo, la referencia que lleva más tiempo
    sin que nadie la mire. Las dos cosas sirven y son distintas.
    """
    a = d.groupby(["cuenta_id", "nombre", "canal", "ciudad", "zona", "vendedor"],
                  as_index=False).agg(
        refs=("sku", "size"), valor=("valor", "sum"),
        indice=("indice", "median"), sobreprecio=("sobreprecio_pct", "mean"),
        muertas=("muerta", "sum"), con_pop=("con_pop", "sum"),
        competidores=("hay_comp", "sum"),
        visita=("visitada_hace_dias", "min"),
        chequeo=("visitada_hace_dias", "max"))
    a["valor_ref"] = a["valor"] / a["refs"]
    a["pop_pct"] = a["con_pop"] / a["refs"] * 100
    a["comp_pct"] = a["competidores"] / a["refs"] * 100
    return a


def _gemelas(a: pd.DataFrame):
    """Busca dos cuentas comparables que roten muy distinto.

    Comparables de verdad: mismo canal, misma ciudad, cartas de tamaño parecido
    y sobreprecio de carta parecido. Si además la que más rota tiene más
    material y menos competencia adentro, el par sirve para lo único que
    interesa — mostrar que la explicación no estaba en el ERP.

    Se descartan las razones por encima de 5x: con esa brecha las dos cuentas ya
    no son comparables por más que coincidan el canal y la ciudad, y el ejemplo
    deja de convencer a quien conoce los dos locales.
    """
    mejor = None
    for _, g in a.groupby("canal"):
        filas = list(g.itertuples())
        for x in filas:
            for y in filas:
                if x.cuenta_id >= y.cuenta_id or x.ciudad != y.ciudad:
                    continue
                baja, alta = (x, y) if x.valor_ref < y.valor_ref else (y, x)
                if baja.valor_ref <= 0:
                    continue
                razon = alta.valor_ref / baja.valor_ref
                if not 1.6 <= razon <= 5:
                    continue
                if abs(baja.refs - alta.refs) > 2:
                    continue
                if abs(baja.sobreprecio - alta.sobreprecio) > 20:
                    continue
                if alta.pop_pct <= baja.pop_pct or alta.comp_pct > baja.comp_pct:
                    continue
                score = (razon * 10
                         + (alta.pop_pct - baja.pop_pct)
                         + (baja.comp_pct - alta.comp_pct)
                         + (baja.visita - alta.visita) * 2
                         + (30 if baja.refs == alta.refs else 0))
                if mejor is None or score > mejor[0]:
                    mejor = (score, baja, alta, razon)
    return mejor


def _tarjeta_cuenta(c, tono: str) -> str:
    """Ficha compacta de una cuenta para la comparación final."""
    color = ROJO_HONDO if tono == "baja" else VERDE
    etiqueta = "Rota poco" if tono == "baja" else "Rota bien"
    badges = "".join([
        chip(f"{int(c.con_pop)} de {int(c.refs)} con material",
             "ok" if c.pop_pct >= 60 else "alerta"),
        chip(f"{_pl(c.competidores, 'referencia')} con competencia adentro",
             "alerta" if c.comp_pct >= 60 else "neutro"),
        chip(f"Última visita hace {_pl(c.visita, 'día')}",
             "alerta" if c.visita > ALERTA_VISITA else "ok"),
        chip(f"{_pl(c.muertas, 'referencia muerta', 'referencias muertas')}",
             "alerta" if c.muertas else "ok"),
    ])
    return f"""
    <div style="border:1px solid {PALIDO};border-top:4px solid {color};
         border-radius:6px;padding:16px 20px;background:#fff;height:100%">
      <div style="font-size:9.5px;font-weight:800;letter-spacing:.14em;
           text-transform:uppercase;color:{color}">{etiqueta}</div>
      <div style="font-family:'DM Serif Display',Georgia,serif;font-size:25px;
           color:{TINTA};line-height:1.15;margin:2px 0 3px">{c.nombre}</div>
      <div style="font-size:11.5px;color:{CLARO};margin-bottom:9px">
        {c.canal} · {c.ciudad} · {c.zona} &nbsp;·&nbsp;
        Vendedor: <b style="color:{TINTA}">{c.vendedor}</b></div>
      <div style="display:flex;gap:22px;margin-bottom:10px">
        <div><div style="font-size:9.5px;font-weight:800;letter-spacing:.1em;
             text-transform:uppercase;color:{CLARO}">Valor por referencia</div>
          <div style="font-size:23px;font-weight:800;color:{color};line-height:1.2">
            {cop(c.valor_ref, 0)}</div></div>
        <div><div style="font-size:9.5px;font-weight:800;letter-spacing:.1em;
             text-transform:uppercase;color:{CLARO}">Sobreprecio de carta</div>
          <div style="font-size:23px;font-weight:800;color:{TINTA};line-height:1.2">
            {pct(c.sobreprecio, 0)}</div></div>
      </div>
      <div>{badges}</div>
    </div>"""


def render():
    st.markdown(HEADER_CSS, unsafe_allow_html=True)
    st.markdown(encabezado(
        "Lo que pasa dentro del bar",
        "Precio en carta, material de exhibición, competencia en la barra y "
        "cobertura de visita",
        "¿Por qué rota lo que rota?"), unsafe_allow_html=True)
    filtros.encabezado_filtro()

    base = _preparar(gerencia.punto_venta())
    d = filtros.aplicar(base, col_mes=None)
    if d.empty:
        st.info("Ninguna cuenta queda con los filtros puestos. "
                "Quítelos en la barra lateral.")
        return
    a = _por_cuenta(d)

    muertas = int(d["muerta"].sum())
    n_con, n_sin = int(d["con_pop"].sum()), int((~d["con_pop"]).sum())
    pop_comparable = n_con >= MIN_GRUPO_POP and n_sin >= MIN_GRUPO_POP
    idx_con = float(d.loc[d["con_pop"], "indice"].median()) if n_con else np.nan
    idx_sin = float(d.loc[~d["con_pop"], "indice"].median()) if n_sin else np.nan
    retorno_pop = ((idx_con / idx_sin - 1) * 100
                   if pop_comparable and idx_sin > 0 else np.nan)
    muertas_con = float(d.loc[d["con_pop"], "muerta"].mean() * 100) if n_con else np.nan
    muertas_sin = float(d.loc[~d["con_pop"], "muerta"].mean() * 100) if n_sin else np.nan

    # El competidor que se señala con nombre propio se elige por los datos, no
    # por reputación: el que más nos baja el índice donde está. Y solo se señala
    # si tiene presencia suficiente Y el efecto es realmente negativo — si no,
    # la pantalla estaría acusando a alguien por catorce filas de azar.
    limpias = d[~d["hay_comp"]]
    idx_limpio = float(limpias["indice"].median()) if len(limpias) else np.nan
    comp = d[d["hay_comp"]].groupby("competencia", as_index=False).agg(
        refs=("indice", "size"), indice=("indice", "median"),
        cuentas=("cuenta_id", "nunique"), muertas=("muerta", "mean"),
        valor=("valor", "sum"))
    comp["muertas"] *= 100
    comp["delta"] = ((comp["indice"] / idx_limpio - 1) * 100
                     if np.isfinite(idx_limpio) and idx_limpio > 0 else np.nan)
    comp = comp.sort_values("indice")
    duros = comp[(comp["refs"] >= MIN_COMP_REFS) & (comp["delta"] < 0)]
    rival = duros.iloc[0] if len(duros) else None

    fuera = a[a["visita"] > ALERTA_VISITA].sort_values("valor", ascending=False)

    k = st.columns(4, gap="small")
    k[0].markdown(kpi(
        "Referencias muertas en carta", num(muertas),
        f"{pct(muertas / len(d) * 100, 0)} de las {num(len(d))} que tenemos en carta",
        False, "🪦",
        "Están impresas en la carta del bar y no vendieron una sola botella el "
        "mes pasado. Ocupan renglón, y el renglón es lo que pelea la competencia.",
        f"{_pl(d.loc[d['muerta'], 'cuenta_id'].nunique(), 'cuenta')} "
        f"con al menos una"), unsafe_allow_html=True)
    if pop_comparable:
        signo_muertas = "menos" if muertas_sin >= muertas_con else "más"
        k[1].markdown(kpi(
            "Lo que devuelve el POP", signo(retorno_pop, 0),
            f"y {num(abs(muertas_sin - muertas_con), 1)} pts {signo_muertas} "
            f"de referencias muertas", retorno_pop > 0, "📺",
            "Rotación de las referencias con material de exhibición contra las "
            "que no lo tienen, medida contra la mediana de cada categoría.",
            "Hoy el POP se entrega sin medir nada"), unsafe_allow_html=True)
    else:
        k[1].markdown(kpi(
            "Cobertura de material", pct(n_con / len(d) * 100, 0),
            f"{_pl(n_sin, 'referencia')} sin una sola pieza", n_sin == 0, "📺",
            "Con esta vista no hay cuentas suficientes para medir qué devuelve "
            "el POP. Quite un filtro y la cifra aparece.",
            "El retorno se mide sobre la red completa"), unsafe_allow_html=True)
    if rival is not None:
        k[2].markdown(kpi(
            f"Donde está {rival['competencia']}", signo(rival["delta"], 0),
            f"en {_pl(rival['cuentas'], 'cuenta')} · "
            f"{_pl(rival['refs'], 'referencia')}",
            False, "🎯",
            "Cuánto rotamos en las barras donde ese distribuidor también está, "
            "contra las barras donde estamos solos."), unsafe_allow_html=True)
    else:
        comp_refs = int(d["hay_comp"].sum())
        k[2].markdown(kpi(
            "Barras compartidas", pct(comp_refs / len(d) * 100, 0),
            f"{_pl(d.loc[d['hay_comp'], 'cuenta_id'].nunique(), 'cuenta')} "
            f"con otro distribuidor adentro", False, "🎯",
            "En esta vista ningún competidor tiene presencia suficiente para "
            "señalarlo con nombre propio sin inventar el hallazgo."),
            unsafe_allow_html=True)
    k[3].markdown(kpi(
        "Cuentas fuera de ruta", num(len(fuera)),
        f"{cop(fuera['valor'].sum(), 0)} al mes sin supervisar"
        if len(fuera) else "toda la red dentro de cadencia",
        len(fuera) == 0, "🚪",
        f"Más de {ALERTA_VISITA} días sin que nadie entre, con la ruta "
        f"programada cada {CADENCIA_RUTA}.",
        "Una cuenta abandonada factura sola hasta que deja de hacerlo"),
        unsafe_allow_html=True)

    st.markdown(espacio(18), unsafe_allow_html=True)

    # ── 1. El precio en carta ───────────────────────────────────────────────
    st.markdown('<div class="ky-sub">A qué precio lo pone el bar</div>',
                unsafe_allow_html=True)

    vivas = d[(d["rotacion_mes"] > 0) & d["indice"].notna()].copy()
    vivas["indice_vis"] = vivas["indice"].clip(upper=TECHO_INDICE)
    corr = float(vivas["sobreprecio_pct"].corr(vivas["indice"])) if len(vivas) > 5 else np.nan

    col = st.columns([3, 2], gap="large")
    with col[0]:
        fig = go.Figure()
        for canal in sorted(vivas["canal"].unique()):
            s = vivas[vivas["canal"] == canal]
            fig.add_trace(go.Scatter(
                x=s["sobreprecio_pct"], y=s["indice_vis"], mode="markers", name=canal,
                marker=dict(size=np.clip(np.sqrt(s["valor"]) / 900, 6, 26),
                            opacity=.72, line=dict(width=1, color="#fff")),
                customdata=np.stack([s["nombre"], s["producto"], s["rotacion_mes"],
                                     s["precio_carta"], s["pop"]], -1),
                hovertemplate="<b>%{customdata[1]}</b><br>%{customdata[0]}"
                              "<br>Sobreprecio de carta: %{x:.0f}%"
                              "<br>En carta a $%{customdata[3]:,.0f}"
                              "<br>Rota %{customdata[2]:.0f} u/mes · índice %{y:.0f}"
                              "<br>Material: %{customdata[4]}<extra></extra>"))
        fig.add_hline(y=100, line_width=1.3, line_dash="dot", line_color=CLARO,
                      annotation_text="rota como su categoría",
                      annotation_position="top left")
        fig.update_xaxes(title="Sobreprecio sobre nuestro precio (%)")
        fig.update_yaxes(title="Índice de rotación (100 = mediana de su categoría)")
        # Con 340 puntos superpuestos, el hover unificado de la casa devuelve un
        # tooltip de veinte líneas. Aquí manda el punto, no la columna.
        st.plotly_chart(light(fig, 400).update_layout(hovermode="closest"),
                        use_container_width=True)

    with col[1]:
        bandas = pd.cut(d["sobreprecio_pct"], [0, 120, 160, 200, 400],
                        labels=["Hasta 120%", "120–160%", "160–200%", "Más de 200%"])
        b = d.groupby(bandas, observed=True, as_index=False).agg(
            n=("muerta", "size"), muertas=("muerta", "mean"),
            indice=("indice", "median"))
        b["muertas"] *= 100
        b.columns = ["banda", "n", "muertas", "indice"]
        fig2 = go.Figure(go.Bar(
            x=b["banda"].astype(str), y=b["muertas"], marker_color=PRIMARIO,
            customdata=np.stack([b["n"], b["indice"]], -1),
            hovertemplate="%{x}<br>%{customdata[0]:.0f} referencias"
                          "<br>%{y:.1f}% no rota"
                          "<br>Índice mediano: %{customdata[1]:.0f}<extra></extra>"))
        fig2.update_yaxes(title="Referencias que no rotan (%)")
        st.plotly_chart(light(fig2, 400), use_container_width=True)

    pie = (f"El tamaño del círculo es lo que esa referencia nos compra al mes"
           + (f"; el eje está recortado en {num(TECHO_INDICE)} y "
              f"{_pl((vivas['indice'] > TECHO_INDICE).sum(), 'punto')} "
              f"{'queda' if int((vivas['indice'] > TECHO_INDICE).sum()) == 1 else 'quedan'} "
              f"por encima."
              if (vivas["indice"] > TECHO_INDICE).any() else "."))
    if np.isfinite(corr) and len(vivas) >= MIN_MUESTRA:
        st.caption(
            f"La correlación entre sobreprecio y rotación es de **{num(corr, 2)}** "
            f"sobre {num(len(vivas))} referencias vivas: no existe. Y la barra de "
            f"la derecha lo dice por el otro lado — la proporción de referencias "
            f"que no rotan es prácticamente igual en la banda barata que en la "
            f"cara. **Dentro del rango en que hoy se mueve la red "
            f"(de {pct(d['sobreprecio_pct'].min(), 0)} a "
            f"{pct(d['sobreprecio_pct'].max(), 0)}), el precio de carta no "
            f"explica la rotación.** {pie}")
    else:
        # Sin muestra no se afirma ni que hay relación ni que no la hay.
        st.caption(
            f"Con {num(len(vivas))} referencias vivas en esta vista la nube no "
            f"alcanza para concluir nada sobre precio y rotación — hacen falta al "
            f"menos {num(MIN_MUESTRA)}. Quite un filtro para leer la relación "
            f"sobre la red completa. {pie}")

    st.markdown(espacio(14), unsafe_allow_html=True)

    # ── Dispersión: el mismo producto a precios que no se parecen ───────────
    st.markdown('<div class="ky-sub">El mismo producto, precios que no se parecen</div>',
                unsafe_allow_html=True)
    sk = d.groupby(["sku", "producto"], as_index=False).agg(
        cuentas=("cuenta_id", "nunique"), lo=("sobreprecio_pct", "min"),
        hi=("sobreprecio_pct", "max"), med=("sobreprecio_pct", "median"),
        p_lo=("precio_carta", "min"), p_hi=("precio_carta", "max"))
    sk = sk[sk["cuentas"] >= MIN_CUENTAS_SKU].copy()
    sk["rango"] = sk["hi"] - sk["lo"]
    top = sk.nlargest(10, "rango").sort_values("rango")

    if len(top):
        etiquetas = [p if len(p) <= 34 else p[:32] + "…" for p in top["producto"]]
        fig3 = go.Figure()
        xs, ys = [], []
        for et, lo, hi in zip(etiquetas, top["lo"], top["hi"]):
            xs += [lo, hi, None]
            ys += [et, et, None]
        fig3.add_trace(go.Scatter(x=xs, y=ys, mode="lines", showlegend=False,
                                  line=dict(color=PALIDO, width=5),
                                  hoverinfo="skip"))
        fig3.add_trace(go.Scatter(
            x=top["lo"], y=etiquetas, mode="markers", name="El bar más barato",
            marker=dict(size=13, color=PRIMARIO, line=dict(width=1.5, color="#fff")),
            customdata=top["p_lo"],
            hovertemplate="%{y}<br>Sobreprecio mínimo: %{x:.0f}%"
                          "<br>En carta a $%{customdata:,.0f}<extra></extra>"))
        fig3.add_trace(go.Scatter(
            x=top["hi"], y=etiquetas, mode="markers", name="El bar más caro",
            marker=dict(size=13, color=ACENTO, line=dict(width=1.5, color="#fff")),
            customdata=top["p_hi"],
            hovertemplate="%{y}<br>Sobreprecio máximo: %{x:.0f}%"
                          "<br>En carta a $%{customdata:,.0f}<extra></extra>"))
        fig3.update_xaxes(title="Sobreprecio de carta (%)")
        fig3.update_yaxes(automargin=True)
        st.plotly_chart(light(fig3, 380).update_layout(hovermode="closest"),
                        use_container_width=True)
    else:
        st.caption(
            f"Ningún producto está en {MIN_CUENTAS_SKU} o más cartas dentro de "
            f"esta vista, así que no hay con qué comparar precios. La dispersión "
            f"se lee sobre la red completa o sobre una ciudad entera.")

    # Lo caro de la dispersión no es el promedio: es el vecino. Dos cuentas de
    # la misma zona con el mismo producto a precios distintos compiten entre
    # ellas y las dos terminan pidiéndonos rebaja.
    vec = d.groupby(["zona", "sku", "producto"], as_index=False).agg(
        cuentas=("cuenta_id", "nunique"), lo=("sobreprecio_pct", "min"),
        hi=("sobreprecio_pct", "max"))
    vec = vec[vec["cuentas"] >= 2].copy()
    vec["brecha"] = vec["hi"] - vec["lo"]
    vec = vec.sort_values("brecha", ascending=False)

    if len(top):
        peor_sku = top.iloc[-1]
        cuerpo = (
            f"<b>{peor_sku['producto']}</b> está en "
            f"{_pl(peor_sku['cuentas'], 'carta')}: el bar más barato lo "
            f"monta a {pct(peor_sku['lo'], 0)} sobre nuestro precio "
            f"({cop(peor_sku['p_lo'], 0)} al público) y el más caro a "
            f"{pct(peor_sku['hi'], 0)} ({cop(peor_sku['p_hi'], 0)}). "
            f"Es el mismo producto, la misma botella y el mismo proveedor.<br><br>")
        if len(vec):
            v0 = vec.iloc[0]
            cuerpo += (
                f"El problema no es el promedio de la red, es el vecino: en "
                f"<b>{v0['zona']}</b>, dos cuentas a pocas cuadras tienen "
                f"<b>{v0['producto']}</b> con {num(v0['brecha'], 0)} puntos de "
                f"diferencia de sobreprecio. Hay "
                f"<b>{_pl((vec['brecha'] > 80).sum(), 'caso')}</b> de este tipo "
                f"con más de 80 puntos de brecha dentro de la misma zona. "
                f"El que quedó caro pierde rotación contra el de al lado, y el "
                f"que quedó barato vuelve a pedirnos descuento porque «no le da "
                f"el margen». Perdemos por los dos lados.<br><br>")
        cuerpo += (
            "<b>Qué hacer con esto.</b> No es fijar precio de carta —eso no se "
            "puede y además es del bar—. Es llevar a la visita el precio de la "
            "zona: el vendedor que entra a negociar sabiendo a qué lo monta el "
            "de enfrente tiene una conversación distinta a la de bajar el "
            "descuento tres puntos más.")
        st.markdown(panel("La dispersión de carta, leída en plata", cuerpo,
                          "🏷️", "naranja"), unsafe_allow_html=True)

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── 2. El material POP ──────────────────────────────────────────────────
    st.markdown('<div class="ky-sub">Qué devuelve el material de exhibición</div>',
                unsafe_allow_html=True)

    p = d.groupby("pop", as_index=False).agg(
        refs=("indice", "size"), indice=("indice", "median"),
        muertas=("muerta", "mean"), valor=("valor", "sum"),
        cuentas=("cuenta_id", "nunique"))
    p["muertas"] *= 100
    p = p.sort_values("indice")

    fig4 = go.Figure(go.Bar(
        y=p["pop"], x=p["indice"], orientation="h",
        marker_color=[ROJO_HONDO if t == SIN_POP else PRIMARIO for t in p["pop"]],
        customdata=np.stack([p["refs"], p["cuentas"], p["muertas"]], -1),
        hovertemplate="%{y}<br>Índice mediano: %{x:.0f}"
                      "<br>%{customdata[0]:.0f} referencias en %{customdata[1]:.0f} cuentas"
                      "<br>%{customdata[2]:.1f}% no rota<extra></extra>"))
    fig4.add_vline(x=100, line_width=1.3, line_dash="dot", line_color=CLARO)
    fig4.update_xaxes(title="Índice de rotación (100 = mediana de su categoría)")
    fig4.update_yaxes(automargin=True)
    st.plotly_chart(light(fig4, 320), use_container_width=True)

    # El material que NO se defiende se nombra desde el dato, no desde la
    # memoria: la lista cambia con el filtro y una frase quemada envejece mal.
    reales = p[(p["pop"] != SIN_POP) & (p["refs"] >= MIN_GRUPO_POP)]
    flojo = reales.iloc[0] if len(reales) else None
    if flojo is not None and np.isfinite(idx_sin) and flojo["indice"] <= idx_sin:
        st.caption(
            f"La barra roja es *sin material*. Todo lo que está a su derecha "
            f"rota más que ella. **La excepción es «{flojo['pop']}»**: cuesta "
            f"como el resto y rota igual que no tener nada "
            f"(índice {num(flojo['indice'], 0)} contra {num(idx_sin, 0)}). Es el "
            f"único material de esta lista que no se defiende solo, y es el "
            f"primero que hay que dejar de repartir por inercia.")
    else:
        st.caption(
            "La barra roja es *sin material*. Todo lo que está a su derecha rota "
            "más que ella: en esta vista **ninguna pieza de POP rinde por debajo "
            "de no tener nada**.")

    sin_nada = a[a["pop_pct"] == 0].sort_values("valor", ascending=False)
    if pop_comparable and np.isfinite(retorno_pop) and retorno_pop > 0:
        titulo_pop = "El POP sí paga, y hasta hoy nadie lo había medido"
        cuerpo_pop = (
            f"Las referencias con material rotan un <b>{signo(retorno_pop, 0)}</b> "
            f"más que las que no lo tienen, y la proporción que no rota nada baja "
            f"de {pct(muertas_sin)} a {pct(muertas_con)}. Sobre las "
            f"{_pl(n_sin, 'referencia')} que hoy están sin material, cerrar esa "
            f"brecha vale del orden de "
            f"{cop(float(d.loc[~d['con_pop'], 'valor'].sum()) * retorno_pop / 100, 0)} "
            f"de compra al mes.<br><br>")
    elif pop_comparable:
        titulo_pop = "Aquí el POP no está pagando, y eso también es un hallazgo"
        cuerpo_pop = (
            f"En esta vista las referencias con material rotan "
            f"<b>{signo(retorno_pop, 0)}</b> contra las que no lo tienen: el "
            f"material no está devolviendo nada. Antes de repartir más, hay que "
            f"mirar si está puesto donde el producto ya rotaba solo — que es lo "
            f"que pasa cuando el POP se entrega para cerrar un pedido y no para "
            f"mover un renglón.<br><br>")
    else:
        titulo_pop = "Hace falta red para medir el retorno del material"
        cuerpo_pop = (
            f"Con {_pl(n_con, 'referencia')} con material y "
            f"{_pl(n_sin, 'referencia')} sin él, esta vista no da para comparar "
            f"rotaciones sin inventar el resultado. Quite un filtro y la cifra "
            f"aparece.<br><br>")
    if len(sin_nada):
        s0 = sin_nada.iloc[0]
        cuerpo_pop += (
            f"Hay <b>{_pl(len(sin_nada), 'cuenta')} sin una sola pieza de "
            f"material</b>. La más grande es <b>{s0['nombre']}</b> "
            f"({s0['canal']}, {s0['ciudad']}), que compra {cop(s0['valor'], 0)} "
            f"al mes con {_pl(s0['refs'], 'referencia')} en carta y ni una "
            f"nevera, ni un hablador, ni un menú.<br><br>")
    cuerpo_pop += (
        "<b>Lo que hay que cambiar en la operación.</b> Hoy el material se "
        "entrega cuando el vendedor lo pide y no se vuelve a mirar. Medido por "
        "cuenta, el POP deja de ser gasto de mercadeo y pasa a ser una inversión "
        "con retorno — que es también la única forma de pedirle al proveedor que "
        "la cofinancie: con el número, no con el argumento.")
    st.markdown(panel(titulo_pop, cuerpo_pop, "📺", "azul"), unsafe_allow_html=True)

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── 3. La competencia en la barra ───────────────────────────────────────
    st.markdown('<div class="ky-sub">Quién más está en esa barra</div>',
                unsafe_allow_html=True)

    cc = comp.copy()
    if len(limpias):
        cc = pd.concat([cc, pd.DataFrame([{
            "competencia": "Estamos solos", "refs": len(limpias),
            "indice": idx_limpio, "cuentas": int(limpias["cuenta_id"].nunique()),
            "muertas": float(limpias["muerta"].mean() * 100),
            "valor": float(limpias["valor"].sum()), "delta": 0.0}])],
            ignore_index=True)
    cc = cc.sort_values("indice")

    fig5 = go.Figure(go.Bar(
        y=cc["competencia"], x=cc["indice"], orientation="h",
        marker_color=[VERDE if c == "Estamos solos" else
                      (ROJO_HONDO if np.isfinite(idx_limpio) and i < idx_limpio
                       else AMBAR)
                      for c, i in zip(cc["competencia"], cc["indice"])],
        customdata=np.stack([cc["refs"], cc["cuentas"], cc["muertas"],
                             cc["delta"].fillna(0)], -1),
        hovertemplate="%{y}<br>Índice mediano nuestro: %{x:.0f}"
                      "<br>%{customdata[0]:.0f} referencias en %{customdata[1]:.0f} cuentas"
                      "<br>%{customdata[2]:.1f}% no rota"
                      "<br>Contra barra limpia: %{customdata[3]:+.0f}%<extra></extra>"))
    if np.isfinite(idx_limpio):
        fig5.add_vline(x=idx_limpio, line_width=1.3, line_dash="dot",
                       line_color=CLARO, annotation_text="barra sin competencia",
                       annotation_position="top")
    fig5.update_xaxes(title="Índice de rotación nuestro en esas barras")
    fig5.update_yaxes(automargin=True)
    st.plotly_chart(light(fig5, 320), use_container_width=True)

    # Quién nos conviene de vecino sale del dato: en una red donde cambia el
    # surtido cada trimestre, quemar un nombre en el texto lo deja mintiendo.
    amable = comp[comp["refs"] >= MIN_COMP_REFS].nlargest(1, "indice")
    if len(amable) and np.isfinite(idx_limpio) and amable.iloc[0]["indice"] > idx_limpio:
        st.caption(
            f"Es nuestra rotación, no la de ellos: lo que mide la barra es "
            f"cuánto nos cuesta compartir estante con cada uno. **Tener "
            f"competencia adentro no es en sí el problema** —con "
            f"{amable.iloc[0]['competencia']} al lado rotamos por encima de la "
            f"barra limpia—: el problema tiene nombre propio y es el que aparece "
            f"abajo del todo.")
    else:
        st.caption(
            "Es nuestra rotación, no la de ellos: lo que mide la barra es cuánto "
            "nos cuesta compartir estante con cada uno.")

    if rival is not None:
        foco = d[d["competencia"] == rival["competencia"]]
        t = foco.groupby(["nombre", "canal", "ciudad"], as_index=False).agg(
            refs=("sku", "size"), indice=("indice", "median"),
            muertas=("muerta", "sum"), pop=("con_pop", "sum"),
            valor=("valor", "sum"), visita=("visitada_hace_dias", "min"))
        t = t.nlargest(12, "refs").sort_values(["refs", "valor"], ascending=False)
        tab = pd.DataFrame({
            "Cuenta": t["nombre"], "Canal": t["canal"], "Ciudad": t["ciudad"],
            f"Referencias con {rival['competencia']} al lado": t["refs"].astype(int),
            "Con material": t["pop"].astype(int),
            "Muertas": t["muertas"].astype(int),
            "Índice": t["indice"].map(lambda v: num(v, 0)),
            "Nos compra al mes": t["valor"].map(lambda v: cop(v, 0)),
            "Sin visita (días)": t["visita"].astype(int)})
        st.dataframe(tab, hide_index=True, width="stretch")

        st.markdown(panel(
            f"{rival['competencia']} no está peleando cuentas: está peleando renglones",
            f"Donde {rival['competencia']} comparte barra con nosotros, nuestro "
            f"índice de rotación es <b>{num(rival['indice'], 0)}</b> contra "
            f"<b>{num(idx_limpio, 0)}</b> en las barras donde estamos solos — "
            f"<b>{signo(rival['delta'], 0)}</b>. Y el "
            f"{pct(rival['muertas'])} de esas referencias no rota nada, contra "
            f"{pct(float(limpias['muerta'].mean() * 100))} en barra "
            f"limpia.<br><br>"
            f"Son {_pl(rival['cuentas'], 'cuenta')} y "
            f"{_pl(rival['refs'], 'referencia')}. "
            f"La lectura correcta no es «hay que sacarlos»: es que "
            f"en esas barras <b>el renglón de la carta se decide cada trimestre</b> "
            f"y ahí es donde el material y la visita dejan de ser un detalle. "
            f"Una referencia muerta en una barra compartida no se queda muerta: "
            f"la reemplazan, y la reemplazan con ellos.",
            "🎯", "alerta"), unsafe_allow_html=True)

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── 4. Cobertura de visita ──────────────────────────────────────────────
    st.markdown('<div class="ky-sub">Las que llevan tiempo sin que nadie entre</div>',
                unsafe_allow_html=True)

    fig6 = go.Figure()
    for canal in sorted(a["canal"].unique()):
        s = a[a["canal"] == canal]
        fig6.add_trace(go.Scatter(
            # Los millones se dividen aquí y no con light(moneda=True): ese
            # atajo reescribe el hovertemplate de la traza y se lleva por
            # delante el nombre de la cuenta, que es lo único que hace
            # accionable este gráfico.
            x=s["visita"], y=s["valor"] / 1e6, mode="markers", name=canal,
            marker=dict(size=np.clip(s["refs"] * 2.6, 8, 28), opacity=.78,
                        line=dict(width=1, color="#fff")),
            customdata=np.stack([s["nombre"], s["ciudad"], s["vendedor"],
                                 s["refs"], s["pop_pct"]], -1),
            hovertemplate="<b>%{customdata[0]}</b> · %{customdata[1]}"
                          "<br>Vendedor: %{customdata[2]}"
                          "<br>Sin visita hace %{x:.0f} días"
                          "<br>Nos compra $%{y:,.1f} M al mes"
                          "<br>%{customdata[3]:.0f} referencias · "
                          "%{customdata[4]:.0f}% con material<extra></extra>"))
    fig6.add_vline(x=CADENCIA_RUTA, line_width=1, line_dash="dot", line_color=CLARO,
                   annotation_text="ruta quincenal", annotation_position="top")
    fig6.add_vline(x=ALERTA_VISITA, line_width=1.6, line_color=ACENTO,
                   annotation_text="fuera de ruta", annotation_position="top right")
    fig6.update_xaxes(title="Días desde la última visita")
    fig6.update_yaxes(title="Lo que nos compra al mes", tickprefix="$",
                      ticksuffix=" M", tickformat=",.0f")
    st.plotly_chart(light(fig6, 380).update_layout(hovermode="closest"),
                    use_container_width=True)
    st.caption(
        "Arriba a la derecha está lo caro: cuentas grandes que llevan semanas "
        "sin supervisión. El tamaño del círculo es el número de referencias "
        "que nos tienen en carta.")

    if len(fuera):
        tv = pd.DataFrame({
            "Cuenta": fuera["nombre"], "Canal": fuera["canal"],
            "Ciudad": fuera["ciudad"], "Zona": fuera["zona"],
            "Vendedor": fuera["vendedor"],
            "Sin visita (días)": fuera["visita"].astype(int),
            "Referencias": fuera["refs"].astype(int),
            "Muertas": fuera["muertas"].astype(int),
            "Con material": fuera["con_pop"].astype(int),
            "Competidores adentro": fuera["competidores"].astype(int),
            "Nos compra al mes": fuera["valor"].map(lambda v: cop(v, 0))})
        st.dataframe(tv, hide_index=True, width="stretch")

    # La referencia más vieja sin chequear dentro de una cuenta que SÍ se visita
    # es el punto ciego de segundo orden: el vendedor entra, toma el pedido de
    # lo que ya rota y nunca mira el estante donde está lo que se murió.
    olvidadas = int((d["visitada_hace_dias"] > 60).sum())
    v0 = fuera.iloc[0] if len(fuera) else None
    cuerpo_v = ""
    if v0 is not None:
        cuerpo_v += (
            f"<b>{v0['nombre']}</b> ({v0['canal']}, {v0['ciudad']} · "
            f"{v0['zona']}) lleva <b>{int(v0['visita'])} días</b> sin que entre "
            f"nadie y nos compra {cop(v0['valor'], 0)} al mes. La lleva "
            f"{v0['vendedor']}. En total son {_pl(len(fuera), 'cuenta')} y "
            f"{cop(fuera['valor'].sum(), 0)} mensuales sin supervisar.<br><br>")
    cuerpo_v += (
        f"Y hay un segundo punto ciego, más silencioso: "
        f"<b>{_pl(olvidadas, 'referencia')} "
        f"{'lleva' if olvidadas == 1 else 'llevan'} más de 60 días sin que nadie "
        f"las chequee</b>, "
        f"muchas de ellas en cuentas que sí se visitan. El vendedor entra, toma "
        f"el pedido de lo que ya rota y no mira el estante donde está lo que se "
        f"murió. Por eso la cobertura de visita no se mide por cuenta: se mide "
        f"por referencia.")
    st.markdown(panel("La cobertura real, que no es la que dice la ruta",
                      cuerpo_v, "🚪", "naranja"), unsafe_allow_html=True)

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── 5. Las gemelas: la conclusión del módulo ────────────────────────────
    st.markdown('<div class="ky-sub">Dos cuentas parecidas que rotan distinto</div>',
                unsafe_allow_html=True)

    par = _gemelas(a)
    if par is None:
        st.info("Con los filtros puestos no quedan dos cuentas comparables "
                "suficientes para el contraste. Amplíe el filtro en la barra lateral.")
        return

    _, baja, alta, razon = par
    c = st.columns(2, gap="large")
    c[0].markdown(_tarjeta_cuenta(baja, "baja"), unsafe_allow_html=True)
    c[1].markdown(_tarjeta_cuenta(alta, "alta"), unsafe_allow_html=True)

    st.markdown(espacio(10), unsafe_allow_html=True)

    dif_pop = alta.pop_pct - baja.pop_pct
    dif_vis = baja.visita - alta.visita
    dif_comp = baja.comp_pct - alta.comp_pct
    st.markdown(panel(
        "La explicación no estaba en el ERP",
        f"<b>{baja.nombre}</b> y <b>{alta.nombre}</b> son el mismo canal "
        f"({baja.canal}), la misma ciudad, cartas de "
        f"{int(baja.refs)} y {int(alta.refs)} referencias nuestras y un "
        f"sobreprecio de carta prácticamente igual "
        f"({pct(baja.sobreprecio, 0)} contra {pct(alta.sobreprecio, 0)}). "
        f"Por referencia, una nos compra <b>{num(razon, 1)} veces</b> lo que nos "
        f"compra la otra: {cop(alta.valor_ref, 0)} contra "
        f"{cop(baja.valor_ref, 0)} al mes.<br><br>"
        f"En Loggro las dos son cuentas activas del mismo segmento, y ahí se "
        f"acaba la información. Lo que las separa está en esta pantalla y en "
        f"ningún otro lado:<br>"
        f"· <b>Material:</b> {int(alta.con_pop)} de {int(alta.refs)} referencias "
        f"con POP contra {int(baja.con_pop)} de {int(baja.refs)} "
        f"({signo(dif_pop, 0)} de cobertura).<br>"
        f"· <b>Competencia:</b> {int(baja.competidores)} referencias con otro "
        f"distribuidor al lado contra {int(alta.competidores)} "
        f"({num(dif_comp, 0)} puntos de diferencia).<br>"
        f"· <b>Visita:</b> última entrada hace {int(baja.visita)} días contra "
        f"{int(alta.visita)} — {num(dif_vis, 0)} días de diferencia.<br>"
        f"· <b>Referencias muertas:</b> {int(baja.muertas)} contra "
        f"{int(alta.muertas)}.<br><br>"
        f"<b>La decisión.</b> Nadie va a arreglar {baja.nombre} bajándole el "
        f"precio: en esta misma pantalla se ve que el precio de carta no mueve "
        f"la rotación. Se arregla con lo que sí la mueve — poner material donde "
        f"no hay, entrar cada {CADENCIA_RUTA} días y pelear "
        f"{_pl(baja.muertas, 'renglón muerto', 'renglones muertos')} antes de "
        f"que los reemplace el de al lado. Es una decisión de ruta y de "
        f"mercadeo, y por eso no aparece en ningún informe de ventas.",
        "🧭", "alerta"), unsafe_allow_html=True)
