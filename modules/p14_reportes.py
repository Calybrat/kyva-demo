"""Reportes automáticos: los informes que hoy alguien arma a mano.

Salen de las MISMAS funciones que alimentan el panel (`utils/datos.py`), así
que ningún reporte puede contradecir a un tablero ni a otro reporte.
"""
import datetime
import io

import pandas as pd
import streamlit as st

from utils.formatters import *
from utils import datos

REPORTES = {
    "Comité del lunes (semanal)":
        "La semana que cerró, el año corrido y las tres decisiones de la semana.",
    "Junta de socios (mensual)":
        "Estado de resultados, mezcla de canales, caja y deuda. Para Romain y Mathieu.",
    "Reporte para un aliado (trimestral)":
        "Cuántos de sus miembros compraron y qué compraron. Para renegociar la alianza con datos.",
    "Operación de entregas (semanal)":
        "Ventanas de despacho, cancelaciones y zonas. Para el equipo de bodega.",
}


def _comite() -> str:
    c, s, m = datos.cabecera(), datos.semana(), datos.margen_canal().set_index("canal")
    a, b = s["actual"], s["anterior"]
    e, en = datos.elite(), datos.entregas()
    d = datos.pipeline_diciembre()
    return f"""# Comité del lunes · semana del 24 al 30 de agosto de 2026

**KYVA** · licores, vinos y cervezas premium · Bogotá y la Sabana

---

## 1. La semana (e-commerce)

| Indicador | Semana | Misma semana 2025 | Cambio |
|---|---|---|---|
| Venta neta | {cop(a['ingreso'])} | {cop(b['ingreso'])} | {signo((a['ingreso']/b['ingreso']-1)*100)} |
| Pedidos entregados | {num(a['pedidos'])} | {num(b['pedidos'])} | {signo((a['pedidos']/b['pedidos']-1)*100)} |
| Ticket promedio | {cop(a['ticket'])} | {cop(b['ticket'])} | {signo((a['ticket']/b['ticket']-1)*100)} |
| Clientes nuevos | {num(a['nuevos'])} | {num(b['nuevos'])} | |
| Esperaron el fin de semana | {pct(a['espera_finde'], 0)} | {pct(b['espera_finde'], 0)} | |
| Cancelados | {num(a['cancelados'])} | {num(b['cancelados'])} | |

## 2. El año

- **Ingresos ene–ago 2026:** {cop(c['ingresos_ytd'])} ({signo(c['crec_ytd'])} contra ene–ago 2025)
- **Margen bruto (12 m):** {pct(c['margen_bruto12'])} · **margen operacional (12 m):** {pct(c['margen_op12'], 2)}
- **Caja:** {cop(c['caja'])} · **deuda:** {cop(c['deuda'])} · **inventario:** {cop(c['inventario'])}

## 3. Las tres decisiones de la semana

**1 · Margen de The Lounge.** Le queda {pct(m.loc['The Lounge', 'contribucion_pct'])} de cada peso contra {pct(m.loc['The Store', 'contribucion_pct'])} de The Store. El descuento Elite de 12 meses suma {cop(e['descuento12'])}.

**2 · Despacho de fin de semana.** {pct(en['finde_pct'], 0)} de los pedidos esperan el fin de semana o un festivo y se cancelan más. Valor perdido estimado: {cop(en['valor_perdido_finde'])} al año.

**3 · Fin de año.** Hay {cop(d['abierto_nov_dic_2026'])} cotizados para nov–dic. La compra de inventario de diciembre se decide en las próximas cuatro semanas.

---
*Generado automáticamente desde el panel. Datos simulados para demostración.*
"""


def _junta() -> str:
    f = datos.finanzas()
    an = datos.anual()
    m = datos.margen_canal()
    c = datos.cabecera()
    filas = "\n".join(
        f"| {r.canal} | {cop(r.ingreso)} | {pct(r.peso_pct, 0)} | {pct(r.margen_bruto_pct)} | {pct(r.contribucion_pct)} |"
        for r in m.itertuples())
    hist = "\n".join(
        f"| {a} | {cop(r['ingresos'])} | {signo(r['crecimiento_pct'], 1) if pd.notna(r['crecimiento_pct']) else '—'} | "
        f"{pct(r['margen_bruto_pct'])} | {cop(r['utilidad_operacional'])} | {pct(r['margen_operacional_pct'], 2)} |"
        for a, r in an.iterrows())
    return f"""# Junta de socios · corte {datos.CORTE_TXT}

**KYVA SAS** · NIT 901.312.028 · Bogotá

---

## Resultados por año

| Año | Ingresos | Crecimiento | Margen bruto | Utilidad operacional | Margen operacional |
|---|---|---|---|---|---|
{hist}

*2026 es enero–agosto.*

## Los cuatro canales (últimos 12 meses)

| Canal | Ingreso | Peso | Margen bruto | Le queda después de costos de venta |
|---|---|---|---|---|
{filas}

## Caja

| | |
|---|---|
| Caja | {cop(c['caja'])} |
| Deuda de corto plazo | {cop(c['deuda'])} (máximo del período: {cop(f['deuda'].max())}) |
| Inventario | {cop(c['inventario'])} |
| Equipo | {c['personas']} personas |

## Lectura

Los ingresos se multiplicaron por más de dos en 2024 y otra vez en 2025, y la
utilidad operacional sigue en cero. No hubo economía de escala: los costos que
acompañan cada pedido —descuento Elite, envío gratis, pasarela— crecieron al
mismo ritmo que la venta. El crecimiento se está financiando con la línea de
crédito, que sube cada octubre con la compra de diciembre.

La conversación de fondo para la junta es de mezcla: cuánto de The Lounge, cuánto
de corporativo y cuánto de distribución se quiere tener en 2027.

---
*Datos simulados para demostración, anclados a cifras públicas de KYVA SAS.*
"""


def _aliado(nombre: str) -> str:
    a = datos.aliados()
    r = a.loc[nombre]
    ok = datos.entregados()
    cli = datos.clientes()
    ids = cli[(cli["aliado"] == nombre)]["cliente_id"]
    p = ok[ok["cliente_id"].isin(ids) & ok["mes"].isin(datos.ultimos(12))]
    cat = p["categoria_principal"].value_counts(normalize=True).head(5) * 100
    cats = "\n".join(f"| {k} | {pct(v, 0)} |" for k, v in cat.items())
    prom = a["activacion_pct"].mean()
    return f"""# Reporte de la alianza · {nombre}

**KYVA · The Lounge** · últimos 12 meses al {datos.CORTE_TXT}

---

## Sus miembros en KYVA

| | |
|---|---|
| Miembros Elite que llegaron por {nombre} | **{num(r['miembros'])}** |
| Estrenaron la membresía | **{pct(r['activacion_pct'], 0)}** (promedio de todos los aliados: {pct(prom, 0)}) |
| Pedidos en 12 meses | {num(r['pedidos12'])} |
| Ahorro que recibieron sus miembros | {cop(r['descuento12'])} |

## Qué compran

| Categoría | Peso en sus pedidos |
|---|---|
{cats}

## Propuesta para el próximo trimestre

{'Sus miembros convierten por encima del promedio. Proponemos ampliar el beneficio: acceso anticipado a lanzamientos y una cata privada anual en su sede.' if r['activacion_pct'] >= prom else 'La mayoría de sus miembros aún no ha estrenado la membresía. Proponemos una activación conjunta —una cata en su sede, como la del Porsche Center en septiembre de 2025— y un recordatorio a quienes la recibieron y no la han usado.'}

---
*Generado automáticamente desde el panel de KYVA. Datos simulados para demostración.*
"""


def _entregas() -> str:
    e = datos.entregas()
    v = e["ventanas"]
    filas = "\n".join(f"| {k} | {pct(r['peso_pct'], 0)} | {num(r['horas'], 1)} h | {pct(r['cancelacion'])} |"
                      for k, r in v.iterrows())
    return f"""# Operación de entregas · semana del {datetime.date(2026, 8, 31):%d/%m/%Y}

## Ventanas de despacho (12 meses)

| Ventana | Pedidos | Espera (mediana) | Cancelación |
|---|---|---|---|
{filas}

- **Pedidos en 12 meses:** {num(e['pedidos12'])}
- **Entregados en la fecha prometida:** {pct(e['promesa_pct'])}
- **Cancelados:** {num(e['cancelados12'])} ({cop(e['valor_cancelado12'])})

## Lo que hay que mirar

El horario de despacho (lun–jue 8–5, vie 8–4) deja por fuera el momento en que
más se compra licor. Los pedidos que esperan el fin de semana o un festivo se
cancelan más que los que salen el mismo día. En la segunda quincena de diciembre
la promesa de entrega se cae en uno de cada cinco pedidos: la capacidad de
diciembre se contrata en octubre.

---
*Generado automáticamente desde el panel. Datos simulados para demostración.*
"""


def render():
    st.markdown(HEADER_CSS, unsafe_allow_html=True)
    st.markdown(encabezado(
        "Reportes Automáticos",
        "Los informes que hoy alguien arma a mano, generados desde los mismos datos",
        "Dirección"), unsafe_allow_html=True)

    st.markdown(panel(
        "Por qué esto importa",
        "En una empresa de trece personas, el informe del lunes lo arma alguien exportando "
        "de WooCommerce, de la pasarela y de la hoja de Excel de corporativo. Toma medio día "
        "y cada semana sale un poco distinto.<br><br>"
        "Estos reportes salen de las <b>mismas funciones</b> que alimentan el panel: no pueden "
        "contradecirse. Y en producción no se abren — <b>llegan solos</b> al correo el lunes a "
        "las 7. El reporte por aliado es el que convierte cada alianza en una conversación "
        "con datos.", "📄"), unsafe_allow_html=True)
    st.markdown(espacio(12), unsafe_allow_html=True)

    c1, c2 = st.columns([2, 1.2])
    with c1:
        tipo = st.selectbox("Reporte", list(REPORTES.keys()), key="rep_tipo")
    with c2:
        aliado = None
        if tipo.startswith("Reporte para un aliado"):
            aliado = st.selectbox("Aliado", datos.aliados().index.tolist(), key="rep_aliado")
        else:
            st.markdown(espacio(26), unsafe_allow_html=True)
            st.caption(REPORTES[tipo])

    with st.spinner("Generando el reporte…"):
        if tipo.startswith("Comité"):
            texto = _comite()
        elif tipo.startswith("Junta"):
            texto = _junta()
        elif tipo.startswith("Reporte para un aliado"):
            texto = _aliado(aliado)
        else:
            texto = _entregas()

    nombre = tipo.split(" (")[0].lower().replace(" ", "_")
    d1, d2, _ = st.columns([1, 1, 3])
    with d1:
        st.download_button("⬇️  Descargar (Markdown)", texto,
                           file_name=f"kyva_{nombre}_{datos.MES_ACTUAL}.md",
                           mime="text/markdown", width="stretch")
    with d2:
        c = datos.cabecera()
        resumen = pd.DataFrame({"Indicador": list(c.keys()), "Valor": list(c.values())})
        buf = io.StringIO()
        resumen.to_csv(buf, index=False)
        st.download_button("⬇️  Indicadores (CSV)", buf.getvalue(),
                           file_name=f"kyva_indicadores_{datos.MES_ACTUAL}.csv",
                           mime="text/csv", width="stretch")

    st.markdown(espacio(10), unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(texto)
