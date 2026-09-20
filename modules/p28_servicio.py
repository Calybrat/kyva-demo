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

# Un pedido a un bar lleva del orden de once referencias distintas. Es el
# denominador del fill rate y es la constante más delicada del módulo: la
# tabla de quiebres SOLO guarda las líneas que fallaron, y dividir entre ellas
# daba un fill rate de 35%, imposible para un negocio que sigue vendiendo.
LINEAS_POR_ENTREGA = 11

# Sano según el sector. La franja, no el punto: el 100% también es un problema.
FILL_SANO = (95.0, 98.0)

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

    q = filtros.aplicar(gerencia.quiebres())
    d = filtros.aplicar(gerencia.devoluciones())
    ventas_per = filtros.aplicar(b2b.ventas())
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

    perdido = float(q["valor_perdido"].sum())
    dev_valor = float(d["valor"].sum())
    # Las devoluciones arrancan en enero y los quiebres en marzo: el ratio se
    # calcula solo sobre los meses que las dos tablas comparten, o queda inflado.
    base_dev = float(ventas_per.loc[ventas_per["mes"].isin(d["mes"].unique()), "neto"].sum())
    dev_pct = dev_valor / base_dev * 100 if base_dev else 0.0

    # ── El costo oculto ─────────────────────────────────────────────────────
    # Se mide por CATEGORÍA, no por SKU, y es deliberado: el mesero no pide
    # «KY-0302», pide tequila. Al bar le da igual la referencia exacta; lo que
    # aprende es que a KYVA no le pida tequila. Medido por SKU aparece un solo
    # caso en seis meses y el riesgo se ve inexistente; medido por categoría son
    # veintiséis, que es lo que de verdad está pasando.
    q = q.copy()
    q["precio_implicito"] = q["valor_perdido"] / q["faltantes"].replace(0, np.nan)
    pares = q.groupby(["cuenta_id", "nombre", "canal", "ciudad", "vendedor",
                       "categoria"]).agg(
        fallas=("mes", "size"), meses=("mes", "nunique"),
        pedidas=("pedidas", "sum"), faltantes=("faltantes", "sum"),
        perdido=("valor_perdido", "sum"),
        precio=("precio_implicito", "mean")).reset_index()
    riesgo = pares[pares["fallas"] >= 2].copy()

    prob = st.session_state.get("sv_prob", 40)
    # Lo que esa cuenta nos pidió de esa categoría en los seis meses de
    # registro, llevado a doce. No es lo que compró: es lo que pidió, que es
    # exactamente lo que se va a pedir en otra parte.
    riesgo["expuesto"] = riesgo["pedidas"] * riesgo["precio"] * 2

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
        "Fill rate", pct(fill),
        f"{num(len(q))} líneas servidas incompletas",
        # Verde a partir de 95%: por encima de 98% el problema existe, pero es
        # sobrestock, no servicio, y pintarlo en rojo aquí confunde al que mira.
        fill >= FILL_SANO[0], "📦",
        "Porcentaje de líneas de pedido que salieron completas. Cada punto que "
        "falta es un pedido que el cliente tuvo que completar en otro lado.",
        "Sano en el sector: 95-98%"), unsafe_allow_html=True)
    k[1].markdown(kpi(
        "Venta perdida", cop(perdido, 0),
        f"{num(q['faltantes'].sum())} unidades que se pidieron y no salieron",
        False, "🩸",
        "Valorizada al precio de la propia línea del pedido. No es una "
        "proyección: es mercancía que el cliente ya había decidido comprar."),
        unsafe_allow_html=True)
    k[2].markdown(kpi(
        "Devoluciones", cop(dev_valor, 0),
        f"{pct(dev_pct, 2)} de la venta neta", dev_pct < 1.0, "↩️",
        "Producto que volvió. Importa menos el total que quién lo causó: "
        "transporte, bodega, compras y comercial son cuatro problemas distintos.",
        "Sano en distribución: por debajo de 1%"), unsafe_allow_html=True)
    k[3].markdown(kpi(
        "Costo oculto", cop(costo_oculto, 0),
        f"{num(riesgo['cuenta_id'].nunique())} cuentas con la misma falla dos veces",
        False, "🕳️",
        f"Venta anual en riesgo de irse en silencio, con un supuesto de "
        f"{prob}% de abandono. El supuesto se ajusta abajo.",
        "Nadie reclama: simplemente deja de pedir"), unsafe_allow_html=True)

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
            marker=dict(size=9, color=[GOOD if FILL_SANO[0] <= v <= FILL_SANO[1]
                                       else ACENTO for v in fill_mes.values],
                        line=dict(width=1.5, color="#fff")),
            text=[f"{v:.1f}%" for v in fill_mes.values],
            textposition="top center", textfont=dict(size=10, color=MUTED),
            hovertemplate="%{x}<br>Fill rate: %{y:.2f}%<extra></extra>"))
        fig.update_yaxes(title="Líneas servidas completas (%)",
                         range=[min(93, fill_mes.min() - 1.5), 100.4])
        st.plotly_chart(light(fig, 330), use_container_width=True)
        st.caption(
            f"La franja verde es el 95-98% que el sector considera sano. "
            f"**Arriba de 98% tampoco es gratis**: se sirve todo porque hay "
            f"stock de más, y ese stock es la misma plata quieta en bodega. El "
            f"promedio del periodo es **{pct(fill)}**.")

    with c[1]:
        pm = q.groupby("mes")["valor_perdido"].sum().reindex(entregas.index).fillna(0)
        fig2 = go.Figure(go.Bar(
            x=[mes_es(m) for m in pm.index], y=pm.values, marker_color=ACENTO,
            name="Venta perdida"))
        fig2.update_yaxes(title="Venta perdida del mes")
        st.plotly_chart(light(fig2, 330, moneda=True), use_container_width=True)
        st.caption(
            "Un mes con buen fill rate y mucha plata perdida significa que "
            "fallaron **pocas líneas pero grandes**: casi siempre whisky de "
            "cuenta corporativa, que es el pedido que menos se puede fallar.")

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
    st.plotly_chart(light(fig3, 300), use_container_width=True)

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
        st.plotly_chart(light(fig4, 360), use_container_width=True)
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
            st.plotly_chart(fig5, use_container_width=True)
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
            st.plotly_chart(light(fig6, 320), use_container_width=True)

        peor_resp = d.groupby("responsable")["valor"].sum().idxmax()
        peor_val = float(d.groupby("responsable")["valor"].sum().max())
        averia = float(d.loc[d["motivo"] == "Avería en transporte", "valor"].sum())
        vencido = float(d.loc[d["motivo"] == "Producto vencido", "valor"].sum())
        st.markdown(panel(
            "Por qué el total de devoluciones no sirve para nada",
            f"En el ERP las {num(len(d))} devoluciones del periodo son una sola "
            f"línea: {cop(dev_valor, 0)} en notas crédito. Abiertas, son cuatro "
            f"problemas con cuatro dueños y cuatro soluciones distintas:<br><br>"
            f"<b>Avería en transporte</b> ({cop(averia, 0)}) se arregla con "
            f"estiba y ruta, no hablando con el cliente. "
            f"<b>Producto vencido</b> ({cop(vencido, 0)}) no es una devolución: "
            f"es un error de compra que se descubrió seis meses tarde en la "
            f"nevera del bar. "
            f"<b>Pedido equivocado</b> es del vendedor y se corrige en el "
            f"momento de tomar el pedido. "
            f"<b>Diferencia de precio</b> ni siquiera es un problema de "
            f"producto: es lista de precios contra lo que el vendedor prometió."
            f"<br><br>Hoy el área que más devuelve es <b>{peor_resp}</b>, con "
            f"{cop(peor_val, 0)}. Con el total agregado, esa frase no se puede "
            f"decir — y sin esa frase nadie cambia nada.",
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
        "Se mide por <b>categoría y no por referencia</b> a propósito: al bar le "
        "da igual el SKU exacto: lo que aprende es que a KYVA no le pida "
        "tequila. La exposición se valoriza con lo que esa cuenta <b>pidió</b> "
        "—no lo que se le vendió— en los meses con registro, llevado a doce, y "
        "se topa con la venta anual real de la cuenta: nadie puede dejar de "
        "comprar más de lo que compra.<br><br>"
        "<b>El porcentaje de abandono es un supuesto, no un dato.</b> Muévalo y "
        "vea el rango. Es la única cifra de este panel que no sale del ERP.",
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

        peor = r.iloc[0]
        st.markdown(espacio(6), unsafe_allow_html=True)
        cols = st.columns([2, 3], gap="large")
        with cols[0]:
            st.markdown(_tabla_html([
                ("Cuentas con la misma falla dos veces", num(riesgo["cuenta_id"].nunique())),
                ("Pares cuenta-categoría en riesgo", num(len(riesgo))),
                ("Venta anual expuesta", cop(expuesto, 0)),
                (f"En riesgo con abandono del {prob}%", cop(costo_oculto, 0)),
                ("Venta ya perdida en el periodo", cop(perdido, 0)),
                ("Relación costo oculto / venta perdida",
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
                f"cajas quietas — contra {cop(peor['expuesto'] * prob / 100, 0)}.",
                "📞", "alerta"), unsafe_allow_html=True)

        # El juicio del fill rate se escribe aquí y no en una plantilla fija:
        # decir «dentro de la franja sana» cuando el filtro dejó la vista en 91%
        # es exactamente el tipo de frase que hace que nadie vuelva a creerle
        # al panel.
        juicio = ("por debajo de la franja sana, que es lo que hace que un bar "
                  "llame a otro proveedor" if fill < FILL_SANO[0] else
                  "dentro de la franja sana" if fill <= FILL_SANO[1] else
                  "por encima de la franja sana, que casi siempre se paga con "
                  "sobrestock en bodega")
        st.markdown(panel(
            "La cuenta completa del servicio",
            f"El periodo cierra con <b>{pct(fill)}</b> de fill rate: {juicio}, "
            f"y aun así <b>{cop(perdido, 0)}</b> de venta que el "
            f"cliente ya había decidido comprar y no se facturó. Ese es el punto "
            f"incómodo de esta métrica — <b>un fill rate respetable convive con "
            f"mucha plata perdida</b>, porque lo que falla no son las líneas "
            f"pequeñas: son los pedidos grandes de whisky.<br><br>"
            f"Sumado: {cop(perdido, 0)} de venta perdida directa, "
            f"{cop(dev_valor, 0)} de devoluciones y {cop(costo_oculto, 0)} de "
            f"cuentas que están aprendiendo a no pedirnos una categoría. "
            f"<b>{cop(perdido + dev_valor + costo_oculto, 0)}</b> que no están en "
            f"ningún informe de ventas porque ningún informe de ventas mide lo "
            f"que no se vendió.",
            "🧾", "alerta"), unsafe_allow_html=True)
