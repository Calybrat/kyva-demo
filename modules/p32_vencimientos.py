"""Vencimientos: lo que ya está en la bodega y se echa a perder si nadie lo saca.

De la revisión adversaria, y es el reverso exacto del módulo de reposición:

    «Vendo cerveza, que dura cuatro a seis meses. El módulo de reposición razona
    con lead times, muy bien, pero razona solo hacia adelante. Nadie me dice qué
    tengo en bodega que se vence en 60 días y hay que sacar ya.»

Comprar y vencer son el mismo error con doce semanas de diferencia. La compra se
mira todos los lunes; el vencimiento no lo mira nadie hasta que el jefe de bodega
avisa, y para entonces ya no es una decisión comercial sino una pérdida contable.

**Esto no aplica a todo el catálogo, y decirlo importa.** Un whisky, un ron, un
aguardiente o un tequila no se vencen: mejoran o se quedan igual, y en el peor
caso pierden etiqueta. El riesgo vive en cinco categorías —cerveza, mixers,
vino, espumosos y accesorios gourmet— que son la minoría del inventario en
pesos. Una alerta genérica de «inventario en riesgo» sobre las trece categorías
es ruido; ésta mira solo donde el producto de verdad caduca.

**Y la fecha sola no decide nada.** Doscientas cajas de cerveza a 60 días del
vencimiento no son un problema si se venden ochenta a la semana. Veinte botellas
de espumoso con tres años de vida útil y cero ventas en noventa días sí lo son,
aunque la fecha esté lejísimos. La cuenta que manda es **stock contra demanda
dentro de la vida útil que queda**, y esa resta es la que ningún ERP hace.

Cuando se hace, aparecen dos problemas distintos que hay que tratar distinto:
producto con fecha encima, que se saca con precio esta semana, y producto muerto
con años por delante, que no es un tema de vencimientos sino de surtido y que se
negocia con el proveedor mientras todavía tiene valor.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.formatters import *
from utils import datos, estado, filtros, gerencia, operacion

# Las ventanas con las que razona una bodega de licores. 30 días es «sale esta
# semana o se pierde»; 90 todavía alcanza para armar una promoción y que el
# vendedor la trabaje; más de 180 ya no es un problema de fecha, es de surtido.
VENTANAS = [(30, "Menos de 30 días"), (60, "31 a 60 días"), (90, "61 a 90 días"),
            (180, "91 a 180 días"), (10 ** 6, "Más de 180 días")]

# Los tres descuentos que se negocian de verdad en el canal. Por debajo del 20%
# el bar no cambia su pedido; por encima del 40% el producto queda marcado y la
# cuenta no vuelve a pagar lista.
DESCUENTOS = (0.20, 0.30, 0.40)

# Un lote sin una sola unidad vendida en noventa días no tiene fecha de consumo:
# tiene fecha de caducidad. Se le asignan diez años —fuera de cualquier vida útil
# real— para que aparezca arriba de todo en la gráfica en vez de desaparecer por
# dividir entre cero, que es lo que pasaba cuando este campo quedaba en nulo.
SIN_CONSUMO = 3650

COLOR_ACCION = {
    "Liquidar ya": "#8B1E1E",
    "Promoción dirigida": ACENTO,
    "Canje con el proveedor": "#2B7A9B",
    "Liquidación programada": "#B5762F",
    "Empujar al canal": "#2f7a48",
}


def _lotes() -> pd.DataFrame:
    """El lote, con su proveedor y su precio de lista pegados.

    El lote solo trae costo, y con costo no se decide un descuento: hace falta
    el precio al que se le factura al establecimiento (lista Classic) para saber
    cuánto se recupera. Y hace falta saber si el proveedor factura en pesos con
    representación local —hay con quién sentarse a negociar un canje— o si es
    importación directa en dólares, donde la mercancía ya se nacionalizó, ya se
    pagó el arancel y no vuelve a manos de nadie.
    """
    l = gerencia.lotes().copy()
    cat = datos.catalogo()[["sku", "proveedor", "precio_classic"]]
    prov = operacion.proveedores()[["proveedor", "nacional", "moneda"]]
    l = l.merge(cat, on="sku", how="left").merge(prov, on="proveedor", how="left")
    l["nacional"] = l["nacional"].fillna(False).astype(bool)
    l["moneda"] = l["moneda"].fillna("COP")
    l["precio_classic"] = pd.to_numeric(l["precio_classic"], errors="coerce").fillna(0)

    # El filtro global habla de ciudades y la tabla de lotes habla de bodegas.
    # Son la misma cosa (Bogotá y Medellín); sin este alias el filtro no muerde.
    l["ciudad"] = l["bodega"]

    dias = l["unidades"] / l["demanda_dia"].replace(0, np.nan)
    l["dias_consumo"] = dias.fillna(SIN_CONSUMO).clip(upper=SIN_CONSUMO)
    l["alcanza"] = l["dias_consumo"] <= l["dias_para_vencer"]
    l["margen_pct"] = np.where(
        l["precio_classic"] > 0,
        (l["precio_classic"] - l["costo_unit"]) / l["precio_classic"] * 100, 0)
    l["ventana"] = pd.cut(l["dias_para_vencer"], [-1] + [v[0] for v in VENTANAS],
                          labels=[v[1] for v in VENTANAS])
    return l


def _canal_por_categoria(pv: pd.DataFrame):
    """Dónde rota de verdad cada categoría, medido dentro del establecimiento.

    Se usa la mediana y no el promedio: un solo restaurante con una rotación
    atípica mueve el promedio y manda el producto al canal equivocado. Y se
    exigen al menos dos cuentas con venta, porque un caso aislado no es un canal.
    """
    d = pv[pv["rotacion_mes"] > 0]
    if d.empty:
        return {}, d
    g = d.groupby(["categoria", "canal"], observed=True).agg(
        rot=("rotacion_mes", "median"), cuentas=("cuenta_id", "nunique")).reset_index()
    g = g[g["cuentas"] >= 2]
    if g.empty:
        return {}, g
    top = g.sort_values("rot", ascending=False).groupby("categoria").head(1)
    return dict(zip(top["categoria"], top["canal"])), top


def _accion(r, canal: str):
    """Qué se hace con este lote. El orden de las reglas es la decisión.

    Primero manda el reloj: con menos de treinta días no hay tiempo de armar
    nada, solo de poner precio. Entre treinta y noventa sí alcanza a trabajarse
    con el equipo comercial. Y solo cuando la fecha está lejos tiene sentido la
    conversación con el proveedor, porque un canje se negocia con producto que
    todavía le sirve a alguien, no con saldos de dos semanas.
    """
    if r["en_riesgo_u"] <= 0:
        return "Sin acción", "la demanda lo consume antes de la fecha"
    if r["dias_para_vencer"] <= 30:
        return "Liquidar ya", "no queda tiempo para nada que no sea precio"
    if r["dias_para_vencer"] <= 90:
        return "Promoción dirigida", f"con descuento y empujado a {canal}"
    if r["demanda_dia"] <= 0 and r["nacional"]:
        return "Canje con el proveedor", "factura en pesos: hay con quién sentarse"
    if r["demanda_dia"] <= 0:
        return "Liquidación programada", f"importado en {r['moneda']}: no se devuelve"
    return "Empujar al canal", f"{canal} es donde rota esta categoría"


def _fecha(d) -> str:
    """dd mmm aaaa en español: el locale del servidor no es de fiar."""
    try:
        return f"{d.day} {MESES_ES[d.month - 1]} {d.year}"
    except (AttributeError, TypeError, ValueError):
        return "—"


def render():
    st.markdown(HEADER_CSS, unsafe_allow_html=True)
    st.markdown(encabezado(
        "Vencimientos y producto detenido",
        "Qué hay en bodega que caduca, cuándo, cuánto vale y qué se hace con ello",
        "¿Qué hay que sacar ya?"), unsafe_allow_html=True)
    filtros.encabezado_filtro()

    l = filtros.aplicar(_lotes(), col_mes=None)
    if l.empty:
        st.info("No hay lotes con vida útil en la bodega seleccionada.")
        return

    pv = filtros.aplicar(gerencia.punto_venta(), col_mes=None)
    canal_cat, rot = _canal_por_categoria(pv)

    inv = operacion.inventario().copy()
    inv["ciudad"] = inv["bodega"]
    inv = filtros.aplicar(inv, col_mes=None)
    perecederas = sorted(l["categoria"].unique().tolist())
    val_total = float(inv["valor_inventario"].sum())
    val_pere = float(inv.loc[inv["categoria"].isin(perecederas), "valor_inventario"].sum())

    riesgo = l[l["en_riesgo_u"] > 0]
    noventa = l[l["dias_para_vencer"] <= 90]
    muertos = l[l["demanda_dia"] <= 0]
    riesgo_total = float(l["en_riesgo"].sum())
    rec30 = float((riesgo["precio_classic"] * 0.70 * riesgo["en_riesgo_u"]).sum())

    k = st.columns(4, gap="small")
    k[0].markdown(kpi(
        "Plata en riesgo de vencerse", cop(riesgo_total, 0),
        f"{num(len(riesgo))} lotes de {num(len(l))}", False, "⏳",
        "Unidades que la demanda de hoy no alcanza a vender antes de la fecha. "
        "No es el valor del lote: es la parte que sobra.",
        f"{pct(riesgo_total / max(val_pere, 1) * 100)} del inventario que caduca"),
        unsafe_allow_html=True)
    k[1].markdown(kpi(
        "Vence en 90 días", cop(noventa["valor"].sum(), 0),
        f"{num(len(noventa))} lotes · {cop(noventa['en_riesgo'].sum(), 0)} sin salida",
        False, "📆",
        "Valor completo de los lotes con fecha encima. La mayoría se vende "
        "sola; lo que importa es el segundo número."), unsafe_allow_html=True)
    k[2].markdown(kpi(
        "Sin una sola venta en 90 días", num(len(muertos)),
        f"{cop(muertos['en_riesgo'].sum(), 0)} detenidos", False, "📦",
        "Lotes con demanda cero. Se vencen igual, solo que más tarde y sin que "
        "nadie los esté mirando.",
        "Aquí está la plata grande, no en la fecha próxima"), unsafe_allow_html=True)
    k[3].markdown(kpi(
        "Recuperable al 30% de descuento", cop(rec30, 0),
        f"contra {cop(0)} si se vence", True, "🏷️",
        "Lo que entra si se coloca con descuento lo que hoy no tiene salida. "
        "El costo ya está pagado: la comparación no es contra el margen."),
        unsafe_allow_html=True)

    st.markdown(espacio(16), unsafe_allow_html=True)
    st.markdown(panel(
        "Por qué esta pantalla mira cinco categorías y no trece",
        f"De {cop(val_total, 0)} de inventario, solo <b>{cop(val_pere, 0)}</b> "
        f"({pct(val_pere / max(val_total, 1) * 100)}) puede caducar: "
        f"{', '.join(perecederas).lower()}. "
        f"El resto —whisky, ron, vodka, tequila, ginebra, aguardiente, brandy— "
        f"<b>no se vence</b>: una caja de whisky olvidada tres años en la bodega "
        f"amarra capital y ocupa metro cuadrado, pero se vende igual de bien. "
        f"Por eso una alerta de «inventario en riesgo» sobre todo el catálogo no "
        f"la lee nadie: el 80% de lo que señala no es un riesgo, es una compra "
        f"grande. Mezclar las dos cosas es lo que hace que se apague la alerta.",
        "🥃", "azul"), unsafe_allow_html=True)

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── La línea de tiempo ──────────────────────────────────────────────────
    st.markdown('<div class="ky-sub">Qué se vence y cuándo</div>',
                unsafe_allow_html=True)
    etiquetas = [v[1] for v in VENTANAS]
    g = l.groupby("ventana", observed=False).agg(
        lotes=("lote", "size"), valor=("valor", "sum"),
        riesgo=("en_riesgo", "sum"), unidades=("unidades", "sum"),
        sobran=("en_riesgo_u", "sum")).reindex(etiquetas).fillna(0).reset_index()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=g["ventana"], y=g["valor"] / 1e6, name="Valor del lote en bodega",
        marker_color=PALIDO,
        customdata=np.stack([g["lotes"], g["unidades"]], -1),
        hovertemplate="%{x}<br>%{customdata[0]:.0f} lotes · "
                      "%{customdata[1]:,.0f} unidades<br>"
                      "Valor: $%{y:,.1f} M<extra></extra>"))
    fig.add_trace(go.Bar(
        x=g["ventana"], y=g["riesgo"] / 1e6, name="Lo que no alcanza a venderse",
        marker_color=ACENTO,
        customdata=np.stack([g["sobran"]], -1),
        hovertemplate="%{x}<br>%{customdata[0]:,.0f} unidades sobrando<br>"
                      "En riesgo: $%{y:,.1f} M<extra></extra>"))
    fig.update_layout(barmode="overlay")
    fig.update_yaxes(title="Millones de pesos", tickprefix="$", ticksuffix=" M")
    st.plotly_chart(light(fig, 320), use_container_width=True)
    st.caption(
        "La barra clara es el valor completo del lote; la coral, la parte que la "
        "demanda no alcanza a consumir antes de la fecha. **Cuando las dos barras "
        "casi coinciden es producto detenido, no producto que se vence pronto**: "
        "el filtro de ciudad aplica a la bodega, y canal y vendedor no filtran "
        "inventario —una caja en bodega todavía no es de nadie— pero sí filtran "
        "el cuadro de rotación de más abajo.")

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── El cálculo que importa: vida útil contra demanda ────────────────────
    st.markdown('<div class="ky-sub">Cuánto tarda en venderse contra cuánto le queda</div>',
                unsafe_allow_html=True)
    fig2 = go.Figure()
    tope = float(max(l["dias_para_vencer"].max(), l["dias_consumo"].max()))
    fig2.add_trace(go.Scatter(
        x=[10, tope], y=[10, tope], mode="lines", name="Justo alcanza",
        line=dict(color=CLARO, width=1.2, dash="dot"), hoverinfo="skip"))
    for i, c in enumerate(perecederas):
        d = l[l["categoria"] == c]
        if d.empty:
            continue
        fig2.add_trace(go.Scatter(
            x=d["dias_para_vencer"], y=d["dias_consumo"], mode="markers", name=c,
            marker=dict(size=np.clip(np.sqrt(d["valor"]) / 90, 7, 34),
                        color=PALETTE[i % len(PALETTE)], opacity=.72,
                        line=dict(width=1, color="#fff")),
            customdata=np.stack([d["producto"], d["bodega"], d["unidades"],
                                 d["demanda_dia"], d["en_riesgo"]], -1),
            hovertemplate="<b>%{customdata[0]}</b> · %{customdata[1]}"
                          "<br>%{customdata[2]:,.0f} unidades · "
                          "%{customdata[3]:.2f} al día"
                          "<br>Vence en %{x:,.0f} días · tarda %{y:,.0f} en venderse"
                          "<br>En riesgo: %{customdata[4]:,.0f}<extra></extra>"))
    fig2.update_xaxes(title="Días que le quedan de vida útil", type="log")
    fig2.update_yaxes(title="Días que tarda en venderse al ritmo de hoy", type="log")
    f2 = light(fig2, 440)
    f2.update_layout(hovermode="closest")
    st.plotly_chart(f2, use_container_width=True)
    st.caption(
        f"**Todo lo que está por encima de la línea no alcanza a venderse.** El "
        f"tamaño del círculo es el valor del lote. La banda pegada al techo son "
        f"los {num(len(muertos))} lotes sin una sola venta en noventa días: no "
        f"tienen fecha de consumo, solo fecha de caducidad. Los dos ejes son "
        f"logarítmicos porque conviven lotes de tres semanas con lotes de siete "
        f"años, y en escala lineal los primeros se aplastan contra el margen.")

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── Dónde está concentrado ──────────────────────────────────────────────
    st.markdown('<div class="ky-sub">En qué categorías está la plata</div>',
                unsafe_allow_html=True)
    cg = l.groupby("categoria", observed=True).agg(
        lotes=("lote", "size"), valor=("valor", "sum"), riesgo=("en_riesgo", "sum"),
        sobran=("en_riesgo_u", "sum")).reset_index().sort_values("riesgo", ascending=False)
    cg["expuesto"] = cg["riesgo"] / cg["valor"].replace(0, np.nan) * 100
    tc = pd.DataFrame({
        "Categoría": cg["categoria"],
        "Lotes": cg["lotes"].astype(int),
        "Valor en bodega": cg["valor"].map(lambda x: cop(x, 0)),
        "Unidades sin salida": cg["sobran"].astype(int),
        "Plata en riesgo": cg["riesgo"].map(lambda x: cop(x, 0)),
        "% del lote expuesto": cg["expuesto"].map(lambda x: pct(x)),
        "Canal donde rota": [canal_cat.get(c, "sin lectura de PDV") for c in cg["categoria"]],
    })
    st.dataframe(tc, hide_index=True, width="stretch")

    peor_cat = cg.iloc[0]
    canal_peor = canal_cat.get(peor_cat["categoria"], "el canal de mayor rotación")
    st.caption(md(
        f"**{peor_cat['categoria']}** concentra {cop(peor_cat['riesgo'], 0)}, el "
        f"{pct(peor_cat['riesgo'] / max(riesgo_total, 1) * 100)} de todo el riesgo. "
        f"La última columna sale de la rotación medida dentro del "
        f"establecimiento, no de lo que se le factura: es el canal al que hay que "
        f"empujar el producto antes de tocar el precio."))

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── Los lotes donde la demanda no alcanza ───────────────────────────────
    st.markdown('<div class="ky-sub">Los lotes donde la demanda no alcanza</div>',
                unsafe_allow_html=True)
    if riesgo.empty:
        # Con la bodega de Medellín filtrada esto pasa de verdad, y sin nombrar
        # el filtro el mensaje se lee como una pantalla rota en vez de como una
        # buena noticia acotada.
        alcance = filtros.resumen() if filtros.activo() else "toda la operación"
        st.success(
            f"En {alcance} ningún lote sobra: la demanda "
            f"consume todo antes de la fecha. Es el estado que se busca, y se "
            f"revisa cada lunes porque una caída de rotación lo cambia en dos "
            f"semanas.")
        return

    det = riesgo.copy()
    acciones = [_accion(r, canal_cat.get(r["categoria"], "el canal que más rota"))
                for _, r in det.iterrows()]
    det["accion"] = [a for a, _ in acciones]
    det["detalle"] = [d for _, d in acciones]
    det["rec30"] = det["precio_classic"] * 0.70 * det["en_riesgo_u"]
    det = det.sort_values("en_riesgo", ascending=False)

    top = det.head(18)
    tt = pd.DataFrame({
        "Lote": top["lote"],
        "Producto": top["producto"],
        "Bodega": top["bodega"],
        "Vence": top["vence"].map(_fecha),
        "Días": top["dias_para_vencer"].astype(int),
        "En bodega": top["unidades"].astype(int),
        "Sobran": top["en_riesgo_u"].astype(int),
        "Plata en riesgo": top["en_riesgo"].map(lambda x: cop(x, 0)),
        "Qué hacer": top["accion"],
        "Por qué": top["detalle"],
    })
    st.dataframe(tt, hide_index=True, width="stretch")
    st.caption(
        f"Ordenado por plata, no por fecha. Son los {num(len(top))} primeros de "
        f"{num(len(det))} lotes con sobrante; la columna «Sobran» es la resta que "
        f"no hace el ERP: unidades en bodega menos lo que la demanda alcanza a "
        f"consumir antes del vencimiento.")

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── El plan por acción ──────────────────────────────────────────────────
    st.markdown('<div class="ky-sub">El plan, agrupado por lo que hay que hacer</div>',
                unsafe_allow_html=True)
    ag = det.groupby("accion", observed=True).agg(
        lotes=("lote", "size"), unidades=("en_riesgo_u", "sum"),
        riesgo=("en_riesgo", "sum"), rec=("rec30", "sum")).reset_index()
    ag = ag.sort_values("riesgo", ascending=False)
    cols = st.columns(min(len(ag), 3), gap="small")
    for i, (_, a) in enumerate(ag.iterrows()):
        color = COLOR_ACCION.get(a["accion"], CLARO)
        cols[i % len(cols)].markdown(f"""
        <div style="border:1px solid {PALIDO};border-left:4px solid {color};
             border-radius:6px;padding:14px 16px;background:#fff;margin-bottom:12px">
          <div style="font-size:9.5px;font-weight:800;letter-spacing:.12em;
               text-transform:uppercase;color:{color}">{a['accion']}</div>
          <div style="font-size:23px;font-weight:800;color:{TINTA};line-height:1.2;
               margin:4px 0 2px">{cop(a['riesgo'], 0)}</div>
          <div style="font-size:11.5px;color:{CLARO}">
            {int(a['lotes'])} lotes · {int(a['unidades'])} unidades<br>
            recupera {cop(a['rec'], 0)} al 30% de descuento</div>
        </div>""", unsafe_allow_html=True)

    st.markdown(espacio(10), unsafe_allow_html=True)

    # ── La aritmética del descuento ─────────────────────────────────────────
    st.markdown('<div class="ky-sub">Cuánto se recupera con descuento</div>',
                unsafe_allow_html=True)
    colocacion = st.select_slider(
        "Qué porcentaje del sobrante se logra colocar de verdad",
        options=[40, 60, 80, 100], value=60, key="vc_coloca",
        format_func=lambda v: f"{v}%")

    costo_hundido = float(det["en_riesgo"].sum())
    lista = float((det["precio_classic"] * det["en_riesgo_u"]).sum())
    # El punto donde el descuento se come el margen entero. Ponderado por valor,
    # no promedio simple: la cerveza tiene 26% de margen y los accesorios 50%, y
    # un promedio simple da un umbral que no aplica a ninguna de las dos.
    equilibrio = (lista - costo_hundido) / max(lista, 1) * 100

    filas = []
    for d in DESCUENTOS:
        recupera = lista * (1 - d) * colocacion / 100
        filas.append({
            "Descuento": pct(d * 100, 0),
            "Precio de venta": cop(lista * (1 - d), 0),
            f"Entra en caja (coloca {colocacion}%)": cop(recupera, 0),
            "Contra el costo": signo((recupera - costo_hundido) / max(costo_hundido, 1) * 100, 0),
            "Recupera": pct(recupera / max(costo_hundido, 1) * 100, 0),
        })
    st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch")

    st.markdown(panel(
        "A partir de qué descuento conviene, y contra qué se compara",
        f"El costo de ese sobrante —<b>{cop(costo_hundido, 0)}</b>— ya está "
        f"pagado. No se recupera dejándolo en la bodega: si se vence, entra "
        f"{cop(0)}. Por eso la comparación correcta no es «¿me deja margen?» "
        f"sino «¿cuánto de esa plata vuelve?».<br><br>"
        f"<b>Hasta {pct(equilibrio, 0)} de descuento la venta todavía deja "
        f"margen positivo</b>: es el margen ponderado real de estos lotes, y por "
        f"debajo de ese umbral el descuento no cuesta nada, solo adelanta la "
        f"venta. Entre {pct(equilibrio, 0)} y 40% se vende bajo costo, pero "
        f"entra entre el 80% y el 95% de la plata en vez de cero — y esa es una "
        f"decisión de caja, no de rentabilidad.<br><br>"
        f"Dos advertencias que cambian el número: el descuento se aplica "
        f"<b>solo a las unidades que sobran</b>, nunca al lote completo, porque "
        f"lo demás se vende a precio de lista sin ayuda; y el 20% no mueve "
        f"producto que lleva noventa días sin una sola venta — ahí el descuento "
        f"que limpia es el de 40%, o directamente el canje. El costo verdadero "
        f"de una liquidación no es el margen perdido: es que la cuenta aprende "
        f"el precio nuevo y tarda dos trimestres en volver a pagar lista.",
        "🏷️", "naranja"), unsafe_allow_html=True)

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── Sacarlo de la pantalla y ponerlo en manos de alguien ────────────────
    st.markdown('<div class="ky-sub">Asignar la salida</div>', unsafe_allow_html=True)
    ya = estado.decisiones()
    opciones = [f"{r['lote']} · {r['producto']} · {cop(r['en_riesgo'], 0)} · "
                f"{int(r['dias_para_vencer'])} días" for _, r in det.head(25).iterrows()]
    c = st.columns([3, 2, 2], gap="small")
    elegido = c[0].selectbox("Lote", opciones, key="vc_lote")
    fila = det.head(25).iloc[opciones.index(elegido)]
    accion = c[1].selectbox(
        "Acción", [fila["accion"]] + [a for a in COLOR_ACCION if a != fila["accion"]],
        key="vc_accion")
    quien = c[2].text_input("Responsable", value="Jefe de bodega", key="vc_quien")

    clave = f"venc:{fila['lote']}"
    if clave in ya:
        d = ya[clave]
        st.markdown(
            chip(f"Asignado a {d['quien']} · {d['cuando']}", "ok") +
            chip(d.get("nota", ""), "neutro"), unsafe_allow_html=True)
    elif st.button("Registrar y abrir compromiso", type="primary", key="vc_ok"):
        # Toda salida de producto por vencimiento genera un compromiso con dueño
        # y fecha. Sin eso el lote vuelve a aparecer en esta misma pantalla el
        # mes entrante, con menos días y menos plata recuperable.
        estado.decidir(clave, "Decidida", quien,
                       f"{accion} — {fila['producto']} ({fila['lote']}), "
                       f"{int(fila['en_riesgo_u'])} unidades por {cop(fila['en_riesgo'], 0)}",
                       float(fila["en_riesgo"]),
                       vence_dias=max(7, int(fila["dias_para_vencer"]) // 2))
        st.rerun()

    st.markdown(espacio(10), unsafe_allow_html=True)
    urgentes = det[det["dias_para_vencer"] <= 60]
    st.markdown(panel(
        "La conclusión",
        f"Con fecha encima —sesenta días o menos— hay "
        f"<b>{num(len(urgentes))} lotes por {cop(urgentes['en_riesgo'].sum(), 0)}</b>. "
        f"Eso es lo que hay que sacar esta semana y cabe en una promoción de "
        f"cerveza y mixers, que es donde vive la vida útil corta.<br><br>"
        f"Pero el hallazgo grande está en el otro lado del calendario: "
        f"<b>{cop(muertos['en_riesgo'].sum(), 0)} en {num(len(muertos))} lotes sin "
        f"una sola venta en noventa días</b>, casi todo vino y espumosos con años "
        f"de vida útil por delante. Ese producto no tiene un problema de "
        f"vencimiento: tiene un problema de surtido, y hoy nadie lo ve porque "
        f"todos los reportes de caducidad ordenan por fecha y lo mandan al final "
        f"de la lista. Cuando llegue al principio va a valer la mitad.<br><br>"
        f"La decisión de la semana no es cuánto descuento dar: es <b>con cuáles "
        f"de esos lotes todavía se puede negociar un canje</b> mientras le sirven "
        f"al proveedor, y cuáles ya solo salen con precio.",
        "🧭", "alerta"), unsafe_allow_html=True)
