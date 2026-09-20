"""Rentabilidad por cuenta: cuánto deja cada bar, no cuánto compra.

El punto ciego número uno de un distribuidor, y no por falta de datos: por
reparto. El ERP sabe cuánto le VENDE a cada cuenta. El operador logístico sabe
cuánto cuesta repartir. Nadie junta las dos cosas, y entre las dos está la única
cifra que importa — **cuánto deja cada cuenta después de servirla**.

La aritmética que aparece cuando se juntan es incómoda:

  · Una entrega cuesta casi lo mismo lleve cuatro botellas o cuarenta.
  · Un bar que pide tres veces por semana valores chicos puede tener buen
    margen bruto y aun así costar plata.
  · Una discoteca compra volumen con 27% de descuento y paga a 15 días; un
    club social compra menos, con 19%, y paga a 45. Cuál conviene no se puede
    contestar mirando la venta.

Se juzga sobre el **último trimestre**, no sobre doce meses. Un mes malo es
ruido —una remodelación, un puente—; tres meses malos son una condición
comercial que hay que cambiar. Y un promedio de doce meses protege justo a la
cuenta que se deterioró hace tres.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.formatters import *
from utils import b2b, filtros, ui

COLOR_SALUD = {"Cuesta plata": "#8B1E1E", "Apenas paga": "#B5762F",
               "Aceptable": "#2B7A9B", "Buena": "#2f7a48"}


def _ficha(c, hist):
    """La cuenta entera en una tarjeta: qué compra, qué cuesta, qué deja."""
    color = COLOR_SALUD.get(c["salud"], CLARO)
    return f"""
    <div style="border:1px solid {PALIDO};border-top:4px solid {color};
         border-radius:6px;padding:18px 22px;background:#fff;margin-bottom:14px">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:20px">
        <div>
          <div style="font-size:9.5px;font-weight:800;letter-spacing:.14em;
               text-transform:uppercase;color:{CLARO}">
            {c['canal']} · {c['ciudad']} · {c['zona']}</div>
          <div style="font-family:'DM Serif Display',Georgia,serif;font-size:27px;
               color:{TINTA};line-height:1.15;margin:2px 0 4px">{c['nombre']}</div>
          <div style="font-size:11.5px;color:{CLARO}">
            Vendedor: <b style="color:{TINTA}">{c['vendedor']}</b> &nbsp;·&nbsp;
            Cliente desde {c['alta']:%b %Y} &nbsp;·&nbsp;
            Descuento {c['descuento_pct']}% &nbsp;·&nbsp; Paga a {c['plazo_pago']} días</div>
        </div>
        <div style="text-align:right;white-space:nowrap">
          <div style="font-size:9.5px;font-weight:800;letter-spacing:.1em;
               text-transform:uppercase;color:{CLARO}">Margen servido · trimestre</div>
          <div style="font-size:30px;font-weight:800;color:{color};line-height:1.1">
            {c['servido_pct']:.1f}%</div>
          <div style="font-size:12px;color:{CLARO}">{cop(c['servido'], 0)}</div>
        </div>
      </div>
    </div>"""


def _cascada(c):
    """De lo que factura a lo que queda. Cada resta con nombre y dueño."""
    pasos = [
        ("Precio de lista", c["bruto"], None),
        ("Descuento comercial", -c["descuento"], "lo pacta el vendedor"),
        ("Devoluciones", -c["devoluciones"], "producto que vuelve"),
        ("Costo de la mercancía", -c["costo"], "lo fija la compra"),
        ("Costo de servir", -c["logistica"], f"{int(c['entregas'])} entregas"),
    ]
    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute"] + ["relative"] * 4 + ["total"],
        x=[p[0] for p in pasos] + ["Lo que queda"],
        y=[p[1] for p in pasos] + [0],
        text=[cop(abs(p[1]), 0) for p in pasos] + [cop(c["servido"], 0)],
        textposition="outside", textfont=dict(size=10),
        connector=dict(line=dict(color=PALIDO, width=1)),
        increasing=dict(marker=dict(color=PRIMARIO)),
        decreasing=dict(marker=dict(color=ACENTO)),
        totals=dict(marker=dict(color=COLOR_SALUD.get(c["salud"], PRIMARIO)))))
    return fig


def render():
    st.markdown(HEADER_CSS, unsafe_allow_html=True)
    st.markdown(encabezado(
        "Rentabilidad por cuenta",
        "Cuánto deja cada establecimiento después de servirlo · último trimestre",
        "¿Quién nos deja plata?"), unsafe_allow_html=True)
    filtros.encabezado_filtro()

    r = filtros.aplicar(b2b.rentabilidad(), col_mes=None)
    if r.empty:
        st.info("Ninguna cuenta con los filtros puestos. Quítalos en la barra lateral.")
        return
    res = b2b.resumen_b2b()
    rojas = r[r["servido"] < 0]
    apenas = r[r["salud"] == "Apenas paga"]

    k = st.columns(4, gap="small")
    k[0].markdown(kpi(
        "Cuentas activas", num(res["cuentas_activas"]),
        f"de {res['cuentas_total']} en la base", True, "🏪",
        "Establecimientos que compraron en agosto."), unsafe_allow_html=True)
    k[1].markdown(kpi(
        "Margen bruto", pct(res["margen_12m_pct"]),
        f"queda {pct(res['servido_12m_pct'])} tras logística",
        res["servido_12m_pct"] > 18, "💸",
        "La diferencia entre los dos números es el costo de servir, "
        "que ningún informe de ventas muestra."), unsafe_allow_html=True)
    k[2].markdown(kpi(
        "Cuentas que cuestan plata", num(len(rojas)),
        f"{num(len(apenas))} más apenas se pagan", len(rojas) == 0, "🩸",
        "Venden, pero después de repartirles queda menos que cero."),
        unsafe_allow_html=True)
    k[3].markdown(kpi(
        "Capital en la calle", cop(res["expuesto"], 0),
        "por los plazos que damos", False, "🏦",
        "Lo que facturamos y todavía no cobramos, por el plazo de cada canal.",
        "Un club social a 45 días amarra mes y medio de su propia venta"),
        unsafe_allow_html=True)

    st.markdown(espacio(18), unsafe_allow_html=True)

    # ── El mapa: venta contra lo que deja ───────────────────────────────────
    st.markdown('<div class="ky-sub">El mapa de las cuentas</div>', unsafe_allow_html=True)
    fig = go.Figure()
    for salud, color in COLOR_SALUD.items():
        d = r[r["salud"] == salud]
        if d.empty:
            continue
        fig.add_trace(go.Scatter(
            x=d["neto"], y=d["servido_pct"], mode="markers", name=salud,
            marker=dict(size=np.clip(d["entregas"] * 1.6, 8, 34), color=color,
                        opacity=.78, line=dict(width=1, color="#fff")),
            customdata=np.stack([d["nombre"], d["canal"], d["ciudad"],
                                 d["entregas"], d["margen_pct"],
                                 d["costo_por_entrega"]], -1),
            hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]} · %{customdata[2]}"
                          "<br>Venta trimestre: %{x:,.0f}<br>"
                          "Margen bruto: %{customdata[4]:.1f}%<br>"
                          "<b>Margen servido: %{y:.1f}%</b><br>"
                          "%{customdata[3]:.0f} entregas a %{customdata[5]:,.0f} c/u"
                          "<extra></extra>"))
    fig.add_hline(y=0, line_width=1.4, line_color="#8B1E1E")
    fig.add_hline(y=18, line_width=1, line_dash="dot", line_color=CLARO)
    fig.update_xaxes(title="Venta neta del trimestre")
    fig.update_yaxes(title="Margen después de servir (%)")
    ui.pista_clic("Haz clic en cualquier cuenta para abrir su ficha")
    elegidas = ui.grafico_seleccionable(fig, "mapa_cuentas", 420)
    if elegidas:
        _abrir_ficha(r, elegidas[0])
    st.caption(
        "El tamaño del círculo es el número de entregas del trimestre. "
        "**Las burbujas grandes abajo a la izquierda son el problema**: cuentas "
        "pequeñas a las que se va muchas veces. La línea punteada es el 18% que "
        "hace falta para pagar la estructura.")

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── Por canal ───────────────────────────────────────────────────────────
    st.markdown('<div class="ky-sub">Qué canal conviene de verdad</div>',
                unsafe_allow_html=True)
    g = r.groupby("canal").agg(
        cuentas=("cuenta_id", "size"), neto=("neto", "sum"),
        margen=("margen", "sum"), logistica=("logistica", "sum"),
        servido=("servido", "sum"), entregas=("entregas", "sum"),
        desc=("descuento_pct", "mean"), plazo=("plazo_pago", "mean")).reset_index()
    g["margen_pct"] = g["margen"] / g["neto"] * 100
    g["servido_pct"] = g["servido"] / g["neto"] * 100
    g["ticket"] = g["neto"] / g["entregas"]
    g = g.sort_values("servido_pct", ascending=False)

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(y=g["canal"], x=g["margen_pct"], orientation="h",
                          name="Margen bruto", marker_color=PALIDO,
                          hovertemplate="Bruto: %{x:.1f}%<extra></extra>"))
    fig2.add_trace(go.Bar(y=g["canal"], x=g["servido_pct"], orientation="h",
                          name="Después de servir",
                          marker_color=[COLOR_SALUD["Buena"] if v > 18 else
                                        COLOR_SALUD["Apenas paga"] if v > 8 else
                                        COLOR_SALUD["Cuesta plata"] for v in g["servido_pct"]],
                          hovertemplate="Servido: %{x:.1f}%<extra></extra>"))
    fig2.update_layout(barmode="overlay")
    fig2.update_xaxes(title="% sobre venta neta")
    st.plotly_chart(light(fig2, 300), use_container_width=True)

    peor = g.iloc[-1]
    mejor = g.iloc[0]
    st.markdown(panel(
        "La conclusión que no se ve en el informe de ventas",
        f"<b>{peor['canal']}</b> vende {cop(peor['neto'], 0)} en el trimestre con "
        f"{pct(peor['margen_pct'])} de margen bruto, pero después de las "
        f"{int(peor['entregas'])} entregas queda en <b>{pct(peor['servido_pct'])}</b>. "
        f"<b>{mejor['canal']}</b>, con un ticket por entrega de "
        f"{cop(mejor['ticket'], 0)} contra {cop(peor['ticket'], 0)}, termina en "
        f"{pct(mejor['servido_pct'])}. "
        f"La diferencia no está en el precio ni en el descuento: está en "
        f"<b>cuántas veces hay que ir</b>. Subir el pedido mínimo cambia más el "
        f"resultado que renegociar la lista.",
        "🧭", "rojo"), unsafe_allow_html=True)

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── La cuenta, en detalle ───────────────────────────────────────────────
    st.markdown('<div class="ky-sub">Abrir una cuenta</div>', unsafe_allow_html=True)
    orden = r.sort_values("servido_pct")
    etiquetas = [f"{x['nombre']} — {x['canal']} · {x['servido_pct']:.1f}%"
                 for _, x in orden.iterrows()]
    elegida = st.selectbox("Cuenta", etiquetas, key="ct_cuenta")
    c = orden.iloc[etiquetas.index(elegida)]

    st.markdown(_ficha(c, None), unsafe_allow_html=True)

    col = st.columns([3, 2], gap="large")
    with col[0]:
        st.plotly_chart(light(_cascada(c), 330, moneda=True), use_container_width=True)
    with col[1]:
        st.markdown(espacio(20), unsafe_allow_html=True)
        filas = [
            ("Venta neta del trimestre", cop(c["neto"], 0)),
            ("Entregas", f"{int(c['entregas'])}"),
            ("Valor por entrega", cop(c["ticket_entrega"], 0)),
            ("Costo de cada entrega", cop(c["costo_por_entrega"], 0)),
            ("Margen bruto", pct(c["margen_pct"])),
            ("Margen después de servir", pct(c["servido_pct"])),
            ("Capital expuesto", cop(c["expuesto"], 0)),
            ("Cupo aprobado", cop(c["cupo_credito"], 0)),
        ]
        cuerpo = "".join(
            f'<tr><td style="padding:6px 0;font-size:12px;color:{CLARO}">{k}</td>'
            f'<td style="padding:6px 0;font-size:13px;font-weight:700;color:{TINTA};'
            f'text-align:right">{v}</td></tr>' for k, v in filas)
        st.markdown(f'<table style="width:100%;border-collapse:collapse">{cuerpo}</table>',
                    unsafe_allow_html=True)

    # Qué hacer con esta cuenta — la parte que convierte el análisis en acción
    if c["servido_pct"] < 8:
        falta = (0.18 - c["servido_pct"] / 100) * c["neto"]
        menos_entregas = max(1, int(c["entregas"] * 0.55))
        ahorro = (c["entregas"] - menos_entregas) * c["costo_por_entrega"]
        nuevo_desc = max(c["descuento_pct"] - 4, 8)
        gana_desc = c["bruto"] * 0.04
        st.markdown(panel(
            f"Tres maneras de arreglar {c['nombre']}",
            f"Para llegar al 18% le faltan <b>{cop(falta, 0)}</b> en el trimestre. "
            f"<br><br>"
            f"<b>1. Menos visitas.</b> Pasar de {int(c['entregas'])} a {menos_entregas} "
            f"entregas ahorra {cop(ahorro, 0)} y no toca el precio. "
            f"Es la palanca más grande y la que menos molesta al cliente.<br>"
            f"<b>2. Menos descuento.</b> Bajar del {c['descuento_pct']}% al "
            f"{nuevo_desc}% suma {cop(gana_desc, 0)}. Es la conversación difícil.<br>"
            f"<b>3. Pedido mínimo.</b> Subirlo a {cop(c['costo_por_entrega'] * 12, 0)} "
            f"hace que cada viaje se pague solo, sin negociar nada.",
            "🔧", "rojo"), unsafe_allow_html=True)
    else:
        st.markdown(panel(
            f"{c['nombre']} está sana",
            f"Deja {pct(c['servido_pct'])} después de servirla, por encima del 18% "
            f"que paga la estructura. La pregunta con una cuenta así no es cómo "
            f"arreglarla: es <b>si se le puede vender más</b> sin subir la "
            f"frecuencia de entrega, que es donde se va el margen.",
            "✓", "azul"), unsafe_allow_html=True)


# ── La ficha, al hacer clic en el mapa ───────────────────────────────────────
# Existe porque un gráfico que no se puede abrir obliga a creerle a una
# cascada. El revisor lo dijo mejor: «si no puedo bajar hasta la factura, yo no
# puedo pelear con ese número y entonces no sirve para decidir nada».
@st.dialog("Ficha de cuenta", width="large")
def _abrir_ficha(r, nombre):
    from utils import gerencia
    c = r[r["nombre"] == nombre]
    if c.empty:
        st.warning(f"No encuentro {nombre}.")
        return
    c = c.iloc[0]
    st.markdown(_ficha(c, None), unsafe_allow_html=True)

    m = st.columns(4, gap="small")
    for col, (etq, val) in zip(m, [
            ("Venta trimestre", cop(c["neto"], 0)),
            ("Entregas", f"{int(c['entregas'])}"),
            ("Costo por entrega", cop(c["costo_por_entrega"], 0)),
            ("Margen servido", pct(c["servido_pct"]))]):
        col.markdown(
            f'<div style="border:1px solid {PALIDO};border-radius:5px;padding:11px 14px">'
            f'<div style="font-size:9.5px;font-weight:800;letter-spacing:.11em;'
            f'text-transform:uppercase;color:{CLARO}">{etq}</div>'
            f'<div style="font-size:19px;font-weight:800;color:{TINTA};'
            f'margin-top:3px">{val}</div></div>', unsafe_allow_html=True)

    st.markdown(espacio(14), unsafe_allow_html=True)
    st.plotly_chart(light(_cascada(c), 300, moneda=True), use_container_width=True)

    # Hasta la factura. Es lo que permite discutir el número con el vendedor.
    try:
        f = gerencia.facturas()
        suyas = f[f["nombre"] == nombre].sort_values("emitida", ascending=False)
        if len(suyas):
            st.markdown('<div class="ky-sub">Sus facturas</div>', unsafe_allow_html=True)
            t = suyas.head(14)[["factura", "emitida", "vence", "valor",
                                "pagada", "dias_vencida", "tramo"]].copy()
            t["emitida"] = suyas.head(14)["emitida"].dt.strftime("%d %b")
            t["vence"] = suyas.head(14)["vence"].dt.strftime("%d %b")
            t["valor"] = suyas.head(14)["valor"].map(lambda v: cop(v, 0))
            t["pagada"] = suyas.head(14)["pagada"].map(lambda x: "✓" if x else "abierta")
            t["dias_vencida"] = suyas.head(14)["dias_vencida"].astype(int)
            t.columns = ["Factura", "Emitida", "Vence", "Valor", "Estado",
                         "Días vencida", "Tramo"]
            st.dataframe(t, hide_index=True, width="stretch")
            abierto = float(suyas.loc[~suyas["pagada"], "saldo"].sum())
            st.caption(md(f"{cop(abierto, 0)} abiertos en "
                       f"{int((~suyas['pagada']).sum())} facturas."))
    except Exception:
        pass
