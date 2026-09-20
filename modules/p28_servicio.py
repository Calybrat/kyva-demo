"""Lo que no se vendió: quiebres, fill rate y devoluciones.

Todo el panel mide lo que se facturó. Esta pantalla mide lo contrario, que es
donde está la plata que nadie reclama porque nadie la ve: **el martes en que el
bar pidió doce botellas de aguardiente, salieron cuatro, y las otras ocho se
las compró al distribuidor de al lado**.

Esa venta no aparece en ningún informe. No hay factura, no hay devolución, no
hay reclamo. El pedido se despachó «bien» —incompleto, pero despachado— y el
sistema lo registra como una entrega más. El único rastro queda en la línea del
pedido que se cerró con menos unidades de las pedidas, y ese dato no lo mira
nadie porque no cuadra con nada de la contabilidad.

Tres cosas que esta pantalla hace y que un informe de ventas no puede hacer:

**1. Separa el motivo, porque cada motivo es de un área distinta.** «Sin stock
en bodega» es un problema de compras: no se compró suficiente. «Comprometido en
otro pedido» es de asignación: la mercancía existía y se prometió dos veces.
«Error de inventario» es de bodega: el sistema decía que había y no había.
Sumarlos en un solo número de venta perdida hace imposible actuar, porque el
número no tiene dueño.

**2. Separa la devolución por responsable.** Una avería en transporte, un
producto vencido y un «me equivoqué al pedir» son tres problemas de tres áreas.
En el ERP los tres son una nota crédito.

**3. Pone precio al daño que no se ve.** Una cuenta a la que se le falla dos
veces en la misma categoría deja de pedirla: no reclama, simplemente la compra
en otro lado y la venta se va sin ruido. Eso vale más que el pedido fallido y
no está en ningún estado de resultados.

La referencia del sector para un distribuidor de licores con bodega propia es
un fill rate de 95-98%. Por debajo de 95% se pierden cuentas; por encima de 98%
casi siempre se está pagando con sobrestock —que es la misma plata, quieta en
la bodega y venciéndose.

**Esa referencia cuenta líneas, no pesos, y las dos cifras no dicen lo mismo.**
Un fill rate de 98% por líneas convive con un 92% por valor, porque la línea
que falla no es la pequeña: es el pedido grande. La pantalla muestra las dos
juntas a propósito — presentar sola la de líneas es la versión favorecedora, y
un COO hace esa división de cabeza en el primer minuto de la demo.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.formatters import *
from utils import gerencia, b2b, filtros

# El registro de líneas incompletas arranca en marzo de 2026. Antes de esa
# fecha el ERP cerraba el pedido con lo despachado y no guardaba lo pedido, así
# que un fill rate anterior sería inventado. Si el filtro pide 12 meses, la
# ventana de esta pantalla se recorta igual hasta aquí.
QUIEBRES_DESDE = "2026-03"

# Las devoluciones sí tienen registro desde enero. La ventana de devoluciones es
# distinta de la de quiebres y por eso se calcula aparte: mezclarlas daba un
# ratio de devoluciones sobre una base de seis meses y un numerador de ocho.
DEVOLUCIONES_DESDE = "2026-01"

# Un pedido a un bar lleva del orden de once referencias distintas. Es el
# denominador del fill rate y es la constante más delicada del módulo: la
# tabla de quiebres SOLO guarda las líneas que fallaron, y dividir entre ellas
# daba un fill rate de 35%, imposible para un negocio que sigue vendiendo.
LINEAS_POR_ENTREGA = 11

# Sano según el sector. La franja, no el punto: el 100% también es un problema.
FILL_SANO = (95.0, 98.0)

# Cada motivo de devolución también tiene un dueño, y son CINCO, no cuatro. El
# quinto —«no rotó en el punto»— es el que más incomoda porque no es un error
# de despacho: es mercancía que el vendedor colocó y el bar no vendió. Sin él,
# el panel acusaba a Comercial por una cifra de la que solo explicaba la mitad.
DUENO_DEVOLUCION = {
    "Avería en transporte": (
        "Logística", "Se arregla con estiba y ruta, no hablando con el cliente"),
    "Producto vencido": (
        "Compras", "No es una devolución: es un error de compra que se "
        "descubrió seis meses tarde en la nevera del bar"),
    "No rotó en el punto": (
        "Comercial", "No se despachó mal: se colocó de más. El bar no lo "
        "vendió y lo devolvió — se corrige surtiendo distinto, no despachando "
        "distinto"),
    "Pedido equivocado": (
        "Comercial", "Es del vendedor y se corrige en el momento de tomar el "
        "pedido"),
    "Diferencia de precio": (
        "Administración", "Ni siquiera es un problema de producto: es lista de "
        "precios contra lo que el vendedor prometió"),
}

# Cada motivo de quiebre tiene un dueño. Sin esta tabla, la venta perdida es
# un número que se comenta en comité y del que no sale ninguna tarea.
DUENO_QUIEBRE = {
    "Sin stock en bodega":         ("Compras", "No se compró suficiente para la demanda real"),
    "Importación atrasada":        ("Compras", "El pedido al proveedor salió tarde o llegó tarde"),
    "Comprometido en otro pedido": ("Asignación", "La mercancía existía y se prometió dos veces"),
    "Error de inventario":         ("Bodega", "El sistema decía que había y no había"),
    "Lote vencido retirado":       ("Bodega", "Estaba, pero no se podía vender"),
}
COLOR_AREA = {"Compras": "#8B1E1E", "Asignación": ACENTO, "Bodega": "#B5762F",
              "Logística": "#2B7A9B", "Comercial": PRIMARIO, "Administración": CLARO}


def _area(motivo: str) -> str:
    return DUENO_QUIEBRE.get(motivo, ("Sin asignar", ""))[0]


def _ventana(meses) -> str:
    """«mar 2026 – ago 2026». La ventana real, dicha en voz alta.

    Esta pantalla abre en trimestre y el comité (p30) siempre lee doce meses.
    Sin la ventana escrita al lado del número, las dos pantallas muestran la
    misma venta perdida con cifras distintas y parece que una de las dos miente.
    """
    a, b = mes_es(min(meses)), mes_es(max(meses))
    return a if a == b else f"{a} – {b}"


def _color_fill(v: float) -> str:
    """Rojo solo por debajo de la franja. Arriba de 98 es ámbar, no alarma.

    Arriba de la franja el problema existe pero es de bodega, no de servicio:
    pintarlo del mismo rojo que un 91% decía que fallarle al cliente y tener
    stock de más son la misma emergencia, y no lo son.
    """
    if v < FILL_SANO[0]:
        return ACENTO
    return GOOD if v <= FILL_SANO[1] else WARN


def _tabla_html(filas) -> str:
    """Filas etiqueta/valor sin el cromo de st.dataframe, para bloques cortos."""
    return '<table style="width:100%;border-collapse:collapse">' + "".join(
        f'<tr><td style="padding:6px 0;font-size:12px;color:{CLARO}">{k}</td>'
        f'<td style="padding:6px 0;font-size:13px;font-weight:700;color:{TINTA};'
        f'text-align:right">{v}</td></tr>' for k, v in filas) + "</table>"


def render():
    st.markdown(HEADER_CSS, unsafe_allow_html=True)
    st.markdown(encabezado(
        "Lo que no se vendió",
        "Quiebres, fill rate y devoluciones · la venta que se pierde antes de facturarse",
        "¿Qué nos cuesta fallar?"), unsafe_allow_html=True)
    filtros.encabezado_filtro()

    ventas_per = filtros.aplicar(b2b.ventas())
    # El recorte a QUIEBRES_DESDE va sobre las DOS tablas, no solo sobre
    # ventas. Hoy `quiebres.csv` empieza en marzo y recortarlo no cambia nada,
    # pero en cuanto entre una fila anterior el KPI la contaría y el gráfico la
    # descartaría —el `.reindex` de abajo la deja fuera— y las dos cifras de la
    # misma pantalla dejarían de cuadrar sin lanzar ningún error.
    q = filtros.aplicar(gerencia.quiebres())
    q = q[q["mes"] >= QUIEBRES_DESDE]
    d = filtros.aplicar(gerencia.devoluciones())
    d = d[d["mes"] >= DEVOLUCIONES_DESDE]
    # El denominador del fill rate solo puede contar meses con registro de
    # quiebres; si no, los meses viejos entran como si se hubiera servido todo.
    ve = ventas_per[ventas_per["mes"] >= QUIEBRES_DESDE]

    if q.empty or ve.empty:
        st.markdown(panel(
            "No hay líneas incompletas en esta vista",
            "Con el filtro puesto no queda ningún quiebre registrado. Puede ser "
            "una buena noticia o puede ser que el corte se fue antes de marzo de "
            "2026, que es cuando el ERP empezó a guardar lo pedido además de lo "
            "despachado. Amplíe el periodo o quite el filtro de vendedor.",
            "○", "azul"), unsafe_allow_html=True)
        return

    entregas = ve.groupby("mes")["entregas"].sum()
    inc_mes = q.groupby("mes").size().reindex(entregas.index).fillna(0)
    lineas_mes = entregas * LINEAS_POR_ENTREGA
    fill_mes = (1 - inc_mes / (lineas_mes + inc_mes)) * 100
    fill = float((1 - len(q) / (lineas_mes.sum() + len(q))) * 100)

    # La ventana real de esta pantalla y cuántos meses tiene. Todo lo que se
    # anualiza más abajo sale de aquí: el periodo por defecto es trimestre, no
    # semestre, y clavar el factor rompía el número sin avisar.
    meses_ventana = max(int(ve["mes"].nunique()), 1)
    ventana_txt = _ventana(ve["mes"].unique())
    factor_anual = 12 / meses_ventana

    perdido = float(q["valor_perdido"].sum())
    neto_ventana = float(ve["neto"].sum())
    # El mismo fill rate, medido en plata. Es la cifra que un COO calcula de
    # cabeza —venta perdida sobre venta— y si la pantalla no la pone, la pone
    # él y descubre que la versión que se le mostró era la favorecedora.
    pedido_total = neto_ventana + perdido
    fill_valor = float((1 - perdido / pedido_total) * 100) if pedido_total else 0.0

    # Devoluciones: dos cifras distintas y las dos ciertas.
    #
    #   · `dev_total` es la nota crédito del ERP (la columna `devoluciones` de
    #     ventas_cuenta_mes). Es la que resta la cascada de p21 y es LA cifra.
    #   · `dev_clas` es la parte que además trae motivo y responsable, que es
    #     lo único que se puede abrir y repartir.
    #
    # Mostrar solo la segunda hacía que p28 y p21 dieran totales distintos del
    # mismo hecho sin que nada lo explicara. Y el ratio va contra la venta
    # BRUTA: `neto` ya trae restadas las devoluciones, así que dividir entre él
    # era dividir un número de devoluciones entre una base que ya restó otro.
    vd = ventas_per[ventas_per["mes"] >= DEVOLUCIONES_DESDE]
    dev_total = float(vd["devoluciones"].sum())
    dev_clas = float(d["valor"].sum())
    base_dev = float(vd["bruto"].sum())
    dev_pct = dev_total / base_dev * 100 if base_dev else 0.0
    dev_cob = dev_clas / dev_total * 100 if dev_total else 0.0
    ventana_dev = _ventana(vd["mes"].unique()) if not vd.empty else ventana_txt

    # ── El costo oculto ─────────────────────────────────────────────────────
    # Se mide por CATEGORÍA, no por SKU, y es deliberado: el mesero no pide
    # «KY-0302», pide tequila. Al bar le da igual la referencia exacta; lo que
    # aprende es que a KYVA no le pida tequila. En la ventana completa, medido
    # por SKU aparece un solo caso y el riesgo se ve inexistente; medido por
    # categoría son veintiséis, que es lo que de verdad está pasando.
    q = q.copy()
    q["precio_implicito"] = q["valor_perdido"] / q["faltantes"].replace(0, np.nan)
    # El valor de lo pedido se calcula LÍNEA A LÍNEA y después se suma. Antes
    # se promediaba el precio del par y se multiplicaba por las unidades
    # sumadas: con precios implícitos que van de $15 mil a $800 mil, un par que
    # juntara una línea barata de mucho volumen con una cara de poco volumen
    # salía con la exposición inflada. Ponderar bien cuesta una columna.
    q["valor_pedido"] = q["pedidas"] * q["precio_implicito"]
    pares = q.groupby(["cuenta_id", "nombre", "canal", "ciudad", "vendedor",
                       "categoria"]).agg(
        fallas=("mes", "size"), meses=("mes", "nunique"),
        pedidas=("pedidas", "sum"), faltantes=("faltantes", "sum"),
        perdido=("valor_perdido", "sum"),
        valor_pedido=("valor_pedido", "sum")).reset_index()
    riesgo = pares[pares["fallas"] >= 2].copy()

    prob = st.session_state.get("sv_prob", 40)
    # Lo que esa cuenta nos pidió de esa categoría en la ventana con registro,
    # llevado a doce meses. No es lo que compró: es lo que pidió, que es
    # exactamente lo que se va a pedir en otra parte.
    #
    # El factor sale de la ventana, no de una constante. Estaba clavado en 2 —o
    # sea, suponía siempre seis meses— y el periodo por defecto es TRIMESTRE:
    # la exposición se anualizaba a seis meses y su tope a doce, y el «costo
    # oculto» pasaba de $863 mil a $81 M según el periodo sin que nada lo dijera.
    riesgo["expuesto"] = riesgo["valor_pedido"] * factor_anual

    # Tope de realidad: ninguna cuenta puede dejar de comprar más de lo que
    # compra. Sin este tope, dos pedidos grandes fallidos hacían que un club
    # apareciera perdiendo el doble de su facturación anual.
    venta_anual = ventas_per.groupby("cuenta_id")["neto"].sum() * (12 / max(
        ventas_per["mes"].nunique(), 1))
    tope = riesgo["cuenta_id"].map(venta_anual).fillna(0)
    grupo = riesgo.groupby("cuenta_id")["expuesto"].transform("sum")
    riesgo["expuesto"] = np.where(grupo > tope,
                                  riesgo["expuesto"] * tope / grupo.replace(0, np.nan),
                                  riesgo["expuesto"])
    riesgo["expuesto"] = riesgo["expuesto"].fillna(0)
    expuesto = float(riesgo["expuesto"].sum())
    costo_oculto = expuesto * prob / 100

    # ── KPIs ────────────────────────────────────────────────────────────────
    k = st.columns(4, gap="small")
    k[0].markdown(kpi(
        "Fill rate por líneas", pct(fill),
        f"Por valor: {pct(fill_valor)} · {num(len(q))} líneas incompletas",
        # Verde a partir de 95%: por encima de 98% el problema existe, pero es
        # sobrestock, no servicio, y pintarlo en rojo aquí confunde al que mira.
        # El delta lleva la cifra por valor porque el verde no es toda la
        # historia: por líneas se sirve 98% y por plata bastante menos.
        fill >= FILL_SANO[0], "📦",
        "Porcentaje de líneas de pedido que salieron completas. La de al lado "
        "es la misma cuenta medida en pesos, y es más baja porque la línea que "
        "falla es la grande.",
        f"Sano en el sector: 95-98% · {ventana_txt}"), unsafe_allow_html=True)
    k[1].markdown(kpi(
        "Venta perdida", cop(perdido, 0),
        f"{num(q['faltantes'].sum())} unidades que se pidieron y no salieron",
        False, "🩸",
        "Valorizada al precio de la propia línea del pedido. No es una "
        "proyección: es mercancía que el cliente ya había decidido comprar.",
        f"Ventana con registro: {ventana_txt}"),
        unsafe_allow_html=True)
    k[2].markdown(kpi(
        "Devoluciones", cop(dev_total, 0),
        f"{pct(dev_pct, 2)} de la venta bruta · {pct(dev_cob, 0)} con motivo "
        f"registrado", dev_pct < 1.0, "↩️",
        "La nota crédito completa del ERP, la misma que resta la cascada de "
        "rentabilidad por cuenta. Abajo se abre la parte que trae motivo y "
        "responsable, que es la única que se puede repartir.",
        "Sano en distribución: por debajo de 1%"), unsafe_allow_html=True)
    k[3].markdown(kpi(
        "Costo oculto", cop(costo_oculto, 0),
        f"{num(riesgo['cuenta_id'].nunique())} cuentas con la misma falla dos veces",
        False, "🕳️",
        f"Venta anual en riesgo de irse en silencio, con un supuesto de "
        f"{prob}% de abandono. El supuesto se ajusta abajo.",
        "Exposición a 12 meses · no se suma a la venta perdida"),
        unsafe_allow_html=True)

    st.markdown(espacio(18), unsafe_allow_html=True)

    # ── Fill rate mes a mes y la plata que se fue con él ────────────────────
    st.markdown('<div class="ky-sub">Cómo venimos sirviendo</div>',
                unsafe_allow_html=True)
    c = st.columns([3, 2], gap="large")

    with c[0]:
        fig = go.Figure()
        fig.add_hrect(y0=FILL_SANO[0], y1=FILL_SANO[1], fillcolor="#2f7a48",
                      opacity=.10, line_width=0)
        fig.add_trace(go.Scatter(
            x=[mes_es(m) for m in fill_mes.index], y=fill_mes.values,
            mode="lines+markers+text", line=dict(color=PRIMARIO, width=2.6),
            marker=dict(size=9,
                        color=[_color_fill(v) for v in fill_mes.values],
                        line=dict(width=1.5, color="#fff")),
            text=[f"{v:.1f}%" for v in fill_mes.values],
            textposition="top center", textfont=dict(size=10, color=MUTED),
            hovertemplate="%{x}<br>Fill rate: %{y:.2f}%<extra></extra>"))
        # El eje arranca justo debajo del piso de la franja, no en 93: con
        # estos datos la serie vive entre 97 y 99 y un eje desde 93 dejaba la
        # mitad del alto en blanco y la línea pegada al techo, plana.
        fig.update_yaxes(
            title="Líneas servidas completas (%)",
            range=[min(FILL_SANO[0] - 0.5, float(fill_mes.min()) - 0.4),
                   max(100.2, float(fill_mes.max()) + 0.5)])
        st.plotly_chart(light(fig, 330), width="stretch", theme=None, config=PLOTLY_CONFIG)
        st.caption(
            f"La franja verde es el 95-98% que el sector considera sano. "
            f"El punto va **rojo por debajo de 95%** —ahí se pierden cuentas— y "
            f"**ámbar por encima de 98%**, que no es alarma sino aviso: se "
            f"sirve todo porque hay stock de más, y ese stock es la misma plata "
            f"quieta en bodega. El promedio del periodo es **{pct(fill)}** por "
            f"líneas y **{pct(fill_valor)}** medido en pesos.")

    with c[1]:
        pm = q.groupby("mes")["valor_perdido"].sum().reindex(entregas.index).fillna(0)
        fig2 = go.Figure(go.Bar(
            x=[mes_es(m) for m in pm.index], y=pm.values, marker_color=ACENTO,
            name="Venta perdida"))
        fig2.update_yaxes(title="Venta perdida del mes")
        st.plotly_chart(light(fig2, 330, moneda=True), width="stretch", theme=None, config=PLOTLY_CONFIG)
        # La categoría sale del dato, no de la memoria: decir «casi siempre
        # whisky» cuando el whisky es el 48% es la clase de frase redonda que
        # el que conoce su negocio desarma en un segundo.
        cat_v = q.groupby("categoria")["valor_perdido"].sum().sort_values(
            ascending=False)
        st.caption(
            f"Un mes con buen fill rate y mucha plata perdida significa que "
            f"fallaron **pocas líneas pero grandes**. La categoría que más pesa "
            f"es **{cat_v.index[0].lower()}**, con "
            f"{pct(cat_v.iloc[0] / perdido * 100, 0)} del valor perdido — es la "
            f"primera, no es todo: el resto se reparte entre otras "
            f"{len(cat_v) - 1} categorías.")

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── El motivo, que es lo único que convierte esto en una tarea ──────────
    st.markdown('<div class="ky-sub">De quién es la plata que se perdió</div>',
                unsafe_allow_html=True)
    m = q.groupby("motivo").agg(
        lineas=("mes", "size"), unidades=("faltantes", "sum"),
        valor=("valor_perdido", "sum")).reset_index()
    m["area"] = m["motivo"].map(_area)
    m = m.sort_values("valor")

    fig3 = go.Figure(go.Bar(
        y=m["motivo"], x=m["valor"], orientation="h",
        marker_color=[COLOR_AREA.get(a, CLARO) for a in m["area"]],
        text=[f"{cop(v, 0)} · {a}" for v, a in zip(m["valor"], m["area"])],
        textposition="outside", textfont=dict(size=11),
        customdata=np.stack([m["lineas"], m["unidades"], m["area"]], -1),
        hovertemplate="<b>%{y}</b><br>Área: %{customdata[2]}"
                      "<br>%{customdata[0]} líneas · %{customdata[1]:,.0f} unidades"
                      "<br>%{x:,.0f}<extra></extra>"))
    fig3.update_xaxes(title="Venta perdida del periodo",
                      range=[0, float(m["valor"].max()) * 1.42])
    st.plotly_chart(light(fig3, 300), width="stretch", theme=None, config=PLOTLY_CONFIG)

    top_m = m.iloc[-1]
    area_top = q.assign(area=q["motivo"].map(_area)).groupby(
        "area")["valor_perdido"].sum().sort_values(ascending=False)
    st.markdown(panel(
        "Un número por área, no un número por la empresa",
        "<br>".join(
            f"<b>{mo}</b> — {cop(v, 0)} · dueño: <b>{DUENO_QUIEBRE[mo][0]}</b>. "
            f"{DUENO_QUIEBRE[mo][1]}."
            for mo, v in zip(m["motivo"][::-1], m["valor"][::-1])
            if mo in DUENO_QUIEBRE) +
        f"<br><br>El motivo más caro es <b>{top_m['motivo'].lower()}</b>, con "
        f"{cop(top_m['valor'], 0)} en {int(top_m['lineas'])} líneas. "
        f"Sumado por área, <b>{area_top.index[0]}</b> responde por "
        f"{cop(area_top.iloc[0], 0)} de los {cop(perdido, 0)} del periodo. "
        f"Esa es la conversación del lunes, y tiene un solo interlocutor — "
        f"no un comité.",
        "🎯", "alerta"), unsafe_allow_html=True)

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── Qué falla y a quién le falla ────────────────────────────────────────
    st.markdown('<div class="ky-sub">Qué se está quebrando</div>',
                unsafe_allow_html=True)
    c2 = st.columns([2, 3], gap="large")

    with c2[0]:
        mar = q.groupby("marca").agg(
            valor=("valor_perdido", "sum"), lineas=("mes", "size"),
            cuentas=("cuenta_id", "nunique")).reset_index()
        mar = mar.sort_values("valor", ascending=False).head(10).sort_values("valor")
        fig4 = go.Figure(go.Bar(
            y=mar["marca"], x=mar["valor"], orientation="h", marker_color=PRIMARIO,
            customdata=np.stack([mar["lineas"], mar["cuentas"]], -1),
            hovertemplate="<b>%{y}</b><br>%{customdata[0]} líneas fallidas"
                          "<br>%{customdata[1]} cuentas afectadas"
                          "<br>%{x:,.0f}<extra></extra>"))
        fig4.update_xaxes(title="Venta perdida · top 10 marcas")
        st.plotly_chart(light(fig4, 360), width="stretch", theme=None, config=PLOTLY_CONFIG)
        st.caption(
            "Fallar una marca exclusiva pesa doble: se pierde la venta **y** "
            "las unidades que cuentan para la cuota del trimestre con ese "
            "proveedor.")

    with c2[1]:
        ref = q.groupby(["sku", "producto", "categoria"]).agg(
            lineas=("mes", "size"), faltantes=("faltantes", "sum"),
            pedidas=("pedidas", "sum"), valor=("valor_perdido", "sum"),
            cuentas=("cuenta_id", "nunique"),
            motivo=("motivo", lambda s: s.mode().iloc[0])).reset_index()
        ref["servido"] = (1 - ref["faltantes"] / ref["pedidas"]) * 100
        ref = ref.sort_values("valor", ascending=False).head(12)
        t = pd.DataFrame({
            "Referencia": ref["producto"],
            "Categoría": ref["categoria"],
            "Veces": ref["lineas"].astype(int),
            "Cuentas": ref["cuentas"].astype(int),
            "Unidades no servidas": ref["faltantes"].astype(int),
            "Se sirvió": ref["servido"].map(lambda v: pct(v, 0)),
            "Venta perdida": ref["valor"].map(lambda v: cop(v, 0)),
            "Motivo dominante": ref["motivo"],
        })
        st.dataframe(t, hide_index=True, width="stretch", height=360)
        st.caption(
            "«Se sirvió» es el porcentaje de lo que el cliente pidió de esa "
            "referencia y sí salió. Una referencia con muchas cuentas y poco "
            "servido no es un problema de inventario: es un problema de "
            "pronóstico de compra.")

    st.markdown(espacio(16), unsafe_allow_html=True)

    st.markdown('<div class="ky-sub">A quién le estamos fallando</div>',
                unsafe_allow_html=True)
    cu = q.groupby(["nombre", "canal", "ciudad", "vendedor"]).agg(
        lineas=("mes", "size"), meses=("mes", "nunique"),
        faltantes=("faltantes", "sum"), valor=("valor_perdido", "sum"),
        categorias=("categoria", "nunique")).reset_index()
    cu = cu.sort_values("valor", ascending=False).head(12)
    tc = pd.DataFrame({
        "Cuenta": cu["nombre"], "Canal": cu["canal"], "Ciudad": cu["ciudad"],
        "Vendedor": cu["vendedor"],
        "Líneas fallidas": cu["lineas"].astype(int),
        "Meses con falla": cu["meses"].astype(int),
        "Categorías": cu["categorias"].astype(int),
        "Venta perdida": cu["valor"].map(lambda v: cop(v, 0)),
    })
    st.dataframe(tc, hide_index=True, width="stretch")
    st.caption(
        "La columna que importa es **meses con falla**. Fallar tres veces el "
        "mismo mes es un problema de bodega y el cliente lo perdona; fallar un "
        "mes de cada dos es lo que hace que el bar llame a otro proveedor "
        "«por si acaso» — y ese otro proveedor ya no se va.")

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── Devoluciones: motivo Y responsable ──────────────────────────────────
    st.markdown('<div class="ky-sub">Las devoluciones, abiertas por responsable</div>',
                unsafe_allow_html=True)
    if d.empty:
        st.caption("Sin devoluciones registradas en esta vista.")
    else:
        cruce = d.pivot_table(index="motivo", columns="responsable",
                              values="valor", aggfunc="sum", fill_value=0)
        c3 = st.columns([3, 2], gap="large")
        with c3[0]:
            fig5 = go.Figure(go.Heatmap(
                z=cruce.values, x=list(cruce.columns), y=list(cruce.index),
                colorscale=[[0, "#FBF7F8"], [0.5, "#E9B9BA"], [1, ACENTO]],
                showscale=False, xgap=3, ygap=3,
                text=[[cop(v, 0) if v else "—" for v in fila] for fila in cruce.values],
                texttemplate="%{text}", textfont=dict(size=11),
                hovertemplate="<b>%{y}</b><br>Responsable: %{x}"
                              "<br>%{z:,.0f}<extra></extra>"))
            fig5 = light(fig5, 320)
            fig5.update_layout(hovermode="closest")
            st.plotly_chart(fig5, width="stretch", theme=None, config=PLOTLY_CONFIG)
        with c3[1]:
            resp = d.groupby("responsable").agg(
                valor=("valor", "sum"), unidades=("unidades", "sum"),
                casos=("mes", "size")).reset_index().sort_values("valor")
            fig6 = go.Figure(go.Bar(
                y=resp["responsable"], x=resp["valor"], orientation="h",
                marker_color=[COLOR_AREA.get(a, CLARO) for a in resp["responsable"]],
                text=[cop(v, 0) for v in resp["valor"]], textposition="outside",
                textfont=dict(size=11),
                customdata=np.stack([resp["casos"], resp["unidades"]], -1),
                hovertemplate="<b>%{y}</b><br>%{customdata[0]} devoluciones"
                              "<br>%{customdata[1]:,.0f} unidades<extra></extra>"))
            fig6.update_xaxes(title="Valor devuelto",
                              range=[0, float(resp["valor"].max()) * 1.45])
            st.plotly_chart(light(fig6, 320), width="stretch", theme=None, config=PLOTLY_CONFIG)

        # Los motivos se enumeran desde el DATO y ordenados por plata. Antes la
        # lista estaba escrita a mano, decía «cuatro problemas» y se saltaba
        # justo «no rotó en el punto» —que es el más caro de Comercial—, así
        # que el mapa de calor de al lado pintaba cinco filas y el texto cuatro.
        por_motivo = d.groupby("motivo")["valor"].sum().sort_values(
            ascending=False)
        lista = "<br>".join(
            f"<b>{mo}</b> ({cop(v, 0)} · dueño: "
            f"<b>{DUENO_DEVOLUCION.get(mo, ('Sin asignar', ''))[0]}</b>). "
            f"{DUENO_DEVOLUCION.get(mo, ('', 'Sin dueño asignado'))[1]}."
            for mo, v in por_motivo.items())

        por_resp = d.groupby("responsable")["valor"].sum().sort_values(
            ascending=False)
        peor_resp, peor_val = por_resp.index[0], float(por_resp.iloc[0])
        # Y el área que más devuelve se abre por dentro. «Comercial devuelve
        # $4,6 M, se corrige al tomar el pedido» era falso: más de la mitad de
        # esa plata no es un pedido mal tomado, es mercancía sobrecolocada.
        dentro = d[d["responsable"] == peor_resp].groupby(
            "motivo")["valor"].sum().sort_values(ascending=False)
        desglose = " · ".join(f"{cop(v, 0)} de «{mo.lower()}»"
                              for mo, v in dentro.items())
        st.markdown(panel(
            "Por qué el total de devoluciones no sirve para nada",
            f"En el ERP las devoluciones de {ventana_dev} son una sola línea: "
            f"{cop(dev_total, 0)} en notas crédito. De esa plata, "
            f"{cop(dev_clas, 0)} ({pct(dev_cob, 0)}) llega con motivo y "
            f"responsable anotados —las {num(len(d))} devoluciones de abajo—; "
            f"el resto entra como nota crédito sin causa y por eso no aparece "
            f"en el mapa. <b>Ese hueco ya es un hallazgo</b>: "
            f"{pct(100 - dev_cob, 0)} de lo que vuelve no tiene a quién "
            f"devolvérselo.<br><br>"
            f"Lo que sí está clasificado son {len(por_motivo)} problemas con "
            f"dueños y soluciones distintas:<br><br>{lista}<br><br>"
            f"Hoy el área que más devuelve es <b>{peor_resp}</b>, con "
            f"{cop(peor_val, 0)} — y por dentro son {len(dentro)}: {desglose}. "
            f"Con el total agregado no se puede decir ni la primera frase ni "
            f"la segunda, y es la segunda la que dice qué hacer.",
            "↩️", "alerta"), unsafe_allow_html=True)

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── El costo oculto ─────────────────────────────────────────────────────
    st.markdown('<div class="ky-sub">El costo que no aparece en ningún lado</div>',
                unsafe_allow_html=True)
    st.markdown(panel(
        "El supuesto, dicho en voz alta",
        "Un bar al que se le falla <b>dos veces la misma categoría</b> deja de "
        "pedirla. No reclama, no se queja y no se va del todo: simplemente la "
        "próxima vez le pide el tequila a otro, y ese proveedor ya entró por la "
        "puerta. El daño no es el pedido fallido: es la venta anual de esa "
        "categoría en esa cuenta.<br><br>"
        "Se mide por <b>categoría y no por referencia</b> a propósito, porque "
        "al bar le da igual el SKU exacto. La exposición se valoriza con lo que "
        "esa cuenta <b>pidió</b> —no lo que se le vendió— en los "
        f"{meses_ventana} mes{'es' if meses_ventana != 1 else ''} con registro "
        f"({ventana_txt}), llevado a doce, y "
        "se topa con la venta anual real de la cuenta: nadie puede dejar de "
        "comprar más de lo que compra.<br><br>"
        "<b>El porcentaje de abandono es un supuesto, no un dato.</b> Muévalo y "
        "vea el rango. Es la única cifra de este panel que no sale del ERP — y "
        "por eso el resultado es una <b>exposición a doce meses</b>, que no se "
        "suma con la venta perdida del periodo: son unidades distintas.",
        "🕳️", "azul"), unsafe_allow_html=True)

    st.slider("Probabilidad de que la cuenta deje de pedir esa categoría (%)",
              min_value=10, max_value=80, value=40, step=5, key="sv_prob")

    if riesgo.empty:
        st.caption("Ninguna cuenta acumula dos fallas en la misma categoría en "
                   "esta vista. Es el mejor resultado posible de esta pantalla.")
    else:
        r = riesgo.sort_values("expuesto", ascending=False).head(14)
        tr = pd.DataFrame({
            "Cuenta": r["nombre"], "Canal": r["canal"], "Ciudad": r["ciudad"],
            "Vendedor": r["vendedor"], "Categoría": r["categoria"],
            "Fallas": r["fallas"].astype(int),
            "Unidades no servidas": r["faltantes"].astype(int),
            "Perdido ya": r["perdido"].map(lambda v: cop(v, 0)),
            "Venta anual expuesta": r["expuesto"].map(lambda v: cop(v, 0)),
            "En riesgo al supuesto": (r["expuesto"] * prob / 100).map(lambda v: cop(v, 0)),
        })
        st.dataframe(tr, hide_index=True, width="stretch")

        # Con pocos pares el patrón no existe todavía, y el texto de abajo está
        # escrito en tono rotundo. En trimestre son diez casos y el más caro
        # tiene exactamente dos fallas: decir «deja de pedirla» sobre n=2 con el
        # mismo aplomo que sobre veintiséis es lo que quema la credibilidad.
        pocos = len(riesgo) < 8
        if pocos:
            st.caption(
                f"⚠ Son **{len(riesgo)} pares cuenta-categoría** en esta "
                f"ventana de {meses_ventana} mes"
                f"{'es' if meses_ventana != 1 else ''} — muy pocos para leerlo "
                f"como patrón. Sirve para revisar estos casos uno por uno, no "
                f"para sacar una conclusión sobre la operación. Amplíe el "
                f"periodo para ver si se repite.")

        peor = r.iloc[0]
        st.markdown(espacio(6), unsafe_allow_html=True)
        cols = st.columns([2, 3], gap="large")
        with cols[0]:
            st.markdown(_tabla_html([
                ("Cuentas con la misma falla dos veces", num(riesgo["cuenta_id"].nunique())),
                ("Pares cuenta-categoría en riesgo", num(len(riesgo))),
                ("Venta expuesta · 12 meses", cop(expuesto, 0)),
                (f"En riesgo con abandono del {prob}% · 12 meses",
                 cop(costo_oculto, 0)),
                (f"Venta ya perdida · {ventana_txt}", cop(perdido, 0)),
                # La relación se dice en su unidad: es una exposición a doce
                # meses contra un flujo de la ventana. Sin el «anualizada» al
                # lado, el «×» se lee como si fueran dos cifras comparables.
                ("Exposición anualizada / venta perdida de la ventana",
                 f"{costo_oculto / perdido:.1f}×" if perdido else "—"),
            ]), unsafe_allow_html=True)
        with cols[1]:
            st.markdown(panel(
                f"El caso más caro: {peor['nombre']}",
                f"{peor['canal']} en {peor['ciudad']}, cuenta de "
                f"<b>{peor['vendedor']}</b>. Se le falló <b>{int(peor['fallas'])} "
                f"veces</b> en {peor['categoria'].lower()}: "
                f"{int(peor['faltantes'])} unidades que pidió y no salieron, "
                f"{cop(peor['perdido'], 0)} de venta perdida directa. "
                f"Detrás hay <b>{cop(peor['expuesto'], 0)}</b> de compra anual de "
                f"esa categoría, y con el supuesto puesto "
                f"<b>{cop(peor['expuesto'] * prob / 100, 0)}</b> en riesgo.<br><br>"
                f"La acción no es un descuento: es que el vendedor llame antes "
                f"de que el cliente se dé cuenta, y que esa categoría entre en "
                f"stock de seguridad para esa cuenta. Cuesta una llamada y unas "
                f"cajas quietas — contra {cop(peor['expuesto'] * prob / 100, 0)}."
                + (f"<br><br>Dicho con cuidado: son <b>{int(peor['fallas'])} "
                   f"fallas</b> en {meses_ventana} mes"
                   f"{'es' if meses_ventana != 1 else ''}. Alcanza para hacer "
                   f"la llamada, no para afirmar que la cuenta ya se está "
                   f"yendo." if pocos or int(peor["fallas"]) <= 2 else ""),
                "📞", "alerta"), unsafe_allow_html=True)

        # El juicio del fill rate se escribe aquí y no en una plantilla fija:
        # decir «dentro de la franja sana» cuando el filtro dejó la vista en 91%
        # es exactamente el tipo de frase que hace que nadie vuelva a creerle
        # al panel.
        #
        # Y la rama de arriba de 98 ya no acusa: el KPI de esta misma pantalla
        # pinta verde desde 95, así que decir «sobrestock» aquí contradecía al
        # KPI en las cuatro ventanas a la vez. Arriba de la franja el problema
        # existe, pero es de bodega y no de servicio, y eso es lo que dice.
        juicio = ("por debajo de la franja sana, que es lo que hace que un bar "
                  "llame a otro proveedor" if fill < FILL_SANO[0] else
                  "dentro de la franja sana" if fill <= FILL_SANO[1] else
                  "en el techo de la franja de referencia. El KPI sigue en "
                  "verde y está bien que siga: arriba de 98% el problema deja "
                  "de ser el cliente y pasa a ser el inventario, y eso se mira "
                  "contra bodega, no contra servicio")

        # La prosa de abajo afirmaba que «lo que falla son los pedidos grandes
        # de whisky». La mitad era cierta y la mitad no: las líneas fallidas SÍ
        # son sistemáticamente grandes, pero no son unas pocas ni son casi
        # siempre whisky. Las dos cifras salen del dato y se dicen con nombre.
        med_fallida = float(q["valor_perdido"].median())
        linea_servida = (neto_ventana / float(lineas_mes.sum())
                         if lineas_mes.sum() else 0.0)
        vals = q["valor_perdido"].sort_values(ascending=False)
        n_mitad = (int((vals.cumsum() >= vals.sum() * 0.5).to_numpy().argmax()) + 1
                   if vals.sum() else 0)
        st.markdown(panel(
            "La cuenta completa del servicio",
            f"La ventana ({ventana_txt}) cierra con <b>{pct(fill)}</b> de fill "
            f"rate <b>medido por líneas</b>: {juicio}. Medido <b>en pesos</b> "
            f"es <b>{pct(fill_valor)}</b>: {cop(perdido, 0)} de venta que el "
            f"cliente ya había decidido comprar, sobre {cop(pedido_total, 0)} "
            f"de venta pedida.<br><br>"
            f"Esa distancia de <b>{num(fill - fill_valor, 1)} puntos</b> entre "
            f"las dos cifras es el punto incómodo de la métrica, y no es "
            f"redondeo: la línea fallida <b>mediana</b> vale "
            f"{cop(med_fallida, 0)} contra {cop(linea_servida, 0)} de la línea "
            f"servida promedio. <b>No fallan las líneas pequeñas: fallan las "
            f"grandes</b> — y no es un puñado de casos que se puedan explicar "
            f"aparte: hacen falta {n_mitad} líneas distintas para juntar la "
            f"mitad del valor perdido, de {num(len(q))} en total. Por eso el "
            f"98% no tranquiliza.<br><br>"
            f"<b>Lo ya perdido en la ventana:</b> {cop(perdido, 0)} de venta "
            f"que no salió, más {cop(dev_total, 0)} de producto que volvió, son "
            f"<b>{cop(perdido + dev_total, 0)}</b>. Las dos cifras salen del "
            f"ERP y son del mismo periodo.<br><br>"
            f"<b>Aparte, y en otra unidad:</b> {cop(costo_oculto, 0)} de venta "
            f"anual expuesta en cuentas que están aprendiendo a no pedirnos una "
            f"categoría. <b>No se suma a lo de arriba</b> —aquello es un flujo "
            f"de {meses_ventana} mes{'es' if meses_ventana != 1 else ''} que ya "
            f"ocurrió, y esto es una exposición a doce meses que todavía no, y "
            f"que además depende de un porcentaje que puso usted—. Pero tampoco "
            f"está en ningún informe de ventas, porque ningún informe de ventas "
            f"mide lo que no se vendió.",
            "🧾", "alerta"), unsafe_allow_html=True)
