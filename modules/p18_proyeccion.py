"""Proyección: en qué va a terminar el año, y qué hace falta para que termine bien.

La proyección se arma con el método más simple que resiste ser explicado en una
reunión: **tendencia de los últimos doce meses × índice estacional del mes**,
calculado sobre el histórico real de KYVA. No hay red neuronal ni caja negra, y
es a propósito — Javier preguntó por el nivel de error y por alucinaciones. Un
pronóstico que no se puede auditar no se puede discutir, y uno que no se puede
discutir no se usa para decidir.

Lo que sí hace falta decir, y la pantalla lo dice: **el rango importa más que el
número.** Un pronóstico puntual invita a tratarlo como un dato; una banda
obliga a preguntarse qué pasa en el extremo malo, que es la conversación útil.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.formatters import *
from utils import datos

MESES_PROY = 4          # septiembre a diciembre de 2026


def _proyectar(serie: pd.Series):
    """Tendencia reciente × estacionalidad histórica. Devuelve (centro, banda).

    La estacionalidad se saca de los años COMPLETOS anteriores, nunca del año
    en curso: incluir 2026 haría que el pico de diciembre se calcule con un
    diciembre que todavía no ocurrió, y el pronóstico se justificaría a sí mismo.
    """
    s = serie.copy()
    s.index = pd.to_datetime(s.index + "-01")
    # El índice hereda el nombre «mes» de la columna original, y más abajo hace
    # falta una columna con el número del mes. Sin borrar el nombre, pandas ve
    # «mes» como índice y como columna a la vez y se niega a agrupar.
    s.index.name = None
    anios_completos = s[s.index.year < s.index.year.max()]

    # Índice estacional: cuánto pesa cada mes contra el promedio de su año.
    if len(anios_completos) >= 12:
        tmp = anios_completos.to_frame("v")
        tmp["anio"], tmp["num_mes"] = tmp.index.year, tmp.index.month
        tmp["idx"] = tmp["v"] / tmp.groupby("anio")["v"].transform("mean")
        estacional = tmp.groupby("num_mes")["idx"].mean()
    else:
        estacional = pd.Series(1.0, index=range(1, 13))

    # Nivel: los últimos 12 meses, desestacionalizados.
    ult = s.tail(12)
    desest = ult / ult.index.month.map(estacional).values
    nivel = float(desest.mean())

    # Tendencia: pendiente de los desestacionalizados, amortiguada. Sin
    # amortiguar, una pendiente de doce meses se extrapola a cuatro meses y
    # produce números que nadie va a creer.
    x = np.arange(len(desest))
    pend = float(np.polyfit(x, desest.values, 1)[0]) * 0.55

    # Error del método contra su propio histórico: es la banda honesta.
    ajuste = (nivel + pend * (x - x.mean())) * ult.index.month.map(estacional).values
    err = float(np.abs(ajuste - ult.values).mean() / max(ult.mean(), 1))

    futuro = pd.date_range(s.index[-1] + pd.offsets.MonthBegin(1),
                           periods=MESES_PROY, freq="MS")
    centro = pd.Series(
        [(nivel + pend * (len(desest) + i)) * estacional.get(f.month, 1.0)
         for i, f in enumerate(futuro)], index=futuro).clip(lower=0)
    return centro, err, estacional


def render():
    st.markdown(HEADER_CSS, unsafe_allow_html=True)
    st.markdown(encabezado(
        "Proyección de cierre",
        "Septiembre a diciembre de 2026, por canal · tendencia × estacionalidad del histórico real",
        "¿Qué viene?"), unsafe_allow_html=True)

    fin = datos.finanzas().copy()
    fin = fin.sort_values("mes")
    serie = fin.set_index("mes")["ingresos"]

    centro, err, estacional = _proyectar(serie)
    bajo, alto = centro * (1 - err), centro * (1 + err)

    ytd = float(serie[serie.index >= "2026-01"].sum())
    cierre = ytd + float(centro.sum())
    anio_ant = float(serie[(serie.index >= "2025-01") & (serie.index <= "2025-12")].sum())
    crec = (cierre / anio_ant - 1) * 100 if anio_ant else 0
    pico = float(centro[centro.index.month.isin([11, 12])].sum())

    k = st.columns(4, gap="small")
    k[0].markdown(kpi(
        "Cierre proyectado 2026", cop(cierre, 0),
        f"{signo(crec)} contra 2025", crec > 0, "🎯",
        "Lo que va del año más la proyección de los cuatro meses que faltan.",
        f"Rango: {cop(ytd + bajo.sum(), 0)} a {cop(ytd + alto.sum(), 0)}"),
        unsafe_allow_html=True)
    k[1].markdown(kpi(
        "Noviembre + diciembre", cop(pico, 0),
        f"{pct(pico / max(cierre, 1) * 100, 0)} de todo el año", True, "🎄",
        "Dos meses que pesan como un trimestre. Lo que se venda ahí se compra ahora."),
        unsafe_allow_html=True)
    k[2].markdown(kpi(
        "Margen de error del método", f"±{err*100:.1f}%",
        "medido contra los últimos 12 meses", err < 0.12, "📐",
        "No es una promesa de precisión: es cuánto se equivocó este mismo cálculo "
        "cuando se le pidió reproducir meses que ya pasaron."),
        unsafe_allow_html=True)
    dic = float(estacional.get(12, 1))
    k[3].markdown(kpi(
        "Peso de diciembre", f"{dic:.2f}×",
        "contra un mes promedio", True, "📈",
        "Índice estacional calculado con los años completos anteriores, nunca con 2026."),
        unsafe_allow_html=True)

    st.markdown(espacio(18), unsafe_allow_html=True)

    # ── La curva ────────────────────────────────────────────────────────────
    st.markdown('<div class="ky-sub">Histórico y proyección</div>', unsafe_allow_html=True)
    hist = serie.copy()
    hist.index = pd.to_datetime(hist.index + "-01")
    hist = hist.tail(24)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(alto.index) + list(bajo.index[::-1]),
        y=list(alto.values) + list(bajo.values[::-1]),
        fill="toself", fillcolor="rgba(206,98,100,.13)", line=dict(width=0),
        hoverinfo="skip", name="Rango"))
    fig.add_trace(go.Scatter(
        x=hist.index, y=hist.values, name="Real", mode="lines+markers",
        line=dict(color=PRIMARIO, width=2.5), marker=dict(size=5),
        hovertemplate="%{x|%b %Y}: %{y:,.0f}<extra></extra>"))
    puente = pd.concat([hist.tail(1), centro])
    fig.add_trace(go.Scatter(
        x=puente.index, y=puente.values, name="Proyección", mode="lines+markers",
        line=dict(color=ACENTO, width=2.5, dash="dot"), marker=dict(size=6),
        hovertemplate="%{x|%b %Y}: %{y:,.0f}<extra></extra>"))
    fig.add_vline(x=hist.index[-1], line_width=1, line_dash="dot", line_color=CLARO)
    st.plotly_chart(light(fig, 380, moneda=True), use_container_width=True)
    st.caption(
        f"La banda es el error propio del método (±{err*100:.1f}%), no un intervalo "
        f"de confianza estadístico. Se calcula pidiéndole al mismo cálculo que "
        f"reproduzca los doce meses que ya pasaron y midiendo cuánto se equivoca.")

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── Por canal ───────────────────────────────────────────────────────────
    st.markdown('<div class="ky-sub">De dónde viene ese cierre</div>',
                unsafe_allow_html=True)
    filas = []
    for canal, col in datos.COL_CANAL.items():
        c, e, _ = _proyectar(fin.set_index("mes")[col])
        ytd_c = float(fin.loc[fin["mes"] >= "2026-01", col].sum())
        ant_c = float(fin.loc[(fin["mes"] >= "2025-01") & (fin["mes"] <= "2025-12"), col].sum())
        filas.append({
            "Canal": canal,
            "Lo que va de 2026": ytd_c,
            "Sep–dic proyectado": float(c.sum()),
            "Cierre 2026": ytd_c + float(c.sum()),
            "vs 2025": (ytd_c + float(c.sum())) / ant_c - 1 if ant_c else np.nan,
            "± del método": e,
        })
    d = pd.DataFrame(filas).sort_values("Cierre 2026", ascending=False)
    muestra = d.copy()
    for c in ("Lo que va de 2026", "Sep–dic proyectado", "Cierre 2026"):
        muestra[c] = muestra[c].map(lambda v: cop(v, 0))
    muestra["vs 2025"] = d["vs 2025"].map(lambda v: signo(v * 100) if pd.notna(v) else "—")
    muestra["± del método"] = d["± del método"].map(lambda v: f"±{v*100:.0f}%")
    st.dataframe(muestra, hide_index=True, width="stretch")

    peor = d.sort_values("± del método", ascending=False).iloc[0]
    st.caption(
        f"**{peor['Canal']}** es el canal menos predecible (±{peor['± del método']*100:.0f}%). "
        f"Tiene sentido: es el que menos historia tiene y el que más depende de pocos "
        f"clientes grandes. Su proyección se usa para planear, no para comprometer.")

    st.markdown(espacio(14), unsafe_allow_html=True)

    # ── El puente con la compra ─────────────────────────────────────────────
    r = datos.resumen_operacion()
    st.markdown(panel(
        "Lo que esta proyección obliga a hacer hoy",
        f"Si noviembre y diciembre van a valer <b>{cop(pico, 0)}</b>, la mercancía "
        f"para venderlos hay que tenerla comprada ya: el módulo de reposición "
        f"calcula <b>{cop(r['compra_diciembre'], 0)}</b> de compra neta, y "
        f"<b>{r['urge_semana']} referencias</b> cuyo plazo de importación deja de "
        f"caber esta semana. Un pronóstico que no termina en una orden de compra "
        f"es un informe.",
        "🔗", "azul"), unsafe_allow_html=True)
