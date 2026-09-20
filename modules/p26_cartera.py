"""Cartera: la plata que ya vendimos y todavía no es nuestra.

Para una distribuidora de licores la cartera no es un tema contable: es el
negocio. Se le compra a la marca de contado o a 30 días y se le vende al bar a
15, 30 o 45 según el canal, así que **cada peso que crece la venta amarra
capital**. Crecer sin mirar esto es exactamente así como se queda sin caja una
empresa rentable.

La versión anterior de esta pantalla estimaba la cartera multiplicando la venta
del mes por el plazo pactado. Un revisor del oficio la destrozó con una frase
que hay que dejar escrita:

    «Eso no es cartera, es una estimación teórica. El plazo pactado y el real se
    llevan tres semanas.»

Tenía razón, y el dato lo confirma: las discotecas firman 15 días y pagan cerca
de 33. Un presupuesto de caja armado con el plazo pactado no se equivoca un
poco — se equivoca medio mes entero, todos los meses. Por eso aquí no hay una
sola cifra estimada: cada peso sale de una factura con número, fecha de emisión,
fecha de vencimiento y fecha de pago cuando la hubo.

Cuatro cosas que esta pantalla hace y un reporte de edades no:

  · **Separa lo que me deben de lo que espero cobrar.** El saldo ponderado por
    la probabilidad de cobro de cada tramo cambia la conversación: no «me deben
    40» sino «de esos 40 espero cobrar 31».
  · **Mide el atraso real contra el pactado, canal por canal.** Ahí está el
    hallazgo, y es un hallazgo de condiciones comerciales, no de cobranza.
  · **Cruza riesgo con valor.** Cortarle el crédito a la cuenta que más margen
    deja es una decisión distinta que cortárselo a una marginal, aunque las dos
    deban lo mismo.
  · **Baja hasta la factura.** Si no se puede abrir una cuenta y ver sus
    facturas una por una, nadie puede pelear con el número y entonces el número
    no sirve para decidir nada.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.formatters import *
from utils import b2b, estado, filtros, gerencia
from utils.datos import CORTE

# Los dos números de la regla NO se eligieron aquí: son los que ya están
# escritos en AUT-06 («escala al comercial a los 5 días · bloquea nuevos pedidos
# a crédito a los 15»). Si esta pantalla dijera otra cosa, el panel se
# contradiría con su propio módulo de automatizaciones.
#
# Y son razonables por su cuenta: a los 15 la probabilidad de cobro empieza a
# caer rápido (del 95% del primer tramo al 82% del segundo) y todavía queda
# margen para arreglarlo con una llamada. Con 30 se llega tarde; con 8 se
# bloquea a un cliente bueno que se demoró por un puente festivo.
BLOQUEO_DIAS = 15
AVISO_DIAS = 5                     # el vendedor se entera antes que el cliente


def _ficha(c, plazo, atraso) -> str:
    """La cuenta entera en una tarjeta: qué debe, qué firmó y cómo paga."""
    color = ACENTO if c["vencido"] > 0 else "#2f7a48"
    sobre = c["saldo"] - c["cupo_credito"]
    cupo_txt = (f'<span style="color:{ACENTO};font-weight:700">'
                f'{cop(sobre, 0)} por encima del cupo</span>' if sobre > 0
                else f'usa {pct(c["saldo"] / max(c["cupo_credito"], 1) * 100, 0)} del cupo')
    return f"""
    <div style="border:1px solid {PALIDO};border-top:4px solid {color};
         border-radius:6px;padding:18px 22px;background:#fff;margin-bottom:14px">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:20px">
        <div>
          <div style="font-size:9.5px;font-weight:800;letter-spacing:.14em;
               text-transform:uppercase;color:{CLARO}">
            {c['canal']} · {c['ciudad']}</div>
          <div style="font-family:'DM Serif Display',Georgia,serif;font-size:27px;
               color:{TINTA};line-height:1.15;margin:2px 0 4px">{c['nombre']}</div>
          <div style="font-size:11.5px;color:{CLARO}">
            Vendedor: <b style="color:{TINTA}">{c['vendedor']}</b> &nbsp;·&nbsp;
            Firmó {int(plazo)} días, paga en {atraso:.0f} &nbsp;·&nbsp;
            Cupo {cop(c['cupo_credito'], 0)}, {cupo_txt}</div>
        </div>
        <div style="text-align:right;white-space:nowrap">
          <div style="font-size:9.5px;font-weight:800;letter-spacing:.1em;
               text-transform:uppercase;color:{CLARO}">Saldo abierto</div>
          <div style="font-size:30px;font-weight:800;color:{color};line-height:1.1">
            {cop(c['saldo'], 0)}</div>
          <div style="font-size:12px;color:{CLARO}">
            {cop(c['vencido'], 0)} vencido · {int(c['facturas'])} facturas abiertas
            de {int(c['emitidas'])} emitidas</div>
        </div>
      </div>
    </div>"""


def render():
    st.markdown(HEADER_CSS, unsafe_allow_html=True)
    st.markdown(encabezado(
        "Cartera",
        "Factura por factura: lo que está en la calle, lo que ya se venció y lo que "
        "de verdad se va a cobrar",
        "¿Dónde está la caja?"), unsafe_allow_html=True)
    filtros.encabezado_filtro()

    f = gerencia.facturas()

    # El filtro de periodo NO se aplica al saldo abierto, a propósito: la cartera
    # es una foto al corte, y una factura de abril que sigue abierta es
    # justamente el problema que hay que ver. Filtrar por mes de emisión la
    # escondería. Ciudad, canal y vendedor sí se aplican.
    fac = filtros.aplicar(f, col_mes=None)
    if fac.empty:
        st.info("No hay facturas con los filtros puestos. Quítelos en la barra lateral.")
        return

    ab = fac[~fac["pagada"]]
    total = float(ab["saldo"].sum())
    esperado = float(ab["esperado"].sum())
    vencido = float(ab.loc[ab["dias_vencida"] > 0, "saldo"].sum())
    pagadas = fac[fac["pagada"]]
    atraso_medio = float(pagadas["dias_atraso_real"].mean()) if len(pagadas) else 0.0
    plazo_medio = float(pagadas["plazo"].mean()) if len(pagadas) else 0.0
    puntual = float((pagadas["dias_atraso_real"] <= 0).mean() * 100) if len(pagadas) else 0.0

    k = st.columns(4, gap="small")
    k[0].markdown(kpi(
        "En la calle", cop(total, 0),
        f"{int(len(ab))} facturas abiertas de {int(ab['cuenta_id'].nunique())} cuentas",
        True, "🏦",
        "Facturado y no cobrado al corte. Sale de las facturas, no del plazo pactado."),
        unsafe_allow_html=True)
    k[1].markdown(kpi(
        "Ya vencido", cop(vencido, 0),
        f"{pct(vencido / max(total, 1) * 100)} de lo que está en la calle",
        vencido / max(total, 1) < 0.25, "⏰",
        "Pasó la fecha de vencimiento y sigue sin pagarse.",
        "Sano en distribución: por debajo del 25%"), unsafe_allow_html=True)
    k[2].markdown(kpi(
        "Lo que espero cobrar", cop(esperado, 0),
        f"{cop(total - esperado, 0)} en riesgo de no entrar", False, "📉",
        "El saldo ponderado por la probabilidad de cobro de cada tramo de edad.",
        "Un peso a más de 90 días vale 28 centavos"), unsafe_allow_html=True)
    k[3].markdown(kpi(
        "Atraso real", f"{atraso_medio:.0f} días",
        f"sobre un plazo pactado de {plazo_medio:.0f}", atraso_medio < 5, "📅",
        f"Solo {puntual:.0f} de cada 100 facturas se pagan el día que dice el "
        f"acuerdo. El presupuesto de caja se arma con el número de la izquierda.",
        "Este es el número que se le pasa a tesorería"), unsafe_allow_html=True)

    st.markdown(espacio(18), unsafe_allow_html=True)

    # ── Lo pactado contra lo real ───────────────────────────────────────────
    st.markdown('<div class="ky-sub">Lo que firmaron y lo que pagan</div>',
                unsafe_allow_html=True)
    pg = filtros.aplicar(fac[fac["pagada"]])   # aquí el periodo sí manda: es historia
    if len(pg):
        cn = pg.groupby("canal").agg(
            plazo=("plazo", "mean"), atraso=("dias_atraso_real", "mean"),
            facturas=("factura", "size"),
            puntual=("dias_atraso_real", lambda s: float((s <= 0).mean() * 100))).reset_index()
        cn["real"] = cn["plazo"] + cn["atraso"]
        cn = cn.sort_values("atraso")

        xs, ys = [], []
        for _, r in cn.iterrows():
            xs += [r["plazo"], r["real"], None]
            ys += [r["canal"], r["canal"], None]

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", showlegend=False,
                                 line=dict(color=PALIDO, width=7), hoverinfo="skip"))
        fig.add_trace(go.Scatter(
            x=cn["plazo"], y=cn["canal"], mode="markers", name="Plazo pactado",
            marker=dict(size=15, color=CLARO, line=dict(width=1.5, color="#fff")),
            hovertemplate="%{y}<br>Pactado: %{x:.0f} días<extra></extra>"))
        fig.add_trace(go.Scatter(
            x=cn["real"], y=cn["canal"], mode="markers+text", name="Día en que pagan",
            marker=dict(size=17, color=ACENTO, line=dict(width=1.5, color="#fff")),
            text=[f"  +{a:.0f} días" for a in cn["atraso"]], textposition="middle right",
            textfont=dict(size=11, color=TINTA),
            customdata=np.stack([cn["atraso"], cn["puntual"], cn["facturas"]], -1),
            hovertemplate="%{y}<br>Pagan en %{x:.0f} días"
                          "<br>Se atrasan %{customdata[0]:.0f} días"
                          "<br>%{customdata[1]:.0f}% paga a tiempo"
                          "<br>%{customdata[2]:.0f} facturas<extra></extra>"))
        fig.update_xaxes(title="Días desde la emisión hasta el pago",
                         range=[0, float(cn["real"].max()) * 1.28])
        fig = light(fig, 300)
        fig.update_layout(hovermode="closest")
        st.plotly_chart(fig, use_container_width=True)

        peor = cn.iloc[-1]
        st.markdown(panel(
            "El hallazgo no es de cobranza: es de condiciones comerciales",
            f"<b>{peor['canal']}</b> firma a <b>{peor['plazo']:.0f} días</b> y paga a "
            f"<b>{peor['real']:.0f}</b>. Son {peor['atraso']:.0f} días de diferencia "
            f"sobre {int(peor['facturas'])} facturas, y solo el "
            f"{peor['puntual']:.0f}% entra en la fecha acordada.<br><br>"
            f"Eso no se arregla llamando más. Un canal de caja diaria y "
            f"administración informal no paga el día 15 porque no hay nadie el día "
            f"15 haciendo pagos; paga cuando pasa el proveedor. Hay dos salidas "
            f"reales: <b>pactar el plazo que de verdad se cumple</b> y cobrarlo en "
            f"el precio, o <b>cobrar en la entrega</b> — que es lo que ya hace quien "
            f"le vende hielo y cerveza a ese mismo bar. Seguir presupuestando caja "
            f"a {peor['plazo']:.0f} días es presupuestar mal a propósito.",
            "🔍", "alerta"), unsafe_allow_html=True)

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── La pirámide de edades ───────────────────────────────────────────────
    st.markdown('<div class="ky-sub">Cómo envejece la cartera</div>',
                unsafe_allow_html=True)
    pt = ab.groupby("tramo").agg(
        saldo=("saldo", "sum"), esperado=("esperado", "sum"),
        facturas=("factura", "size")).reindex(gerencia.TRAMOS).fillna(0).reset_index()
    pt["perdida"] = pt["saldo"] - pt["esperado"]

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=pt["tramo"], y=pt["esperado"], name="Lo que se espera cobrar",
        marker_color=[gerencia.COLOR_TRAMO.get(t, PRIMARIO) for t in pt["tramo"]],
        customdata=pt["facturas"],
        hovertemplate="%{x}<br>Esperado: %{y:,.0f}"
                      "<br>%{customdata:.0f} facturas<extra></extra>"))
    fig2.add_trace(go.Bar(
        x=pt["tramo"], y=pt["perdida"], name="Lo que estadísticamente no entra",
        marker_color=PALIDO,
        hovertemplate="%{x}<br>En riesgo: %{y:,.0f}<extra></extra>"))
    fig2.update_layout(barmode="stack")
    st.plotly_chart(light(fig2, 320, moneda=True), use_container_width=True)

    vacios = [t for t in gerencia.TRAMOS if float(pt.loc[pt["tramo"] == t, "saldo"].sum()) == 0]
    cola = (f"Hoy no hay un solo peso en **{'** ni **'.join(vacios)}**: la cartera "
            f"está sucia, no perdida — y esa es la diferencia entre gestionarla y "
            f"provisionarla. " if vacios else "")
    st.caption(
        f"La parte gris es lo que estadísticamente no se cobra. **No es una "
        f"provisión contable: es el argumento para llamar hoy.** Cada semana que un "
        f"saldo cruza al siguiente tramo, una parte se vuelve gris y no vuelve. "
        f"{cola}El trabajo es que siga así.")

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── Riesgo contra valor ─────────────────────────────────────────────────
    st.markdown('<div class="ky-sub">A quién apretar y a quién cuidar</div>',
                unsafe_allow_html=True)
    # Se agrupa sobre TODAS las facturas, no solo las abiertas: una factura
    # pagada trae saldo 0 y no ensucia ninguna suma, pero deja a la cuenta en la
    # lista. Si se agrupa solo lo abierto, la cuenta que acaba de pagar
    # desaparece del panel justo el día en que uno quiere ver cómo pagó.
    base = fac.assign(venc=np.where(fac["dias_vencida"] > 0, fac["saldo"], 0),
                      abierta=(~fac["pagada"]).astype(int))
    cta = base.groupby(["cuenta_id", "nombre", "canal", "ciudad", "vendedor"]).agg(
        saldo=("saldo", "sum"), esperado=("esperado", "sum"),
        vencido=("venc", "sum"), facturas=("abierta", "sum"),
        emitidas=("factura", "size"),
        dias_max=("dias_vencida", "max")).reset_index()
    # El margen y el cupo no están en la factura: viven en la ficha de la cuenta.
    # Sin ellos la matriz no se puede dibujar, porque el eje que decide no es el
    # saldo — es lo que se pierde si se corta el despacho.
    ficha = b2b.rentabilidad()[["cuenta_id", "servido", "cupo_credito", "plazo_pago"]]
    cta = cta.merge(ficha, on="cuenta_id", how="left")
    for c in ("servido", "cupo_credito", "plazo_pago"):
        cta[c] = cta[c].fillna(0)
    cta["riesgo_pct"] = (1 - cta["esperado"] / cta["saldo"].replace(0, np.nan)) * 100
    cta["riesgo_pct"] = cta["riesgo_pct"].fillna(0)
    cta["en_riesgo"] = cta["saldo"] - cta["esperado"]

    mapa = cta[cta["saldo"] > 0]      # quien no debe nada no tiene lugar en la matriz
    fig3 = go.Figure()
    for canal, color in b2b.COLOR_CANAL.items():
        d = mapa[mapa["canal"] == canal]
        if d.empty:
            continue
        fig3.add_trace(go.Scatter(
            x=d["riesgo_pct"], y=d["servido"], mode="markers", name=canal,
            marker=dict(size=np.clip(d["saldo"] / 8e5, 9, 42), color=color,
                        opacity=.78, line=dict(width=1, color="#fff")),
            customdata=np.stack([d["nombre"], d["saldo"], d["vencido"],
                                 d["facturas"], d["dias_max"]], -1),
            hovertemplate="<b>%{customdata[0]}</b><br>Saldo: %{customdata[1]:,.0f}"
                          "<br>Vencido: %{customdata[2]:,.0f} en %{customdata[3]:.0f} facturas"
                          "<br>La más vieja lleva %{customdata[4]:.0f} días"
                          "<br>Riesgo de no cobrar: %{x:.1f}%"
                          "<br>Margen del trimestre: %{y:,.0f}<extra></extra>"))
    if len(mapa):
        fig3.add_vline(x=float(mapa["riesgo_pct"].median()), line_dash="dot", line_color=CLARO)
        fig3.add_hline(y=float(mapa["servido"].median()), line_dash="dot", line_color=CLARO)
    fig3.update_xaxes(title="Riesgo de no cobrar (%)")
    fig3.update_yaxes(title="Margen que deja en el trimestre")
    fig3 = light(fig3, 400)
    fig3.update_layout(hovermode="closest")
    st.plotly_chart(fig3, use_container_width=True)
    st.caption(
        "El tamaño del círculo es el saldo abierto. **Arriba a la derecha** están "
        "las que hay que cuidar y cobrar a la vez: dejan plata y se están "
        "atrasando; ahí va el gerente, no el mensaje de texto. **Abajo a la "
        "derecha** son las que no duelen — mucho riesgo, poco margen; ahí se corta "
        "el crédito sin pensarlo dos veces. Aplicarles la misma política a las dos, "
        "que es lo que hace una cartera sin datos, cuesta justamente las buenas.")

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── A quién llamar hoy ──────────────────────────────────────────────────
    st.markdown('<div class="ky-sub">A quién llamar hoy</div>', unsafe_allow_html=True)
    llamar = cta[cta["vencido"] > 0].nlargest(12, "en_riesgo").copy()
    if llamar.empty:
        st.success("No hay nada vencido con estos filtros. La lista de llamadas está vacía.")
    else:
        llamar["accion"] = np.where(
            llamar["dias_max"] >= BLOQUEO_DIAS,
            "Bloquear despacho y llamar al dueño",
            np.where(llamar["dias_max"] >= AVISO_DIAS,
                     "Llamar hoy: el bloqueo entra en " +
                     (BLOQUEO_DIAS - llamar["dias_max"]).astype(int).astype(str) + " días",
                     "Recordatorio por WhatsApp con el soporte de la factura"))
        t = llamar[["nombre", "canal", "ciudad", "vendedor", "facturas", "dias_max",
                    "vencido", "en_riesgo", "accion"]].copy()
        t["facturas"] = t["facturas"].astype(int)
        t["dias_max"] = t["dias_max"].astype(int)
        for c in ("vencido", "en_riesgo"):
            t[c] = llamar[c].map(lambda x: cop(x, 0))
        t.columns = ["Cuenta", "Canal", "Ciudad", "Vendedor", "Facturas abiertas",
                     "Días de la más vieja", "Vencido", "Plata en riesgo", "Qué hacer"]
        st.dataframe(t, hide_index=True, width="stretch")
        st.caption(
            "Ordenada por **plata en riesgo**, no por saldo: una cuenta que debe más "
            "pero está corriente no es urgente, y una que debe menos a 45 días sí. "
            "El vendedor que aparece es el que llama — no el de cartera, porque el "
            "cliente le contesta a quien le vende.")

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── Drill-down: la factura, una por una ─────────────────────────────────
    st.markdown('<div class="ky-sub">Abrir una cuenta, factura por factura</div>',
                unsafe_allow_html=True)
    orden = cta.sort_values("en_riesgo", ascending=False).reset_index(drop=True)
    etiquetas = [f"{x['nombre']} — {cop(x['saldo'], 0)} abiertos · {x['canal']}"
                 for _, x in orden.iterrows()]
    elegida = st.selectbox("Cuenta", etiquetas, key="cart_cuenta")
    c = orden.iloc[etiquetas.index(elegida)]

    hist = fac[(fac["cuenta_id"] == c["cuenta_id"]) & fac["pagada"]]
    atraso_cta = float(hist["dias_atraso_real"].mean()) if len(hist) else 0.0
    plazo_cta = float(c["plazo_pago"]) or float(
        fac.loc[fac["cuenta_id"] == c["cuenta_id"], "plazo"].median())
    st.markdown(_ficha(c, plazo_cta, plazo_cta + atraso_cta), unsafe_allow_html=True)

    det = fac[fac["cuenta_id"] == c["cuenta_id"]].sort_values("emitida", ascending=False)
    d = pd.DataFrame({
        "Factura": det["factura"],
        "Emitida": det["emitida"].dt.strftime("%d/%m/%Y"),
        "Vence": det["vence"].dt.strftime("%d/%m/%Y"),
        "Plazo": det["plazo"].astype(int).astype(str) + " d",
        "Valor": det["valor"].map(lambda x: cop(x, 0)),
        "Estado": np.where(det["pagada"],
                           "Pagada el " + det["pagada_el"].astype(str),
                           "ABIERTA"),
        "Atraso al pagar": np.where(det["pagada"],
                                    det["dias_atraso_real"].astype(int).astype(str) + " d",
                                    "—"),
        "Días vencida": np.where(det["dias_vencida"] > 0,
                                 det["dias_vencida"].astype(int).astype(str) + " d", "—"),
        "Tramo": det["tramo"],
        "Saldo": det["saldo"].map(lambda x: cop(x, 0) if x > 0 else "—"),
    })
    st.dataframe(d, hide_index=True, width="stretch", height=330)
    st.caption(
        f"{len(det)} facturas de **{c['nombre']}** en el histórico cargado: "
        f"{int(det['pagada'].sum())} pagadas y {int((~det['pagada']).sum())} abiertas. "
        f"Esta es la tabla con la que se pelea el número por teléfono — con fecha, "
        f"con consecutivo y con días. Sin ella la discusión es opinión contra opinión.")

    # La gestión queda registrada fuera del navegador: si se refresca la página,
    # el compromiso sigue ahí, con dueño y fecha. Un botón que solo pinta un
    # mensaje verde y se borra al recargar es exactamente lo que hace que nadie
    # vuelva a abrir estas herramientas.
    st.markdown(espacio(10), unsafe_allow_html=True)
    g = st.columns([3, 2], gap="large")
    with g[0]:
        if st.button(f"Asignar el cobro de {c['nombre']} a {c['vendedor']}",
                     key="cart_gestion", type="primary"):
            estado.nuevo_compromiso(
                f"Cobrar {cop(c['saldo'], 0)} a {c['nombre']} "
                f"({int(c['facturas'])} facturas, {int(c['dias_max'])} días la más vieja)",
                c["vendedor"], dias=7, valor=float(c["saldo"]), origen="Cartera")
            st.success(f"Compromiso abierto a nombre de {c['vendedor']}, vence en 7 días. "
                       f"Queda en el módulo de compromisos.")
    with g[1]:
        abiertos = [v for v in estado.compromisos().values()
                    if v.get("origen") == "Cartera" and v.get("estado") == "En curso"]
        if abiertos:
            st.markdown(
                f'<div style="font-size:12px;color:{CLARO};padding-top:8px">'
                f'{len(abiertos)} cobros asignados y sin cerrar · '
                f'{cop(sum(v.get("valor", 0) for v in abiertos), 0)}</div>',
                unsafe_allow_html=True)

    st.markdown(espacio(14), unsafe_allow_html=True)

    # ── La regla ────────────────────────────────────────────────────────────
    bloqueo = ab[ab["dias_vencida"] >= BLOQUEO_DIAS]
    aviso = ab[(ab["dias_vencida"] >= AVISO_DIAS) & (ab["dias_vencida"] < BLOQUEO_DIAS)]
    st.markdown(panel(
        "La regla que evita la conversación incómoda",
        f"Bloquear el despacho automáticamente a los <b>{BLOQUEO_DIAS} días de "
        f"vencido</b>, avisando al vendedor <b>{BLOQUEO_DIAS - AVISO_DIAS} días "
        f"antes</b>. Suena duro y es lo contrario: cuando el bloqueo es una regla "
        f"del sistema y no la decisión de una persona, <b>el vendedor deja de ser "
        f"el malo</b> y el cliente deja de negociarlo cada vez. Nadie discute con "
        f"una fecha.<br><br>"
        f"Hoy, con los filtros puestos: <b>{len(bloqueo)} facturas</b> por "
        f"{cop(float(bloqueo['saldo'].sum()), 0)} ya cruzaron el umbral y deberían "
        f"estar bloqueadas; otras <b>{len(aviso)}</b> entran en la ventana de aviso "
        f"esta semana. Ese segundo grupo es el que importa: ahí todavía alcanza una "
        f"llamada y no se pierde ni el despacho ni el cliente.<br><br>"
        f"Es el flujo <b>AUT-06</b> del módulo de automatizaciones, y es el único de "
        f"cartera que no necesita que nadie apruebe nada — porque no decide, "
        f"solo aplica lo que ya está firmado.",
        "📏", "azul"), unsafe_allow_html=True)
