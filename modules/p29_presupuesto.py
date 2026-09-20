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
si el año se cierra, y esa es la única pregunta que importa en septiembre.

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


def _div(a, b, sino=0.0):
    """División que no tumba la pantalla cuando el filtro deja el denominador en cero."""
    b = float(b or 0)
    return float(a) / b if b else sino


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
    filtros.encabezado_filtro()

    # El filtro de periodo NO se aplica aquí a propósito. Este módulo mide un
    # año fiscal contra un compromiso anual; dejar que «Trimestre» recorte la
    # serie haría que el acumulado dijera una cosa y el compromiso otra, que es
    # exactamente el error que la pantalla existe para evitar. Ciudad, canal y
    # vendedor sí se respetan.
    p = filtros.aplicar(gerencia.presupuesto(), col_mes=None)
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
    k[2].markdown(kpi(
        "Brecha viva del mes", cop(abs(deuda_mes)),
        f"{len(debajo)} de {len(lin_mes)} líneas debajo",
        len(debajo) == 0, "🩸",
        "Lo que las líneas que no llegaron le deben al mes. Esto es lo que hay "
        "que cobrarle a alguien esta semana, no el promedio.")
        if len(debajo) else kpi(
        "Brecha viva del mes", "Ninguna",
        f"las {len(lin_mes)} líneas cumplieron", True, "✓",
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
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        f"La línea coral es el cumplimiento. Que **no baje nunca del 100%** en "
        f"ocho meses no es una buena noticia: es la señal de que el compromiso "
        f"se armó sobre el año anterior más {pct((FACTOR - 1) * 100, 0)} mientras "
        f"el negocio crecía mucho más. Un presupuesto que jamás se incumple no "
        f"mide a nadie.")

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
                          400, moneda=True), use_container_width=True)
    st.caption(pie)

    # El panel habla SIEMPRE del año, aunque el gráfico esté abierto en el mes:
    # la lectura de fondo —el presupuesto dejó de medir— es anual, y cambiarla
    # según el botón que alguien oprimió sería un análisis distinto cada vez.
    g_anio = _lineas(ytd, por_ciudad=False)
    motor = g_anio.nlargest(1, "brecha").iloc[0]
    ancla = lin_ytd.nlargest(1, "peso").iloc[0]
    st.markdown(panel(
        "Por qué este presupuesto ya no sirve para controlar nada",
        f"El año va en <b>{pct(cumpl_ytd, 0)}</b> del compromiso. Un presupuesto "
        f"que se supera por más del doble dejó de ser un control: nadie tiene "
        f"variable en riesgo, ninguna línea está formalmente mal y por lo tanto "
        f"ninguna conversación de desempeño tiene sustento.<br><br>"
        f"El problema no es el nivel, es la <b>mezcla</b>. "
        f"<b>{motor['etiqueta']}</b> aporta {cop(motor['brecha'], 0)} de "
        f"desviación positiva cargando apenas {pct(motor['peso'], 0)} del "
        f"compromiso: es la línea que sostiene el año y es a la que menos se le "
        f"pidió. Mientras tanto el {pct(ancla['peso'], 0)} del compromiso está "
        f"puesto sobre <b>{ancla['etiqueta']}</b>, que crece a un ritmo normal "
        f"y es la única línea a la que la meta todavía le aprieta.<br><br>"
        f"<b>Lo que hay que decidir</b>: volver a armar el presupuesto de "
        f"septiembre sobre el ritmo real, no sobre el año anterior. Un "
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
        customdata=np.stack([lin_ytd["presupuesto"], lin_ytd["brecha"],
                             lin_ytd["peso"]], -1),
        hovertemplate="<b>%{y}</b><br>Vendido: $%{x:,.0f} M"
                      "<br>Comprometido: $%{customdata[0]:,.0f}"
                      "<br>Brecha: $%{customdata[1]:,.0f}"
                      "<br>Pesa %{customdata[2]:.1f}% del compromiso<extra></extra>"))
    fig2.add_trace(go.Scatter(
        y=lin_ytd["etiqueta"], x=lin_ytd["presupuesto"] / 1e6, mode="markers",
        name="La meta", marker=dict(symbol="line-ns-open", size=20,
                                    color=TINTA, line=dict(width=2.6)),
        hovertemplate="Meta: $%{x:,.0f} M<extra></extra>"))
    fig2 = light(fig2, 430)
    # En barras horizontales el «x unified» de la plantilla agrupa filas que no
    # tienen nada que ver entre sí y hace ilegible el tooltip.
    fig2.update_layout(hovermode="closest")
    fig2.update_xaxes(title="Vendido enero–agosto · millones de pesos",
                      tickprefix="$", ticksuffix=" M", tickformat=",.0f")
    st.plotly_chart(fig2, use_container_width=True)
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
            f"**{sin_base} líneas dicen «sin base»**: son de Medellín, que abrió "
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
    rez = lin_mes.nsmallest(1, "cumplimiento").iloc[0]
    canal_r, ciudad_r = rez["canal"], rez["ciudad"]

    v = filtros.aplicar(b2b.ventas(), col_mes=None)
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
    trayecto = " → ".join(f"{mes_es(r['mes'])[:3]} {_div(r['real'], r['presupuesto']) * 100:.0f}%"
                          for _, r in hist.iterrows())

    st.markdown(f"""
    <div style="border:1px solid {PALIDO};border-top:4px solid
         {VERDE if rez['cumplimiento'] >= 100 else ACENTO};border-radius:6px;
         padding:18px 22px;background:#fff;margin-bottom:14px">
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
          <div style="font-size:30px;font-weight:800;line-height:1.1;
               color:{VERDE if rez['brecha'] >= 0 else ACENTO}">
            {signo_cop(rez['brecha'])}</div>
          <div style="font-size:12px;color:{CLARO}">
            {pct(rez['cumplimiento'], 0)} · pesa {pct(rez['peso'], 0)} del mes</div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    # El compromiso se guarda en disco, no en la sesión: una brecha que se
    # discute el lunes tiene que seguir ahí el lunes siguiente, con dueño.
    with st.expander("Dejar esto comprometido con alguien", expanded=False):
        c1, c2 = st.columns([3, 1])
        texto = c1.text_input(
            "Compromiso",
            f"Cerrar {cop(abs(rez['brecha']))} de brecha en "
            f"{rez['canal']} · {rez['ciudad']}", key="pr_txt")
        opciones = sorted(v["vendedor"].dropna().unique().tolist()) or ["Gerencia"]
        idx = opciones.index(dueno) if dueno in opciones else 0
        quien = c2.selectbox("Dueño", opciones, index=idx, key="pr_due")
        if st.button("Registrar compromiso", type="primary", key="pr_btn"):
            cid = estado.nuevo_compromiso(texto, quien, dias=30,
                                          valor=abs(float(rez["brecha"])),
                                          origen="Presupuesto")
            st.success(f"Compromiso {cid} a cargo de {quien}, vence en 30 días. "
                       f"Queda guardado en disco: sigue ahí después de refrescar.")
        abiertos = {k: c for k, c in estado.compromisos().items()
                    if c.get("origen") == "Presupuesto" and c.get("estado") == "En curso"}
        if abiertos:
            st.dataframe(pd.DataFrame([
                {"Id": k, "Compromiso": c["compromiso"], "Dueño": c["dueno"],
                 "Vence": c["vence"], "Vale": cop(c.get("valor", 0), 0)}
                for k, c in abiertos.items()]), hide_index=True, width="stretch")

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── Lo que falta para cerrar el año ─────────────────────────────────────
    st.markdown('<div class="ky-sub">Lo que falta para cerrar el año</div>',
                unsafe_allow_html=True)
    meses_anio = sorted(m["mes"].tolist()) + RESTO
    comp_mes = (m.set_index("mes")["presupuesto"].reindex(sorted(m["mes"].tolist())).tolist() +
                resto.groupby("mes")["presupuesto"].sum().reindex(RESTO).fillna(0).tolist())
    real_acum = list(np.cumsum(m.set_index("mes")["real"]
                               .reindex(sorted(m["mes"].tolist())).values))
    proy = [real_acum[-1] + real_mes * (i + 1) for i in range(len(RESTO))]

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
        x=[mes_es(x) for x in RESTO], y=proy,
        name=f"Proyección al ritmo de {mes_es(CORTE)}", mode="lines",
        line=dict(color=ACENTO, width=2.4, dash="dash")))
    st.plotly_chart(light(fig3, 340, moneda=True), use_container_width=True)

    cierre = proy[-1] if proy else real_ytd
    cumpl_cierre = _div(cierre, compromiso_anual) * 100
    exigido_resto = pres_resto
    entrega_resto = real_mes * len(RESTO)
    cumpl_resto = _div(entrega_resto, exigido_resto) * 100
    st.caption(md(
        f"El compromiso de los doce meses suma **{cop(compromiso_anual, 0)}**. "
        f"Van {cop(real_ytd, 0)} y faltan **{cop(max(falta_anual, 0), 0)}**, que "
        f"al ritmo de {mes_es(CORTE)} son {dias_de_venta:.0f} días de venta. "
        f"Los cuatro meses que quedan piden {cop(exigido_resto, 0)} y el ritmo "
        f"actual entrega {cop(entrega_resto, 0)}: **{pct(cumpl_resto, 0)}**."))

    st.markdown(panel(
        "El año se cierra, pero el último trimestre no sobra",
        f"Al ritmo de {mes_es(CORTE)} el año termina en {cop(cierre, 0)}, "
        f"{pct(cumpl_cierre, 0)} del compromiso. Suena holgado y no lo es, por "
        f"una razón de calendario: el compromiso de septiembre a diciembre está "
        f"armado sobre el <b>mismo trimestre del año pasado, que es temporada "
        f"alta</b> — diciembre es el mes más grande del año en licores, y en "
        f"corporativo casi todo el año se juega ahí. Por eso los cuatro meses "
        f"que quedan piden {cop(exigido_resto, 0)} y el ritmo de hoy entrega "
        f"{pct(cumpl_resto, 0)} de eso, sin margen.<br><br>"
        f"La consecuencia operativa no es comercial, es de <b>inventario</b>: "
        f"lo que se venda en diciembre hay que haberlo comprado en octubre, y "
        f"una importación tarda del orden de sesenta días. La decisión de cerrar "
        f"el año no se toma en diciembre — se toma ahora, con la orden de compra.",
        "🏁", "azul" if cumpl_cierre >= 100 else "alerta"), unsafe_allow_html=True)

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── Las tres palancas ───────────────────────────────────────────────────
    va = v[v["mes"] == CORTE]
    base_cuentas = filtros.aplicar(b2b.cuentas(), col_mes=None)
    activas = int(va["cuenta_id"].nunique())
    dormidas = max(len(base_cuentas) - activas, 0)
    ticket = _div(va["neto"].sum(), va["entregas"].sum())
    frec = _div(va["entregas"].sum(), activas)
    por_cuenta = _div(va["neto"].sum(), activas)

    serie = v[v["mes"] >= INICIO_ANIO].groupby("mes")["cuenta_id"].nunique()
    pico = int(serie.max()) if len(serie) else activas
    mes_pico = str(serie.idxmax()) if len(serie) else CORTE
    objetivo = max(falta_anual / max(len(RESTO), 1), abs(deuda_mes))
    n_cuentas = objetivo / por_cuenta if por_cuenta else 0
    gana_ticket = real_mes * 0.10
    gana_frec = activas * ticket

    # Con la base casi toda comprando, «despertar dormidas» deja de ser una
    # opción real y hay que decirlo: mandar al equipo a reactivar tres cuentas
    # cuando la brecha vale cien millones es perder el trimestre.
    saturada = dormidas <= max(len(base_cuentas) * 0.15, 1)
    cuentas_txt = (
        f"Solo {dormidas} de {len(base_cuentas)} cuentas de la base no "
        f"compraron este mes: <b>la base está agotada</b>. Crecer en cuentas ya "
        f"no es reactivar, es abrir, y eso es otro trabajo y otro plazo."
        if saturada else
        f"Quedan {dormidas} cuentas en la base sin compra este mes: despertar "
        f"una cuenta conocida cuesta la mitad que abrir una nueva y entrega en "
        f"la mitad del tiempo.")

    st.markdown(panel(
        "La brecha se cierra de tres maneras y ninguna tarda lo mismo",
        f"Hacen falta <b>{cop(objetivo, 0)} al mes</b> para no depender del "
        f"último trimestre. Con {activas} cuentas activas, {cop(por_cuenta)} por "
        f"cuenta y {cop(ticket)} por entrega, la aritmética es ésta:<br><br>"
        f"<b>1. Más cuentas — {np.ceil(n_cuentas):.0f} cuentas nuevas.</b> "
        f"Es la palanca que sostuvo el año: las activas pasaron de "
        f"{int(serie.iloc[0]) if len(serie) else activas} en enero a {pico} en "
        f"{mes_es(mes_pico)}, y ahí se estancó — hoy son {activas}. "
        f"{cuentas_txt} <i>Madura en 60 a 90 días</i>: prospecto, primera compra "
        f"y recompra. Si la brecha es de este trimestre, llega tarde.<br>"
        f"<b>2. Más ticket — {cop(gana_ticket, 0)} con subir 10%.</b> Se cobra en "
        f"el <i>próximo pedido</i>: mezcla hacia referencias de mayor valor, "
        f"pedido mínimo, y menos descuento donde el margen lo aguante. Es la "
        f"única palanca que actúa este mes, y también la que tiene techo — no se "
        f"puede pedir dos trimestres seguidos.<br>"
        f"<b>3. Más frecuencia — {cop(gana_frec, 0)} con una entrega más por "
        f"cuenta.</b> Es la más rápida de todas y la única que <b>empeora el "
        f"negocio</b>: cada entrega cuesta casi lo mismo lleve cuatro botellas o "
        f"cuarenta, así que la venta sube y el margen servido baja. Hoy vamos en "
        f"{num(frec, 1)} entregas por cuenta al mes.<br><br>"
        f"<b>El orden correcto</b>: ticket ahora, para este trimestre; "
        f"prospección nueva ahora también, pero contándola para el primer "
        f"trimestre del año entrante, no para diciembre. Frecuencia solo donde "
        f"el margen después de servir lo permita — y eso se mira en Rentabilidad "
        f"por cuenta, no aquí.",
        "🔧", "alerta"), unsafe_allow_html=True)
