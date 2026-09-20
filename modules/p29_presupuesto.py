"""Presupuesto: el año contra el compromiso, y quién debe la diferencia.

Todo lo demás en este panel es descriptivo. Se proyectan cuatro mil doscientos
millones — ¿y eso es bueno o malo? Nadie lo sabe, porque no hay contraparte. La
pregunta de un gerente nunca fue «cuánto vendí»: es **cuánto me falta y quién lo
debe**, con nombre, apellido y fecha.

Tres cosas que esta pantalla hace y que un informe de ventas no puede hacer:

**1. Le pone contraparte a la cifra.** Una venta sin compromiso al lado es una
anécdota. El mismo número contra el presupuesto es una conversación con dueño.

**2. Separa la desviación buena de la desviación ciega.** Una línea que cumple
el 700% no es una línea excelente: es una línea a la que nadie le pidió nada.
Medir el cumplimiento sin mirar el *peso* de cada línea en el compromiso lleva
al error más caro de un comité — discutir dos horas la línea que falló por el
4% y no mencionar la que representa el 20% de la venta y no tiene meta.

**3. Cierra el año, no el mes.** El archivo de presupuesto llega a agosto; el
compromiso es anual. Sin reconstruir septiembre–diciembre no se puede contestar
si el año se cierra, y esa es la única pregunta que importa en septiembre. Las
dos mitades de esa cuenta —lo que se exige y lo que se va a entregar— van con
la MISMA estacionalidad: comparar un compromiso armado sobre temporada alta
contra «agosto cuatro veces» no mide el negocio, mide el método.

Alcance: esta pantalla mide solo el B2B presupuestado, que es lo que hay en
`presupuesto.csv` —canal × ciudad—. El cierre de la compañía entera, con The
Store, The Lounge y distribución, se proyecta en «Proyección de cierre» sobre
otro universo de datos; los dos números no son comparables y no deben sumarse.

El cierre de la pantalla no es un gráfico: es la aritmética de las tres palancas
—más cuentas, más ticket, más frecuencia—, porque las tres cierran brecha y
ninguna cierra en el mismo plazo. Elegir mal la palanca es perder el trimestre
haciendo algo que sí funcionaba, pero para marzo.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.formatters import *
from utils import gerencia, b2b, filtros, estado

CORTE = "2026-08"
INICIO_ANIO = "2026-01"
RESTO = ["2026-09", "2026-10", "2026-11", "2026-12"]

# Factor de ambición con que se reconstruyen los cuatro meses que el archivo no
# trae. No es un supuesto libre: es la mediana del factor implícito en el propio
# presupuesto (presupuesto 2026 ÷ real del mismo mes de 2025 = 1,216 en la
# mediana, entre 1,12 y 1,34). Se probó con 1,10 y el año quedaba cumplido en
# septiembre, con lo cual la pantalla no decía nada útil; con 1,22 el cierre cae
# donde de verdad está — justo sobre la línea y sin colchón.
FACTOR = 1.22

VERDE = "#2f7a48"
AMBAR = "#B5762F"
ABREV = {"Clubes sociales": "Clubes soc."}

# El presupuesto se firma por canal y ciudad: `presupuesto.csv` no tiene
# vendedor. Filtrar por vendedor las ventas y no el compromiso dejaba la mitad
# de arriba hablando de la empresa entera y la de abajo de una sola persona —y
# pidiéndole a quien tiene diez cuentas la brecha de toda la compañía.
SIN_VENDEDOR = ("vendedor",)


def _div(a, b, sino=0.0):
    """División que no tumba la pantalla cuando el filtro deja el denominador en cero."""
    b = float(b or 0)
    return float(a) / b if b else sino


def _lin(n: int) -> str:
    """«1 línea» / «4 líneas». La concordancia se rompe justo con un filtro puesto."""
    return f"{n} línea" if n == 1 else f"{n} líneas"


def _resto_del_anio(p: pd.DataFrame) -> pd.DataFrame:
    """Reconstruye el presupuesto de septiembre a diciembre.

    Con la misma regla con que se armó el original —mismo mes del año anterior
    por el factor de ambición— y, donde no hay año anterior, con el promedio de
    los últimos tres meses. Esa excepción no es un parche: Medellín abrió en
    marzo, así que para esa ciudad no existe un 2025 contra el cual proyectar y
    lo único honesto es su propio ritmo.
    """
    filas = []
    for (canal, ciudad), g in p.groupby(["canal", "ciudad"]):
        ult3 = float(np.nan_to_num(g[g["mes"] <= CORTE].sort_values("mes")["real"].tail(3).mean()))
        for m in RESTO:
            ant = float(g.loc[g["mes"] == "2025-" + m[5:], "real"].sum())
            filas.append({"mes": m, "canal": canal, "ciudad": ciudad,
                          "presupuesto": (ant if ant > 0 else ult3) * FACTOR})
    return pd.DataFrame(filas, columns=["mes", "canal", "ciudad", "presupuesto"])


def _forma_del_cierre(p: pd.DataFrame):
    """Cuánto vale cada mes de septiembre a diciembre, medido en «agostos».

    El compromiso de esos cuatro meses se reconstruyó sobre los mismos meses de
    2025 —temporada alta— así que proyectar la entrega como «agosto cuatro
    veces» compara dos cosas distintas y produce el falso empate que hacía ver
    apretado un año que no lo está. Se toma solo la FORMA de 2025 (cada mes
    contra su propio agosto) y se aplica al nivel de hoy: así la proyección
    hereda la estacionalidad pero no el crecimiento interanual, que sería
    justificarse a sí misma.

    La forma se saca SIEMPRE de toda la operación, nunca del recorte filtrado:
    la temporada es del calendario, no de la línea, y una línea chica no tiene
    meses suficientes para tener estacionalidad propia. Con la de Discotecas ·
    Bogotá —trece millones de compromiso en el año— el diciembre de 2025 salía
    valiendo diez agostos y la proyección terminaba en 1.580% del compromiso.

    Devuelve (factores, hay_historia). Sin 2025 contra el cual medir se queda
    plana y la pantalla lo dice.
    """
    r = p[(p["mes"] >= "2025-01") & (p["mes"] <= "2025-12")].groupby("mes")["real"].sum()
    ago = float(r.get("2025-08", 0))
    if ago > 0:
        f = [float(r.get("2025-" + m[5:], 0)) / ago for m in RESTO]
        if all(x > 0 for x in f):
            return f, True
    return [1.0] * len(RESTO), False


def _lineas(d: pd.DataFrame, por_ciudad: bool = True) -> pd.DataFrame:
    """Agrega a nivel de línea de compromiso. Una línea es canal × ciudad."""
    claves = ["canal", "ciudad"] if por_ciudad else ["canal"]
    g = d.groupby(claves, as_index=False).agg(
        presupuesto=("presupuesto", "sum"), real=("real", "sum"))
    g["brecha"] = g["real"] - g["presupuesto"]
    g["cumplimiento"] = [_div(r, p) * 100 for r, p in zip(g["real"], g["presupuesto"])]
    g["peso"] = g["presupuesto"] / max(g["presupuesto"].sum(), 1) * 100
    g["etiqueta"] = (g["canal"].map(lambda c: ABREV.get(c, c)) +
                     (" · " + g["ciudad"] if por_ciudad else ""))
    return g


def _cascada(g: pd.DataFrame, base: float, total: float, titulo_eje: str) -> go.Figure:
    """De lo comprometido a lo real, con cada línea aportando su desviación."""
    g = g.sort_values("brecha")
    etiquetas = [e.replace(" · ", "<br>") for e in g["etiqueta"]]
    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute"] + ["relative"] * len(g) + ["total"],
        x=["Comprometido"] + etiquetas + ["Vendido"],
        y=[base] + list(g["brecha"]) + [0],
        text=[cop(base, 0)] + [signo_cop(v) for v in g["brecha"]] + [cop(total, 0)],
        textposition="outside", textfont=dict(size=10),
        connector=dict(line=dict(color=PALIDO, width=1)),
        increasing=dict(marker=dict(color=VERDE)),
        decreasing=dict(marker=dict(color=ACENTO)),
        totals=dict(marker=dict(color=PRIMARIO))))
    fig.update_yaxes(title=titulo_eje)
    return fig


def signo_cop(v) -> str:
    """Brecha con signo. Debajo de cien millones va con decimal a propósito:
    redondear 3.893.264 a «$4 M» borra justo la cifra que hay que ir a cobrar."""
    return ("+" if v >= 0 else "−") + cop(abs(v), 0 if abs(v) >= 1e8 else 1)


def render():
    st.markdown(HEADER_CSS, unsafe_allow_html=True)
    st.markdown(encabezado(
        "Presupuesto y brecha",
        "Cómo va el año contra el compromiso, qué línea debe la diferencia y "
        "qué falta para cerrar",
        "¿Cuánto me falta?"), unsafe_allow_html=True)
    filtros.encabezado_filtro(ignorar=SIN_VENDEDOR)

    # El filtro de periodo NO se aplica aquí a propósito. Este módulo mide un
    # año fiscal contra un compromiso anual; dejar que «Trimestre» recorte la
    # serie haría que el acumulado dijera una cosa y el compromiso otra, que es
    # exactamente el error que la pantalla existe para evitar. Ciudad y canal sí
    # se respetan; vendedor no existe en el compromiso y se ignora ENTERO —en
    # las ventas también— para que las dos mitades de la pantalla hablen del
    # mismo universo.
    vendedor = filtros.elegido("vendedor")
    if vendedor:
        st.info(
            f"El presupuesto se firma por canal y ciudad: no hay meta por "
            f"vendedor. Esta pantalla **ignora el filtro de {vendedor}** y "
            f"muestra la operación completa — repartir la meta de un canal "
            f"entre sus vendedores sería inventar una cuota que nadie firmó, y "
            f"pedirle a una persona la brecha de toda la compañía. Para mirar a "
            f"{vendedor}, la pantalla es **Equipo comercial**.")

    p = filtros.aplicar(gerencia.presupuesto(), col_mes=None, ignorar=SIN_VENDEDOR)
    if p.empty:
        st.info("El filtro activo no deja ninguna línea de presupuesto. "
                "Quítalo en la barra lateral para ver el compromiso completo.")
        return

    ytd = p[(p["mes"] >= INICIO_ANIO) & (p["mes"] <= CORTE)]
    mes = p[p["mes"] == CORTE]
    if ytd.empty or mes.empty:
        st.info("No hay meses de 2026 con compromiso bajo el filtro activo.")
        return
    pres_ytd, real_ytd = float(ytd["presupuesto"].sum()), float(ytd["real"].sum())
    pres_mes, real_mes = float(mes["presupuesto"].sum()), float(mes["real"].sum())
    cumpl_ytd = _div(real_ytd, pres_ytd) * 100
    cumpl_mes = _div(real_mes, pres_mes) * 100

    resto = _resto_del_anio(p)
    pres_resto = float(resto["presupuesto"].sum())
    compromiso_anual = pres_ytd + pres_resto
    falta_anual = compromiso_anual - real_ytd
    dias_de_venta = _div(falta_anual, real_mes) * 30

    lin_mes = _lineas(mes)
    lin_ytd = _lineas(ytd)
    debajo = lin_mes[lin_mes["brecha"] < 0]
    deuda_mes = float(debajo["brecha"].sum())

    # ── Los cuatro números ──────────────────────────────────────────────────
    k = st.columns(4, gap="small")
    k[0].markdown(kpi(
        "Año contra compromiso", pct(cumpl_ytd, 0),
        f"{cop(real_ytd, 0)} sobre {cop(pres_ytd, 0)} comprometidos",
        cumpl_ytd >= 100, "🎯",
        "Enero a agosto. El acumulado es lo único que se puede defender en junta: "
        "un mes bueno tapa uno malo, ocho meses no.",
        "Un presupuesto sano se cumple entre 95% y 110%"), unsafe_allow_html=True)
    k[1].markdown(kpi(
        f"El mes ({mes_es(CORTE)})", pct(cumpl_mes, 0),
        f"{signo_cop(real_mes - pres_mes)} contra lo pedido",
        cumpl_mes >= 100, "📅",
        "El mes solo es útil para ver la dirección; la decisión se toma sobre el "
        "acumulado y la tendencia."), unsafe_allow_html=True)
    # La brecha viva casi siempre va a ser un número pequeño al lado de la venta
    # del mes, y hay que decirlo en la misma tarjeta: es el único dinero de esta
    # pantalla que tiene dueño y fecha, no es la desviación del mes.
    peso_deuda = _div(abs(deuda_mes), real_mes) * 100
    k[2].markdown(kpi(
        "Brecha viva del mes", cop(abs(deuda_mes)),
        f"{_lin(len(debajo))} de {len(lin_mes)} debajo · "
        f"{pct(peso_deuda, 1)} de lo vendido en el mes",
        len(debajo) == 0, "🩸",
        "Lo que las líneas que no llegaron le deben al mes. No es plata grande: "
        "es la única con nombre, y la única que se puede cobrar esta semana.")
        if len(debajo) else kpi(
        "Brecha viva del mes", "Ninguna",
        f"{_lin(len(lin_mes))} y todas cumplieron", True, "✓",
        "Ninguna línea quedó debajo de su compromiso en el mes."),
        unsafe_allow_html=True)
    k[3].markdown(kpi(
        "Falta para cerrar el año", cop(max(falta_anual, 0), 0),
        f"{dias_de_venta:.0f} días de venta al ritmo de {mes_es(CORTE)}"
        if falta_anual > 0 else "el compromiso anual ya está cubierto",
        falta_anual <= 0 or dias_de_venta < 120, "🏁",
        "Contra el compromiso de los doce meses. Septiembre a diciembre se "
        "reconstruye con la regla del propio presupuesto.",
        f"Quedan {len(RESTO)} meses, que son {len(RESTO) * 30} días"),
        unsafe_allow_html=True)

    st.markdown(espacio(18), unsafe_allow_html=True)

    # ── El año, mes a mes ───────────────────────────────────────────────────
    st.markdown('<div class="ky-sub">El año contra el compromiso, mes a mes</div>',
                unsafe_allow_html=True)
    m = ytd.groupby("mes", as_index=False).agg(
        presupuesto=("presupuesto", "sum"), real=("real", "sum"))
    m["cumplimiento"] = [_div(r, pr) * 100 for r, pr in zip(m["real"], m["presupuesto"])]
    m["etq"] = m["mes"].map(mes_es)

    fig = go.Figure()
    fig.add_trace(go.Bar(x=m["etq"], y=m["presupuesto"], name="Comprometido",
                         marker_color=PALIDO))
    fig.add_trace(go.Bar(x=m["etq"], y=m["real"], name="Vendido",
                         marker_color=PRIMARIO))
    fig.add_trace(go.Scatter(x=m["etq"], y=m["cumplimiento"], name="Cumplimiento",
                             yaxis="y2", mode="lines+markers",
                             line=dict(color=ACENTO, width=2.2),
                             marker=dict(size=7),
                             hovertemplate="%{y:.0f}% del compromiso<extra></extra>"))
    fig.update_layout(barmode="group")
    fig = light(fig, 340, moneda=True)
    fig.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False,
                                  ticksuffix="%", tickfont=dict(color=ACENTO),
                                  rangemode="tozero"))
    st.plotly_chart(fig, width="stretch", theme=None, config=PLOTLY_CONFIG)
    bajo_100 = int((m["cumplimiento"] < 100).sum())
    st.caption(
        f"La línea coral es el cumplimiento. Que **no baje nunca del 100%** en "
        f"{len(m)} meses no es una buena noticia: es la señal de que el "
        f"compromiso se armó sobre el año anterior más "
        f"{pct((FACTOR - 1) * 100, 0)} mientras el negocio crecía mucho más. Un "
        f"presupuesto que jamás se incumple no mide a nadie."
        if bajo_100 == 0 else
        f"La línea coral es el cumplimiento. Bajó del 100% en "
        f"{bajo_100} de {len(m)} meses; el resto del año va por encima, y eso "
        f"pasa porque el compromiso se armó sobre el año anterior más "
        f"{pct((FACTOR - 1) * 100, 0)} mientras el negocio crecía mucho más.")

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── De dónde sale la desviación ─────────────────────────────────────────
    st.markdown('<div class="ky-sub">De dónde sale la desviación</div>',
                unsafe_allow_html=True)
    corte = st.radio(
        "Qué descomponer", ["Año acumulado, por canal", "Agosto, línea por línea"],
        horizontal=True, key="pr_cascada", label_visibility="collapsed")

    if corte.startswith("Año"):
        g = _lineas(ytd, por_ciudad=False)
        base, total = pres_ytd, real_ytd
        pie = ("El año es una pregunta estratégica: **qué canal** sostiene la "
               "desviación. Por eso se mira sin abrir ciudad.")
    else:
        g = lin_mes
        base, total = pres_mes, real_mes
        pie = ("El mes es una pregunta operativa: **a quién se llama hoy**. Por "
               "eso se abre canal y ciudad, que es el nivel al que alguien "
               "responde.")
    st.plotly_chart(light(_cascada(g, base, total, "Desviación contra el compromiso"),
                          400, moneda=True), width="stretch")
    st.caption(pie)

    # El panel habla SIEMPRE del año, aunque el gráfico esté abierto en el mes:
    # la lectura de fondo —el presupuesto dejó de medir— es anual, y cambiarla
    # según el botón que alguien oprimió sería un análisis distinto cada vez.
    #
    # Y habla al MISMO nivel que la tabla que viene diez líneas abajo —canal ×
    # ciudad—. Mezclar canal arriba y línea abajo hacía que el panel llamara
    # «la única a la que la meta le aprieta» a una línea que la propia tabla
    # mostraba en 154%.
    motor = lin_ytd.nlargest(1, "brecha").iloc[0]
    ancla = lin_ytd.nlargest(1, "peso").iloc[0]
    desv_total = float(lin_ytd.loc[lin_ytd["brecha"] > 0, "brecha"].sum())
    aprietan = lin_ytd[lin_ytd["cumplimiento"] < 100].sort_values("cumplimiento")
    extremo = lin_ytd.nlargest(1, "cumplimiento").iloc[0]

    exceso = cumpl_ytd - 100
    if exceso >= 100:
        nivel = "que se supera por más del doble"
    elif exceso >= 15:
        nivel = f"que se supera en {pct(exceso, 0)}"
    else:
        nivel = "que se cumple raspando"

    if cumpl_ytd < 110:
        cuerpo = (
            f"El año va en <b>{pct(cumpl_ytd, 0)}</b> del compromiso. En este "
            f"recorte el presupuesto sí está midiendo: la meta y la venta van a "
            f"la par, y una conversación de desempeño aquí tiene sustento. "
            f"Mira la operación completa para ver por qué deja de medirla.")
    else:
        cuerpo = (
            f"El año va en <b>{pct(cumpl_ytd, 0)}</b> del compromiso. Un "
            f"presupuesto {nivel} dejó de ser un control: nadie tiene variable "
            f"en riesgo, ninguna línea está formalmente mal y por lo tanto "
            f"ninguna conversación de desempeño tiene sustento.")
        # La mezcla solo se afirma cuando de verdad hay mezcla que mirar: con un
        # filtro de canal puesto, motor y ancla colapsan en la misma línea y el
        # párrafo se quedaba diciendo que aporta «100% de la desviación cargando
        # 93% del compromiso», que no es un desbalance, es una sola línea.
        share_motor = _div(motor["brecha"], desv_total) * 100
        if (len(lin_ytd) > 1 and desv_total > 0
                and motor["etiqueta"] != ancla["etiqueta"]
                and share_motor > motor["peso"] + 10):
            cuerpo += (
                f"<br><br>El problema no es el nivel, es la <b>mezcla</b>. "
                f"<b>{motor['etiqueta']}</b> aporta {cop(motor['brecha'], 0)} "
                f"de desviación positiva —{pct(share_motor, 0)} de toda la del "
                f"año— cargando {pct(motor['peso'], 0)} del compromiso: la "
                f"línea que sostiene el año no es la línea a la que se le pidió "
                f"el año. Mientras tanto el {pct(ancla['peso'], 0)} del "
                f"compromiso está puesto sobre <b>{ancla['etiqueta']}</b>, que "
                f"va en {pct(ancla['cumplimiento'], 0)}.")
            if extremo["etiqueta"] not in (motor["etiqueta"], ancla["etiqueta"]):
                cuerpo += (
                    f" El caso extremo es <b>{extremo['etiqueta']}</b>: "
                    f"{pct(extremo['peso'], 1)} del compromiso y "
                    f"{pct(extremo['cumplimiento'], 0)} de cumplimiento.")
        if len(aprietan):
            ap = aprietan.iloc[0]
            if len(aprietan) == 1:
                quienes = ("La única línea a la que la meta todavía le aprieta "
                           "es")
            else:
                quienes = (f"De {_lin(len(lin_ytd))}, a {len(aprietan)} les "
                           f"aprieta todavía la meta; la más apretada es")
            cuerpo += (
                f"<br><br>{quienes} <b>{ap['etiqueta']}</b>: "
                f"{pct(ap['cumplimiento'], 0)} del compromiso y "
                f"{pct(ap['peso'], 1)} del peso. Lo único que este presupuesto "
                f"sigue midiendo pesa {pct(float(aprietan['peso'].sum()), 1)} "
                f"del año.")
        else:
            cuerpo += (
                "<br><br>"
                + ("La única línea de este recorte quedó por encima de su "
                   "compromiso anual. "
                   if len(lin_ytd) == 1 else
                   f"Ninguna de las {len(lin_ytd)} líneas quedó debajo de su "
                   f"compromiso anual. ")
                + "No hay una sola conversación de desempeño que este "
                  "presupuesto pueda sostener.")
    st.markdown(panel(
        "Por qué este presupuesto ya no sirve para controlar nada",
        cuerpo +
        f"<br><br><b>Lo que hay que decidir</b>: volver a armar el presupuesto "
        f"de septiembre sobre el ritmo real, no sobre el año anterior. Un "
        f"compromiso que se cumple sin esfuerzo y otro que no se puede cumplir "
        f"terminan igual — el equipo deja de mirarlo.",
        "🧭", "alerta"), unsafe_allow_html=True)

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── Quién va adelante y quién atrás ─────────────────────────────────────
    st.markdown('<div class="ky-sub">Quién va adelante y quién atrás</div>',
                unsafe_allow_html=True)
    lin_ytd = lin_ytd.sort_values("presupuesto")
    colores = [VERDE if c >= 100 else ACENTO for c in lin_ytd["cumplimiento"]]

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        y=lin_ytd["etiqueta"], x=lin_ytd["real"] / 1e6, orientation="h",
        name="Vendido en el año", marker_color=colores,
        text=[f"{c:,.0f}%".replace(",", ".") for c in lin_ytd["cumplimiento"]],
        textposition="outside", textfont=dict(size=11, color=MUTED),
        # El eje va en millones: la ventana emergente también. Traía el vendido
        # en «$618 M» y, dos renglones abajo, el comprometido en pesos crudos;
        # el mismo número en dos unidades dentro del mismo cuadro.
        customdata=np.stack([lin_ytd["presupuesto"] / 1e6, lin_ytd["brecha"] / 1e6,
                             lin_ytd["peso"]], -1),
        hovertemplate="<b>%{y}</b><br>Vendido: $%{x:,.1f} M"
                      "<br>Comprometido: $%{customdata[0]:,.1f} M"
                      "<br>Brecha: $%{customdata[1]:,.1f} M"
                      "<br>Pesa %{customdata[2]:.1f}% del compromiso<extra></extra>"))
    fig2.add_trace(go.Scatter(
        y=lin_ytd["etiqueta"], x=lin_ytd["presupuesto"] / 1e6, mode="markers",
        name="La meta", marker=dict(symbol="line-ns-open", size=20,
                                    color=TINTA, line=dict(width=2.6)),
        hovertemplate="Meta: $%{x:,.1f} M<extra></extra>"))
    fig2 = light(fig2, 430)
    # En barras horizontales el «x unified» de la plantilla agrupa filas que no
    # tienen nada que ver entre sí y hace ilegible el tooltip.
    fig2.update_layout(hovermode="closest")
    fig2.update_xaxes(title="Vendido enero–agosto · millones de pesos",
                      tickprefix="$", ticksuffix=" M", tickformat=",.0f")
    st.plotly_chart(fig2, width="stretch", theme=None, config=PLOTLY_CONFIG)
    st.caption(
        "El trazo vertical oscuro es la meta de cada línea. Están ordenadas por "
        "**tamaño del compromiso**, no por cumplimiento: una línea pequeña al "
        "700% mueve menos plata que una línea grande al 96%.")

    # Lo pedido contra lo logrado — la tabla que explica el desorden.
    ant = p[(p["mes"] >= "2025-01") & (p["mes"] <= "2025-08")].groupby(
        ["canal", "ciudad"], as_index=False).agg(base=("real", "sum"))
    t = lin_ytd.merge(ant, on=["canal", "ciudad"], how="left")
    t["base"] = t["base"].fillna(0)
    t["pedido"] = [(_div(pr, b) - 1) * 100 if b > 0 else np.nan
                   for pr, b in zip(t["presupuesto"], t["base"])]
    t["logrado"] = [(_div(r, b) - 1) * 100 if b > 0 else np.nan
                    for r, b in zip(t["real"], t["base"])]
    t = t.sort_values("cumplimiento")
    tabla = pd.DataFrame({
        "Línea": t["etiqueta"],
        "Comprometido": t["presupuesto"].map(lambda v: cop(v, 0)),
        "Vendido": t["real"].map(lambda v: cop(v, 0)),
        "Cumple": t["cumplimiento"].map(lambda v: pct(v, 0)),
        "Brecha": t["brecha"].map(signo_cop),
        "Pesa en el compromiso": t["peso"].map(lambda v: pct(v, 1)),
        "Crecimiento pedido": t["pedido"].map(
            lambda v: "sin base" if pd.isna(v) else signo(v, 0)),
        "Crecimiento logrado": t["logrado"].map(
            lambda v: "ciudad nueva" if pd.isna(v) else signo(v, 0)),
    })
    st.dataframe(tabla, hide_index=True, width="stretch")

    sin_base = int(t["pedido"].isna().sum())
    if sin_base:
        st.caption(md(
            f"**{_lin(sin_base)} {'dice' if sin_base == 1 else 'dicen'} «sin "
            f"base»**: son de Medellín, que abrió "
            f"en marzo de 2026. A esas líneas el presupuesto les asignó meta "
            f"desde enero —"
            f"{cop(float(p[(p['ciudad'] == 'Medellín') & (p['mes'].isin(['2026-01', '2026-02']))]['presupuesto'].sum()), 0)} "
            f"de compromiso sobre una ciudad que todavía no existía— y ese "
            f"faltante arrastra su cumplimiento anual hacia abajo sin que nadie "
            f"haya hecho nada mal. Antes de juzgar a Medellín hay que sacarle "
            f"esos dos meses."))

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── La brecha con nombre y apellido ─────────────────────────────────────
    st.markdown('<div class="ky-sub">La brecha con nombre y apellido</div>',
                unsafe_allow_html=True)
    v = filtros.aplicar(b2b.ventas(), col_mes=None, ignorar=SIN_VENDEDOR)

    def _abiertos_presupuesto():
        ab = {k: c for k, c in estado.compromisos().items()
              if c.get("origen") == "Presupuesto" and c.get("estado") == "En curso"}
        if ab:
            st.dataframe(pd.DataFrame([
                {"Id": k, "Compromiso": c["compromiso"], "Dueño": c["dueno"],
                 "Vence": c["vence"], "Vale": cop(c.get("valor", 0), 0)}
                for k, c in ab.items()]), hide_index=True, width="stretch")
        return ab

    # La ficha solo se pinta si hay una línea DEBAJO de su compromiso. Con
    # `nsmallest` a secas siempre salía una —con cualquier filtro de canal la
    # «más rezagada» era una línea al 1.897%, con borde verde, y el formulario
    # proponía «cerrar» una brecha que era excedente.
    if len(debajo):
        rez = debajo.nsmallest(1, "cumplimiento").iloc[0]
        canal_r, ciudad_r = rez["canal"], rez["ciudad"]
        vr = v[(v["canal"] == canal_r) & (v["ciudad"] == ciudad_r) & (v["mes"] == CORTE)]
        if len(vr):
            dueno = vr.groupby("vendedor")["neto"].sum().idxmax()
            parte = _div(vr.groupby("vendedor")["neto"].sum().max(), vr["neto"].sum()) * 100
            cuentas_r = int(vr["cuenta_id"].nunique())
            entregas_r = float(vr["entregas"].sum())
        else:
            dueno, parte, cuentas_r, entregas_r = "sin asignar", 0.0, 0, 0.0

        hist = p[(p["canal"] == canal_r) & (p["ciudad"] == ciudad_r) &
                 (p["mes"] >= "2026-04")].sort_values("mes")
        trayecto = " → ".join(
            f"{mes_es(r['mes'])[:3]} {_div(r['real'], r['presupuesto']) * 100:.0f}%"
            for _, r in hist.iterrows())

        st.markdown(f"""
        <div style="border:1px solid {PALIDO};border-top:4px solid {ACENTO};
             border-radius:6px;padding:18px 22px;background:#fff;margin-bottom:14px">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:20px">
            <div>
              <div style="font-size:9.5px;font-weight:800;letter-spacing:.14em;
                   text-transform:uppercase;color:{CLARO}">
                Línea más rezagada de {mes_es(CORTE)}</div>
              <div style="font-family:'DM Serif Display',Georgia,serif;font-size:27px;
                   color:{TINTA};line-height:1.15;margin:2px 0 4px">
                {rez['canal']} · {rez['ciudad']}</div>
              <div style="font-size:11.5px;color:{CLARO}">
                Responde: <b style="color:{TINTA}">{dueno}</b> ({pct(parte, 0)} de la
                venta de la línea) &nbsp;·&nbsp; {cuentas_r} cuentas activas
                &nbsp;·&nbsp; {entregas_r:.0f} entregas en el mes</div>
              <div style="font-size:11.5px;color:{CLARO};margin-top:4px">
                Trayectoria: {trayecto}</div>
            </div>
            <div style="text-align:right;white-space:nowrap">
              <div style="font-size:9.5px;font-weight:800;letter-spacing:.1em;
                   text-transform:uppercase;color:{CLARO}">Brecha del mes</div>
              <div style="font-size:30px;font-weight:800;line-height:1.1;color:{ACENTO}">
                {signo_cop(rez['brecha'])}</div>
              <div style="font-size:12px;color:{CLARO}">
                {pct(rez['cumplimiento'], 0)} · pesa {pct(rez['peso'], 0)} del mes</div>
            </div>
          </div>
        </div>""", unsafe_allow_html=True)
        st.caption(md(
            f"Esta misma línea llega a **Centro de decisiones** como tarjeta con "
            f"dueño, opciones y costo de no actuar. Aquí lo que se agrega es el "
            f"año: el mes se cobra, el compromiso anual se vuelve a armar."))

        # El compromiso se guarda en disco, no en la sesión: una brecha que se
        # discute el lunes tiene que seguir ahí el lunes siguiente, con dueño.
        with st.expander("Dejar esto comprometido con alguien", expanded=False):
            c1, c2 = st.columns([3, 1])
            # La clave lleva la línea adentro a propósito: con una clave fija,
            # Streamlit conservaba el texto de la línea anterior al cambiar de
            # filtro y el compromiso quedaba guardado con el texto de una línea
            # y el monto de otra.
            texto = c1.text_input(
                "Compromiso",
                f"Cerrar {cop(abs(rez['brecha']))} de brecha en "
                f"{rez['canal']} · {rez['ciudad']}",
                key=f"pr_txt_{canal_r}_{ciudad_r}")
            opciones = sorted(v["vendedor"].dropna().unique().tolist()) or ["Gerencia"]
            idx = opciones.index(dueno) if dueno in opciones else 0
            quien = c2.selectbox("Dueño", opciones, index=idx, key="pr_due")
            if st.button("Registrar compromiso", type="primary", key="pr_btn"):
                cid = estado.nuevo_compromiso(texto, quien, dias=30,
                                              valor=abs(float(rez["brecha"])),
                                              origen="Presupuesto")
                st.success(f"Compromiso {cid} a cargo de {quien}, vence en 30 días. "
                           f"Queda guardado en disco: sigue ahí después de refrescar.")
            _abiertos_presupuesto()
    else:
        st.markdown(f"""
        <div style="border:1px solid {PALIDO};border-top:4px solid {VERDE};
             border-radius:6px;padding:16px 22px;background:#fff;margin-bottom:6px">
          <div style="font-size:9.5px;font-weight:800;letter-spacing:.14em;
               text-transform:uppercase;color:{CLARO}">
            {mes_es(CORTE)}: ninguna línea debajo</div>
          <div style="font-size:13.5px;color:{TINTA};margin-top:6px;line-height:1.6">
            {_lin(len(lin_mes)).capitalize()} de este recorte
            {'cerró' if len(lin_mes) == 1 else 'cerraron'} el mes por encima de
            su compromiso, así que no hay brecha que asignarle a nadie. Con toda la
            operación a la vista sí la hay — y es lo único de esta pantalla que se
            cobra esta semana.</div>
        </div>""", unsafe_allow_html=True)
        if estado.compromisos():
            with st.expander("Compromisos de presupuesto abiertos", expanded=False):
                if not _abiertos_presupuesto():
                    st.caption("No hay compromisos de presupuesto en curso.")

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── Lo que falta para cerrar el año ─────────────────────────────────────
    st.markdown('<div class="ky-sub">Lo que falta para cerrar el año</div>',
                unsafe_allow_html=True)
    meses_anio = sorted(m["mes"].tolist()) + RESTO
    comp_mes = (m.set_index("mes")["presupuesto"].reindex(sorted(m["mes"].tolist())).tolist() +
                resto.groupby("mes")["presupuesto"].sum().reindex(RESTO).fillna(0).tolist())
    real_acum = list(np.cumsum(m.set_index("mes")["real"]
                               .reindex(sorted(m["mes"].tolist())).values))

    # La proyección va corregida por estacionalidad, no plana. El compromiso de
    # sep–dic se reconstruyó sobre temporada alta; enfrentarlo contra «agosto
    # cuatro veces» producía un falso empate —101%, «sin margen»— que era del
    # método, no del negocio.
    forma, hay_forma = _forma_del_cierre(gerencia.presupuesto())
    proy_mes = [real_mes * f for f in forma]
    proy = list(real_acum[-1] + np.cumsum(proy_mes))

    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        x=[mes_es(x) for x in meses_anio], y=list(np.cumsum(comp_mes)),
        name="Compromiso acumulado", mode="lines",
        line=dict(color=CLARO, width=2)))
    fig3.add_trace(go.Scatter(
        x=[mes_es(x) for x in sorted(m["mes"].tolist())], y=real_acum,
        name="Vendido acumulado", mode="lines+markers",
        line=dict(color=PRIMARIO, width=3)))
    fig3.add_trace(go.Scatter(
        # Empieza en agosto, sobre el último punto del acumulado real: sin ese
        # ancla la línea punteada arrancaba en el aire, con un salto visible
        # entre donde termina lo vendido y donde empieza lo proyectado.
        x=[mes_es(CORTE)] + [mes_es(x) for x in RESTO],
        y=[real_acum[-1]] + proy,
        name=("Proyección con la estacionalidad de 2025" if hay_forma
              else f"Proyección al ritmo de {mes_es(CORTE)}"),
        mode="lines", line=dict(color=ACENTO, width=2.4, dash="dash")))
    st.plotly_chart(light(fig3, 340, moneda=True), width="stretch", theme=None, config=PLOTLY_CONFIG)

    entrega_resto = float(sum(proy_mes))
    cierre = real_ytd + entrega_resto
    cumpl_cierre = _div(cierre, compromiso_anual) * 100
    exigido_resto = pres_resto
    cumpl_resto = _div(entrega_resto, exigido_resto) * 100
    dic = proy_mes[-1] if proy_mes else 0.0
    prom_ene_ago = _div(real_ytd, len(m))
    prom_resto = _div(entrega_resto, len(RESTO))

    st.caption(md(
        f"El compromiso de los doce meses suma **{cop(compromiso_anual, 0)}**. "
        f"Van {cop(real_ytd, 0)} y "
        + (f"faltan **{cop(falta_anual, 0)}**, que al ritmo de {mes_es(CORTE)} "
           f"son {dias_de_venta:.0f} días de venta. "
           if falta_anual > 0 else
           "el compromiso anual **ya está cubierto** con ocho meses. ")
        + f"Los cuatro meses que quedan piden {cop(exigido_resto, 0)}; el ritmo "
          f"de hoy con la curva de fin de año entrega {cop(entrega_resto, 0)}: "
          f"**{pct(cumpl_resto, 0)}**."))

    if not hay_forma:
        titulo_cierre = "El cierre va sin temporada: es un piso, no un pronóstico"
        primera = (
            f"No hay un 2025 completo contra el cual medir la curva de fin de "
            f"año, así que la proyección va plana —{mes_es(CORTE)} repetido "
            f"cuatro veces—: el año termina en <b>{cop(cierre, 0)}</b>, "
            f"{pct(cumpl_cierre, 0)} del compromiso, y los cuatro meses que "
            f"quedan entregan {pct(cumpl_resto, 0)} de lo que piden. Léelo como "
            f"un piso: el compromiso de sep–dic sí está armado sobre temporada "
            f"alta y esta proyección no tiene con qué verla.")
    elif cumpl_resto >= 115:
        titulo_cierre = "El año no se cierra: se cierra de sobra, y eso es el problema"
        primera = (
            f"Con la estacionalidad de 2025 aplicada al ritmo de "
            f"{mes_es(CORTE)}, el año termina en <b>{cop(cierre, 0)}</b>, "
            f"{pct(cumpl_cierre, 0)} del compromiso. Los cuatro meses que "
            f"quedan piden {cop(exigido_resto, 0)} y el negocio, sin hacer "
            f"nada distinto, entrega {pct(cumpl_resto, 0)} de eso. La razón es "
            f"aritmética: el compromiso de sep–dic se armó sobre los mismos "
            f"meses de 2025 más {pct((FACTOR - 1) * 100, 0)}, y la venta de hoy "
            f"ya va muy por encima de ese 2025. Cumplirlo no exige nada, y por "
            f"eso no sirve para pedirle nada a nadie.")
    else:
        titulo_cierre = "El año se cierra, pero el último trimestre no sobra"
        primera = (
            f"Con la estacionalidad de 2025 aplicada al ritmo de "
            f"{mes_es(CORTE)}, el año termina en <b>{cop(cierre, 0)}</b>, "
            f"{pct(cumpl_cierre, 0)} del compromiso. Los cuatro meses que "
            f"quedan piden {cop(exigido_resto, 0)} y el ritmo de hoy entrega "
            f"{pct(cumpl_resto, 0)} de eso: aquí sí hay que empujar.")

    # El párrafo del calendario solo tiene sentido con la forma de 2025 puesta:
    # con la proyección plana, «sep–dic promedia más que ene–ago» no dice nada
    # del calendario, dice que agosto fue más grande que el promedio del año.
    if hay_forma:
        calendario = (
            f"Lo que sí cambia es el <b>calendario</b>: septiembre a diciembre "
            f"promedia {cop(prom_resto, 0)} al mes contra "
            f"{cop(prom_ene_ago, 0)} de enero a agosto"
            + (f", y diciembre solo vale {cop(dic, 0)}" if dic > prom_ene_ago else "")
            + ". ")
    else:
        calendario = ("De todas formas el calendario manda: noviembre y "
                      "diciembre son los dos meses grandes del año en licores. ")

    st.markdown(panel(
        titulo_cierre,
        primera + "<br><br>" + calendario
        + f"La consecuencia no es comercial, es de <b>inventario</b>: lo que "
          f"se venda en diciembre hay que haberlo comprado en octubre, y una "
          f"importación tarda del orden de sesenta días. La decisión de cerrar "
          f"el año no se toma en diciembre — se toma ahora, con la orden de "
          f"compra.<br><br>"
          f"<b>Alcance</b>: este cierre es solo el B2B presupuestado — canal × "
          f"ciudad. El cierre de la compañía entera, con The Store, The Lounge "
          f"y distribución, está en <b>Proyección de cierre</b>, sobre otro "
          f"universo de datos y con otro método. Son dos números distintos a "
          f"propósito y no se suman.",
        "🏁", "azul" if cumpl_cierre >= 100 else "alerta"), unsafe_allow_html=True)

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── Las tres palancas ───────────────────────────────────────────────────
    va = v[v["mes"] == CORTE]
    base_cuentas = filtros.aplicar(b2b.cuentas(), col_mes=None, ignorar=SIN_VENDEDOR)
    activas = int(va["cuenta_id"].nunique())
    dormidas = max(len(base_cuentas) - activas, 0)
    entregas_mes = float(va["entregas"].sum())
    ticket = _div(va["neto"].sum(), entregas_mes)
    frec = _div(entregas_mes, activas)
    por_cuenta = _div(va["neto"].sum(), activas)

    serie = v[v["mes"] >= INICIO_ANIO].groupby("mes")["cuenta_id"].nunique()
    pico = int(serie.max()) if len(serie) else activas
    mes_pico = str(serie.idxmax()) if len(serie) else CORTE
    mes_inicio = str(serie.index[0]) if len(serie) else INICIO_ANIO
    objetivo = max(falta_anual / max(len(RESTO), 1), abs(deuda_mes), 0.0)

    # Las tres palancas se miden por lo que hay que MOVERLAS, no por lo que
    # traería moverlas un poco cada una: así son comparables. Antes la tercera
    # se calculaba como «una entrega más por cada cuenta activa al ticket
    # medio» —$213 M, casi el doble de la brecha— y dejaba la caja diciendo que
    # la palanca más rápida sobraba sola mientras el cierre recomendaba otra.
    #
    # Medidas así las tres piden el MISMO porcentaje, y no es casualidad: la
    # venta es cuentas × frecuencia × ticket, de modo que mover cualquiera de
    # los tres factores un x% da el mismo x% de venta. Lo que las separa no es
    # cuánta plata traen, es en cuánto tiempo y qué le hacen al margen.
    mueve_pct = _div(objetivo, float(va["neto"].sum())) * 100
    n_cuentas = _div(objetivo, por_cuenta)
    alza_ticket = _div(objetivo, entregas_mes)
    frec_extra = _div(_div(objetivo, ticket), activas)
    gana_ticket = real_mes * 0.10
    cubre_10 = _div(gana_ticket, objetivo) * 100

    # Con la base casi toda comprando, «despertar dormidas» deja de ser una
    # opción real y hay que decirlo: mandar al equipo a reactivar tres cuentas
    # cuando la brecha vale cien millones es perder el trimestre.
    saturada = dormidas <= max(len(base_cuentas) * 0.15, 1)
    if dormidas == 0:
        cuentas_txt = (
            f"Las {len(base_cuentas)} cuentas de la base compraron este mes: no "
            f"queda una sola por despertar. Crecer en cuentas ya no es "
            f"reactivar, es abrir, y eso es otro trabajo y otro plazo.")
    elif saturada:
        cuentas_txt = (
            f"Solo {dormidas} de {len(base_cuentas)} cuentas de la base no "
            f"{'compró' if dormidas == 1 else 'compraron'} este mes: <b>la base "
            f"está agotada</b>. Crecer en cuentas ya no es reactivar, es abrir, "
            f"y eso es otro trabajo y otro plazo.")
    else:
        cuentas_txt = (
            f"Quedan {dormidas} cuentas en la base sin compra este mes: "
            f"despertar una cuenta conocida cuesta la mitad que abrir una nueva "
            f"y entrega en la mitad del tiempo.")

    if objetivo <= 0:
        st.markdown(panel(
            "No hay brecha que cerrar en este recorte",
            f"El compromiso anual de lo que está filtrado ya está cubierto y "
            f"ninguna línea quedó debajo en {mes_es(CORTE)}, así que no hay una "
            f"cifra mensual que repartir entre palancas. Quita el filtro para "
            f"ver la aritmética sobre la operación completa.",
            "🔧", "azul"), unsafe_allow_html=True)
        return

    st.markdown(panel(
        "La brecha se cierra de tres maneras y ninguna tarda lo mismo",
        f"La brecha anual repartida en los cuatro meses que quedan son "
        f"<b>{cop(objetivo, 0)} al mes</b>. "
        + ("La curva de fin de año los entrega sola <i>si</i> la temporada "
           "llega como el año pasado; estas tres palancas son lo que hay si no "
           "llega, o si el año no se quiere jugar entero en noviembre y "
           "diciembre. " if hay_forma and cumpl_resto >= 115 else
           "Eso es lo que hay que sacar de más cada mes hasta diciembre. ")
        + f"Con {activas} cuentas activas, "
        f"{cop(por_cuenta)} por cuenta y {cop(ticket)} por entrega, cada una "
        f"pide moverse <b>{pct(mueve_pct, 0)}</b>:<br><br>"
        f"<b>1. Más cuentas — {np.ceil(n_cuentas):.0f} cuentas nuevas.</b> "
        f"Es la palanca que sostuvo el año: las activas pasaron de "
        f"{int(serie.iloc[0]) if len(serie) else activas} en "
        f"{mes_es(mes_inicio)} a {pico} en {mes_es(mes_pico)}, y ahí se "
        f"estancó — hoy son {activas}. {cuentas_txt} <i>Madura en 60 a 90 "
        f"días</i>: prospecto, primera compra y recompra. Si la brecha es de "
        f"este trimestre, llega tarde.<br>"
        f"<b>2. Más ticket — {cop(alza_ticket)} más por entrega.</b> Se cobra "
        f"en el <i>próximo pedido</i>: mezcla hacia referencias de mayor valor, "
        f"pedido mínimo, y menos descuento donde el margen lo aguante. Es la "
        f"única que actúa este mes y la que tiene techo: subir el ticket un "
        f"10% —lo máximo que aguanta un trimestre sin perder cuentas— son "
        f"{cop(gana_ticket, 0)}, o sea {pct(cubre_10, 0)} de lo que falta. "
        f"Sola no alcanza.<br>"
        f"<b>3. Más frecuencia — {num(frec_extra, 2)} entregas más por cuenta "
        f"al mes</b>, sobre las {num(frec, 1)} de hoy. Es la más rápida de "
        f"todas y la única que <b>empeora el negocio</b>: cada entrega cuesta "
        f"casi lo mismo lleve cuatro botellas o cuarenta, así que la venta sube "
        f"y el margen servido baja.<br><br>"
        f"<b>El orden correcto</b>: ticket ahora, porque es lo único que se "
        f"cobra este mes, sabiendo que cubre {pct(cubre_10, 0)}; el resto, "
        f"frecuencia y solo donde el margen después de servir lo aguante — eso "
        f"se mira en <b>Rentabilidad por cuenta</b>, no aquí. Prospección "
        f"nueva ahora también, pero contándola para el primer trimestre del año "
        f"entrante, no para diciembre.",
        "🔧", "alerta"), unsafe_allow_html=True)
