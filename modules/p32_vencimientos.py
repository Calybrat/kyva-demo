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
vencimiento no son un problema si se venden ochenta a la semana. La cuenta que
manda es **stock contra demanda dentro de la vida útil que queda**, y esa resta
es la que ningún ERP hace.

**Pero el resultado de esa resta son dos problemas distintos, y sumarlos es
mentir.** Un lote de cerveza que sobra y vence en siete semanas es plata que se
pierde este trimestre. Doce botellas de champaña de prestigio que llevan
noventa días sin salir pero vencen en 2029 no se van a vencer: son capital
dormido y un error de surtido, y hoy valen lo que costaron. Meter las dos cosas
bajo un solo titular de «plata en riesgo de vencerse» infla el número entre diez
y treinta veces y lo vuelve indefendible en el primer comité. Por eso la
pantalla parte por la línea de los 180 días —el mismo corte que ya usaba la
línea de tiempo— y da dos números con dos nombres:

  · **Se vence antes de venderse**: sobrante en lotes con seis meses o menos de
    vida útil. Es el número de merma, y cae donde tiene que caer para el sector
    (entre 0,5% y 2% del inventario perecedero).
  · **Detenido, con años por delante**: sobrante en lotes sin demanda y con la
    fecha lejos. Es surtido y capital de trabajo, se negocia con el proveedor
    mientras la mercancía todavía le sirve a alguien, y es plata de verdad —
    pero no es merma y no se presenta como merma.
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

# La línea que separa los dos problemas. Sale de la última ventana de arriba, no
# de un número redondo elegido aparte: por debajo la fecha manda la decisión, por
# encima la fecha es irrelevante y lo que manda es que el producto no rota.
HORIZONTE = 180

# Los tres descuentos que se negocian de verdad en el canal. Por debajo del 20%
# el bar no cambia su pedido; por encima del 40% el producto queda marcado y la
# cuenta no vuelve a pagar lista.
DESCUENTOS = (0.20, 0.30, 0.40)

# Qué porcentaje del sobrante se supone colocado. Nadie coloca el 100% de un
# saldo: el supuesto por defecto es 60% y es el MISMO en las tarjetas, en el KPI
# y en el cuadro. Tres bloques con tres supuestos distintos del mismo descuento
# es la forma más rápida de perder una demostración.
COLOCACION = [40, 60, 80, 100]
COLOCACION_DEF = 60

# Un lote sin una sola unidad vendida en noventa días no tiene fecha de consumo:
# tiene fecha de caducidad. Se le asignan diez años —fuera de cualquier vida útil
# real— para que aparezca arriba de todo en la gráfica en vez de desaparecer por
# dividir entre cero, que es lo que pasaba cuando este campo quedaba en nulo.
SIN_CONSUMO = 3650

# Proveedores que no son un proveedor: son la bolsa donde el maestro mete a los
# importadores chicos. No hay una contraparte, no hay un ejecutivo de cuenta y no
# hay con quién negociar un canje. Recomendarlo sería mandar al jefe de bodega a
# llamar a un nombre que no existe.
AGREGADOS = {"Otros importadores"}

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
    l["proveedor"] = l["proveedor"].fillna("sin proveedor en el maestro")
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
    l["problema"] = np.where(l["dias_para_vencer"] <= HORIZONTE,
                             "Fecha encima", "Capital detenido")
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

    Primero el caso sin salida: con menos de treinta días no hay tiempo de armar
    nada, solo de poner precio.

    Después **la demanda, antes que el reloj**. Un lote que lleva noventa días
    sin vender una sola unidad no se arregla con una promoción, y da igual si le
    quedan sesenta días o seis años: la promoción es precisamente lo que este
    mismo módulo dice que no funciona ahí. Mandarlo a «promoción dirigida»
    porque la fecha está cerca es contradecirse dentro de la misma pantalla.

    Y solo con la fecha lejos tiene sentido la conversación con el proveedor,
    porque un canje se negocia con producto que todavía le sirve a alguien, no
    con saldos de dos semanas — y se negocia con una contraparte real, no con la
    bolsa de «otros importadores» del maestro.
    """
    if r["en_riesgo_u"] <= 0:
        return "Sin acción", "la demanda lo consume antes de la fecha"
    if r["dias_para_vencer"] <= 30:
        return "Liquidar ya", "no queda tiempo para nada que no sea precio"
    if r["demanda_dia"] <= 0:
        if r["dias_para_vencer"] <= 90:
            return "Liquidar ya", "cero ventas en 90 días y la fecha encima: solo precio"
        if r["proveedor"] in AGREGADOS:
            return ("Liquidación programada",
                    "«otros importadores» no es una contraparte: no hay con quién sentarse")
        if r["nacional"]:
            return "Canje con el proveedor", "factura en pesos: hay con quién sentarse"
        return "Liquidación programada", f"importado en {r['moneda']}: no se devuelve"
    if r["dias_para_vencer"] <= 90:
        return "Promoción dirigida", f"con descuento y empujado a {canal}"
    return "Empujar al canal", f"{canal} es donde rota esta categoría"


def _lista(nombres) -> str:
    """Enumera categorías sin producir «champaña y espumosos y vino».

    Dos nombres del maestro ya traen una «y» adentro —«Champaña y espumosos»,
    «Mixers y aguas»—, así que unirlos con «y» arma un trabalenguas. Y cuando
    una categoría se lleva el grueso, nombrar la segunda estorba más de lo que
    informa: la frase queda «casi todo cerveza», que es lo que pasa de verdad.
    """
    n = list(nombres)
    if not n:
        return ""
    if len(n) == 1:
        return n[0]
    sep = ", y " if any(" y " in x for x in n) else " y "
    return sep.join(n)


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

    # Qué categorías caducan NO depende del filtro: si Medellín no tuviera un
    # solo lote de vino, el vino seguiría siendo perecedero. La lista sale del
    # universo completo; `l` es la que va filtrada.
    universo = _lotes()
    perecederas = sorted(universo["categoria"].unique().tolist())

    l = filtros.aplicar(universo, col_mes=None)
    if l.empty:
        st.info("No hay lotes con vida útil en la bodega seleccionada.")
        return

    # El canal donde rota una categoría se mide contra TODOS los canales. Si se
    # deja que el filtro de canal muerda aquí, con «Discotecas» puesto todas las
    # categorías responden «Discotecas» y la recomendación se vuelve un eco del
    # filtro. Ciudad y vendedor sí aplican; el canal se esconde renombrando la
    # columna antes de pasar por el filtro global.
    pv = gerencia.punto_venta().rename(columns={"canal": "canal_pdv"})
    pv = filtros.aplicar(pv, col_mes=None).rename(columns={"canal_pdv": "canal"})
    canal_cat, _ = _canal_por_categoria(pv)

    inv = operacion.inventario().copy()
    inv["ciudad"] = inv["bodega"]
    inv = filtros.aplicar(inv, col_mes=None)
    cats_inv = sorted(inv["categoria"].unique().tolist())
    no_perecederas = [c for c in cats_inv if c not in perecederas]
    val_total = float(inv["valor_inventario"].sum())
    val_pere = float(inv.loc[inv["categoria"].isin(perecederas), "valor_inventario"].sum())

    riesgo = l[l["en_riesgo_u"] > 0]
    fecha = riesgo[riesgo["dias_para_vencer"] <= HORIZONTE]
    detenido = riesgo[riesgo["dias_para_vencer"] > HORIZONTE]
    noventa = l[l["dias_para_vencer"] <= 90]
    muertos = l[l["demanda_dia"] <= 0]
    riesgo_total = float(riesgo["en_riesgo"].sum())
    venc_total = float(fecha["en_riesgo"].sum())
    det_total = float(detenido["en_riesgo"].sum())

    # El supuesto de colocación se lee del estado del slider de más abajo, no de
    # un 100% implícito: así el KPI, las tarjetas de plan y el cuadro del
    # descuento dicen el mismo número del mismo escenario.
    coloca = int(st.session_state.get("vc_coloca", COLOCACION_DEF))
    lista_riesgo = float((riesgo["precio_classic"] * riesgo["en_riesgo_u"]).sum())
    rec30 = lista_riesgo * (1 - DESCUENTOS[1]) * coloca / 100

    k = st.columns(4, gap="small")
    k[0].markdown(kpi(
        "Se vence antes de venderse", cop(venc_total),
        (f"{num(len(fecha))} lotes con {HORIZONTE} días o menos de vida útil"
         if len(fecha) else "ningún lote con fecha encima tiene sobrante"),
        venc_total <= 0, "⏳",
        "Unidades que la demanda de hoy no alcanza a vender antes de la fecha, "
        "contadas solo donde la fecha manda: seis meses o menos de vida útil. "
        "No es el valor del lote, es la parte que sobra.",
        (f"{pct(venc_total / max(val_pere, 1) * 100)} del inventario que caduca · "
         f"en distribución de bebidas lo normal va de 0,5% a 2%" if venc_total > 0
         else "cero merma proyectada · en distribución de bebidas lo normal va "
              "de 0,5% a 2% del inventario que caduca")),
        unsafe_allow_html=True)
    k[1].markdown(kpi(
        "Vence en 90 días", cop(noventa["valor"].sum(), 0),
        (f"{num(len(noventa))} lotes · {cop(noventa['en_riesgo'].sum())} sin salida"
         if float(noventa["en_riesgo"].sum()) > 0 else
         f"{num(len(noventa))} lotes, y la demanda alcanza a consumirlos todos"
         if len(noventa) else "ningún lote entra a la ventana de 90 días"),
        float(noventa["en_riesgo"].sum()) <= 0, "📆",
        "Valor completo de los lotes con fecha encima. La mayoría se vende "
        "sola; lo que importa es el segundo número."), unsafe_allow_html=True)
    k[2].markdown(kpi(
        "Detenido, con años por delante", cop(det_total, 0),
        (f"{num(len(detenido))} lotes · mediana de "
         f"{num(detenido['en_riesgo_u'].median())} unidades cada uno"
         if len(detenido) else "ningún lote detenido: todo tiene demanda"),
        det_total <= 0, "📦",
        "Sobrante en lotes sin una sola venta en noventa días y con más de seis "
        "meses de vida útil. Se vencen, sí, pero en dos o tres años.",
        ("No es merma: es surtido y capital dormido. Son pocas botellas caras, "
         "no estibas" if det_total > 0 else "")), unsafe_allow_html=True)
    k[3].markdown(kpi(
        "Recuperable al 30% de descuento", cop(rec30, 0),
        (f"{pct(rec30 / max(riesgo_total, 1) * 100, 0)} del costo hundido, "
         f"contra {cop(0)} si se vence" if riesgo_total > 0
         else "no hay sobrante que colocar"),
        True, "🏷️",
        "Lo que entra si se coloca con descuento lo que hoy no tiene salida. "
        "El costo ya está pagado: la comparación no es contra el margen.",
        f"supone colocar el {coloca}% del sobrante, el mismo supuesto del cuadro "
        f"de más abajo"), unsafe_allow_html=True)

    if riesgo.empty:
        alcance = filtros.resumen() if filtros.activo() else "toda la operación"
        st.markdown(espacio(16), unsafe_allow_html=True)
        st.markdown(panel(
            "Ningún lote sobra, y eso es el resultado que se busca",
            f"En {alcance} hay <b>{num(len(l))} lotes con vida útil</b> en bodega "
            f"por {cop(l['valor'].sum(), 0)}, y la demanda de hoy los consume "
            f"todos antes de la fecha. Los cuatro números de arriba están en cero "
            f"porque no hay nada que sacar, no porque falte información.<br><br>"
            f"Se revisa igual cada lunes: este estado lo cambia una caída de "
            f"rotación en dos semanas, y los {num(len(noventa))} lotes que ya "
            f"entraron a la ventana de noventa días "
            f"({cop(noventa['valor'].sum(), 0)} en bodega) son los que hay que "
            f"mirar primero cuando eso pase.",
            "✅", "ok"), unsafe_allow_html=True)

    st.markdown(espacio(16), unsafe_allow_html=True)
    st.markdown(panel(
        f"Por qué esta pantalla mira {num(len(perecederas))} categorías "
        f"y no {num(len(cats_inv))}",
        f"De {cop(val_total, 0)} de inventario, solo <b>{cop(val_pere, 0)}</b> "
        f"({pct(val_pere / max(val_total, 1) * 100)}) puede caducar: "
        f"{', '.join(perecederas).lower()}. "
        f"El resto —{', '.join(no_perecederas).lower()}— "
        f"<b>no se vence</b>: una caja de whisky olvidada tres años en la bodega "
        f"amarra capital y ocupa metro cuadrado, pero se vende igual de bien. "
        f"Por eso una alerta de «inventario en riesgo» sobre todo el catálogo no "
        f"la lee nadie: la mayor parte de lo que señala no es un riesgo, es una "
        f"compra grande. Mezclar las dos cosas es lo que hace que se apague la "
        f"alerta.",
        "🥃", "azul"), unsafe_allow_html=True)

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── Cómo cuadra con las otras dos pantallas que cuentan lo mismo ─────────
    # Tres pantallas tocan este inventario con tres definiciones distintas. Si
    # la conciliación no está escrita aquí, en el comité quedan dos cifras con
    # la misma etiqueta y gana la discusión el que hable más duro.
    #
    # Va toda sobre el universo SIN filtrar: el comité y surtido publican la
    # operación completa, y conciliar una cifra filtrada contra una que no lo
    # está es fabricar una tercera discrepancia.
    s = datos.surtido()
    quietas = s[s["unidades_90d"] == 0]
    q_pere = quietas[quietas["categoria"].isin(perecederas)]
    q_resto = quietas[~quietas["categoria"].isin(perecederas)]
    u_riesgo = universo[universo["en_riesgo_u"] > 0]
    u_venc = float(u_riesgo.loc[u_riesgo["dias_para_vencer"] <= HORIZONTE, "en_riesgo"].sum())
    u_critico = float(
        universo.loc[universo["estado"].isin(["Crítico", "Vencido"]), "en_riesgo"].sum())
    u_muertos = int((universo["demanda_dia"] <= 0).sum())
    st.markdown(panel(
        "Por qué este número no es el del comité ni el de surtido",
        (f"<i>Los cuatro números de este bloque son de toda la operación, que es "
         f"como los publican esas dos pantallas; los de arriba sí respetan el "
         f"filtro.</i><br><br>" if filtros.activo() else "") +
        f"<b>El comité del lunes y el centro de decisiones dicen "
        f"{cop(u_critico)}</b> de «inventario en riesgo de vencimiento». Usan "
        f"la definición estrecha: solo lotes en estado Crítico o Vencido, 45 días "
        f"o menos. Es un subconjunto de los <b>{cop(u_venc)}</b> de esta "
        f"pantalla, que estira la ventana hasta {HORIZONTE} días. Los dos números "
        f"son correctos y miden lo mismo con distinto alcance: el de allá sirve "
        f"para «qué firmo esta semana», el de aquí para «qué armo este "
        f"trimestre».<br><br>"
        f"<b>Surtido y rotación dice {num(len(quietas))} referencias sin una "
        f"venta en 90 días por {cop(quietas['valor_stock'].sum(), 0)}</b>. Es la "
        f"misma población, contada sobre las {num(len(cats_inv))} categorías. "
        f"Aquí solo caben las que caducan: {num(len(q_pere))} referencias "
        f"({num(u_muertos)} lotes, porque una referencia se parte en varios "
        f"lotes y bodegas) por {cop(q_pere['valor_stock'].sum(), 0)}. La "
        f"diferencia —{num(len(q_resto))} referencias por "
        f"{cop(q_resto['valor_stock'].sum(), 0)}— es whisky, ron y aguardiente "
        f"quietos: capital dormido de verdad, pero no se vencen y no se atienden "
        f"con una promoción de fecha.",
        "🔗", "azul"), unsafe_allow_html=True)

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
    st.plotly_chart(light(fig, 320), width="stretch", theme=None, config=PLOTLY_CONFIG)
    st.caption(
        "La barra clara es el valor completo del lote; la coral, la parte que la "
        "demanda no alcanza a consumir antes de la fecha. **En la última columna "
        "—más de 180 días— coral no significa que se vaya a vencer: significa "
        "que no rota**, y ése es el otro problema. El filtro de ciudad aplica a "
        "la bodega; canal y vendedor no filtran inventario —una caja en bodega "
        "todavía no es de nadie— pero sí filtran el cuadro de rotación de más "
        "abajo.")

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
    st.plotly_chart(f2, width="stretch", theme=None, config=PLOTLY_CONFIG)
    banda = (f"La banda pegada al techo son los {num(len(muertos))} lotes sin una "
             f"sola venta en noventa días: no tienen fecha de consumo, solo fecha "
             f"de caducidad."
             if len(muertos) else
             "Aquí no hay banda pegada al techo: ningún lote de esta bodega lleva "
             "noventa días sin vender una unidad, así que todos tienen una fecha "
             "de consumo real contra la cual medirse.")
    st.caption(
        f"**Todo lo que está por encima de la línea no alcanza a venderse.** El "
        f"tamaño del círculo es el valor del lote. {banda} Los dos ejes son "
        f"logarítmicos porque conviven lotes de tres semanas con lotes de siete "
        f"años, y en escala lineal los primeros se aplastan contra el margen.")

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── Dónde está concentrado ──────────────────────────────────────────────
    st.markdown('<div class="ky-sub">En qué categorías está la plata</div>',
                unsafe_allow_html=True)
    cg = l.groupby("categoria", observed=True).agg(
        lotes=("lote", "size"), valor=("valor", "sum"), riesgo=("en_riesgo", "sum"),
        sobran=("en_riesgo_u", "sum")).reset_index()
    # Con una bodega donde nada sobra, ordenar por riesgo ordena una columna de
    # ceros y la «peor categoría» sale por accidente del orden alfabético. Si no
    # hay riesgo que repartir, se ordena por lo único que sí distingue: el valor.
    cg = cg.sort_values("riesgo" if riesgo_total > 0 else "valor", ascending=False)
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

    if riesgo_total > 0:
        peor_cat = cg.iloc[0]
        st.caption(md(
            f"**{peor_cat['categoria']}** concentra {cop(peor_cat['riesgo'], 0)}, el "
            f"{pct(peor_cat['riesgo'] / max(riesgo_total, 1) * 100)} de todo el "
            f"sobrante. La última columna sale de la rotación medida dentro del "
            f"establecimiento —contra todos los canales, no contra el que esté "
            f"filtrado— y no de lo que se le factura: es el canal al que hay que "
            f"empujar el producto antes de tocar el precio."))
    else:
        st.caption(md(
            f"Ninguna categoría tiene sobrante: las columnas de riesgo están en "
            f"cero porque la demanda consume los {num(len(l))} lotes antes de la "
            f"fecha, y la tabla va ordenada por valor en bodega. La última "
            f"columna sirve igual: es el canal al que hay que empujar cada "
            f"categoría si la rotación cae."))

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
    det["rec30"] = det["precio_classic"] * (1 - DESCUENTOS[1]) * det["en_riesgo_u"] * coloca / 100
    # Primero lo que tiene fecha encima y después lo detenido, y dentro de cada
    # bloque por plata. Ordenar solo por plata pone arriba una champaña que vence
    # en tres años, y el gerente lee la primera fila como si se estuviera
    # venciendo mañana.
    det["_orden"] = (det["dias_para_vencer"] > HORIZONTE).astype(int)
    det = det.sort_values(["_orden", "en_riesgo"], ascending=[True, False])

    top = det.head(18)
    tt = pd.DataFrame({
        "Lote": top["lote"],
        "Producto": top["producto"],
        "Bodega": top["bodega"],
        "Vence": top["vence"].map(_fecha),
        "Días": top["dias_para_vencer"].astype(int),
        "Qué problema es": top["problema"],
        "En bodega": top["unidades"].astype(int),
        "Sobran": top["en_riesgo_u"].astype(int),
        "Plata en riesgo": top["en_riesgo"].map(lambda x: cop(x, 0)),
        "Qué hacer": top["accion"],
        "Por qué": top["detalle"],
    })
    st.dataframe(tt, hide_index=True, width="stretch")
    st.caption(
        f"Primero los lotes con fecha encima y después los detenidos; dentro de "
        f"cada bloque, por plata. Son los {num(len(top))} primeros de "
        f"{num(len(det))} lotes con sobrante. La columna «Sobran» es la resta que "
        f"no hace el ERP: unidades en bodega menos lo que la demanda alcanza a "
        f"consumir antes del vencimiento. Y «Qué problema es» hay que leerla "
        f"junto con «Días»: con la fecha a más de "
        f"{num(HORIZONTE)} días el lote no se está venciendo, está quieto.")

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
            entran {cop(a['rec'], 0)} al 30% de descuento colocando el {coloca}%</div>
        </div>""", unsafe_allow_html=True)

    canje = det[det["accion"] == "Canje con el proveedor"]
    if not canje.empty:
        cp = canje.groupby("proveedor").agg(
            n=("lote", "size"), plata=("en_riesgo", "sum")).sort_values(
            "plata", ascending=False)
        quienes = " · ".join(
            f"{p} ({int(r['n'])} lotes, {cop(r['plata'], 0)})"
            for p, r in cp.head(3).iterrows())
        st.caption(md(
            f"**El canje es una hipótesis, no un acuerdo.** Supone que el "
            f"proveedor recibe de vuelta mercancía suya que todavía tiene vida "
            f"útil, y eso hay que preguntarlo antes de contarlo como plata "
            f"recuperada. Las contrapartes son: {quienes}. Con marcas de "
            f"prestigio la conversación realista no es «devuelvo» sino «cambio "
            f"referencia» o «apoyo de mercadeo para rotarlo»; si el proveedor "
            f"dice que no, estos lotes caen a liquidación programada."))

    st.markdown(espacio(10), unsafe_allow_html=True)

    # ── La aritmética del descuento ─────────────────────────────────────────
    st.markdown('<div class="ky-sub">Cuánto se recupera con descuento</div>',
                unsafe_allow_html=True)
    colocacion = st.select_slider(
        "Qué porcentaje del sobrante se logra colocar de verdad",
        options=COLOCACION, value=COLOCACION_DEF, key="vc_coloca",
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
            "Valor del sobrante a ese precio": cop(lista * (1 - d), 0),
            f"Entra en caja (coloca {colocacion}%)": cop(recupera, 0),
            "Contra el costo": signo((recupera - costo_hundido) / max(costo_hundido, 1) * 100, 0),
            "Recupera": pct(recupera / max(costo_hundido, 1) * 100, 0),
        })
    st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch")

    # Los dos extremos del tramo «bajo costo», calculados con el mismo supuesto
    # de colocación del cuadro. Antes esta frase decía «entre 80% y 95%» fijo, y
    # no cuadraba ni con colocación total ni con la del slider.
    rec_eq = lista * (1 - equilibrio / 100) * colocacion / 100 / max(costo_hundido, 1) * 100
    rec_40 = lista * (1 - DESCUENTOS[-1]) * colocacion / 100 / max(costo_hundido, 1) * 100
    # A colocación total el extremo bueno es 100% por definición —el equilibrio
    # es justo donde el ingreso iguala al costo hundido— y el malo sale del mix.
    tope_txt = (f" Subir el control de arriba al 100% mueve las dos puntas al "
                f"{pct(lista * (1 - DESCUENTOS[-1]) / max(costo_hundido, 1) * 100, 0)} "
                f"y al {pct(100, 0)}." if colocacion < 100 else "")
    st.markdown(panel(
        "A partir de qué descuento conviene, y contra qué se compara",
        f"El costo de ese sobrante —<b>{cop(costo_hundido, 0)}</b>— ya está "
        f"pagado, y no se recupera dejándolo en la bodega. De ahí, "
        f"{cop(venc_total)} se vence antes de venderse: si nadie lo saca, entra "
        f"{cop(0)}. El resto no se va a vencer pronto, pero sigue amarrando caja "
        f"cada mes que espera. Por eso la comparación correcta no es «¿me deja "
        f"margen?» sino «¿cuánto de esa plata vuelve, y cuándo?».<br><br>"
        f"<b>Hasta {pct(equilibrio, 0)} de descuento la venta todavía deja "
        f"margen positivo</b>: es el margen ponderado real de estos lotes. Ojo "
        f"con la lectura fácil: el descuento <b>sí cuesta</b> —cuesta exactamente "
        f"el margen que se regala— y solo sale gratis comparado contra el "
        f"escenario de perderlo todo. Entre {pct(equilibrio, 0)} y 40% ya se "
        f"vende bajo costo: colocando el {colocacion}% del sobrante entra entre "
        f"el <b>{pct(rec_40, 0)}</b> y el <b>{pct(rec_eq, 0)}</b> del costo "
        f"hundido en vez de cero, y eso es una decisión de caja, no de "
        f"rentabilidad.{tope_txt}<br><br>"
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
    def _dominantes(serie) -> list:
        """Las categorías que hay que nombrar: una si se lleva el grueso, si no dos."""
        s = serie.sort_values(ascending=False)
        if s.empty or s.sum() <= 0:
            return []
        n = 1 if s.iloc[0] / s.sum() >= 0.70 else 2
        return [c.lower() for c in s.head(n).index]

    urgentes = det[det["dias_para_vencer"] <= 60]
    cat_urg = _dominantes(urgentes["categoria"].value_counts())
    cat_det = _dominantes(detenido.groupby("categoria")["en_riesgo"].sum())
    bloque_fecha = (
        f"Con fecha encima —sesenta días o menos— hay "
        f"<b>{num(len(urgentes))} lotes por {cop(urgentes['en_riesgo'].sum())}</b>"
        + (f", casi todo {_lista(cat_urg)}, que es donde vive la vida útil "
           f"corta" if cat_urg else "") +
        f". Eso es lo que hay que sacar esta semana y cabe en una sola promoción."
        if len(urgentes) else
        "Con fecha encima —sesenta días o menos— no hay un solo lote con "
        "sobrante: lo que vence pronto se vende solo, y por ahí no se está "
        "perdiendo plata.")
    if len(detenido):
        bloque_det = (
            f"El otro lado del calendario es más grande y es otro problema: "
            f"<b>{cop(det_total, 0)} en {num(len(detenido))} lotes</b> sin una "
            f"sola venta en noventa días y con más de seis meses de vida útil"
            + (f", sobre todo {_lista(cat_det)}" if cat_det else "") +
            f". Ese producto <b>no se va a vencer</b> —la mediana tiene "
            f"{num(detenido['dias_para_vencer'].median() / 365, 1)} años por "
            f"delante— y presentarlo como merma es lo que hace que el comité deje "
            f"de creerle a la pantalla. Lo que sí es cierto es que son "
            f"{num(detenido['en_riesgo_u'].sum())} unidades de producto caro "
            f"quietas hace un trimestre: capital de trabajo, no caducidad.<br><br>"
            f"La decisión de la semana no es cuánto descuento dar: es <b>con "
            f"cuáles de esos lotes todavía se puede negociar un canje</b> "
            f"mientras le sirven al proveedor, y cuáles ya solo salen con precio.")
    else:
        bloque_det = (
            "Y al otro lado del calendario no hay nada represado: ningún lote "
            "con más de seis meses de vida útil tiene sobrante, así que aquí no "
            "hay el problema de surtido disfrazado de vencimiento que sí "
            "aparece al mirar la operación completa.")
    st.markdown(panel("La conclusión", f"{bloque_fecha}<br><br>{bloque_det}",
                      "🧭", "alerta"), unsafe_allow_html=True)
